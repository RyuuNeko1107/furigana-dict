#!/usr/bin/env python3
# ruff: noqa: T201
"""
ja-furigana (OSS lib) vs ryuuneko.com (= production reference) の出力比較 tool。

corpus TOML を input に取り、 各 case を:
1. ローカル ja-furigana binary で変換
2. ryuuneko.com /furigana API で変換
3. 結果を比較、 一致 / 不一致を集計

ryuuneko.com は ja-furigana の production version (= 同等の curated dict + tuning)、
OSS lib との出力差は dict カバレッジ / engine 実装の進度差を示す。

## 使い方

    python3 tools/compare_with_reference.py \\
        --binary /path/to/furigana-corpus-check \\
        --rules-dir <furigana-dict/rules> \\
        --core-dict-dir <furigana-dict/core/jukugo> \\
        ... \\
        tests/corpus/should_read.toml

## 注意

- ryuuneko.com は無認証で 60 req/min レート制限、 サンプリングで実行 (default 50 case)
- API キー指定で高 rate 上限 (`--api-key=...`)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

REFERENCE_API = "https://ryuuneko.com/furigana"


def call_reference(text: str, mode: str, api_key: str | None = None) -> str:
    """ryuuneko.com /furigana API を呼んで result を返す。"""
    body = json.dumps({"text": text, "mode": mode}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        # 「Python-urllib/3.x」 default User-Agent は ryuuneko 側 anti-bot で 403 になるため、
        # 明示的に dev tool 名を入れる (= サーバ側 log で OSS 比較利用を識別可能)
        "User-Agent": "ja-furigana-dict-compare-tool/1.0 (+https://github.com/RyuuNeko1107/ja-furigana-dict)",
    }
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(REFERENCE_API, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310 (= URL は固定 ryuuneko.com、 user 入力なし)
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("result", "")
    except urllib.error.HTTPError as e:
        return f"<HTTP {e.code}>"
    except (urllib.error.URLError, TimeoutError) as e:
        return f"<network error: {e}>"


def call_local(binary: str, args: list[str], corpus_file: Path) -> dict[int, str]:
    """ローカル furigana-corpus-check binary で corpus を実行、 case index → actual の dict を返す。

    binary は verbose mode (-v) で 「OK」 「FAIL」 行を吐き、 actual を parse する。
    """
    cmd = [binary, *args, "-v", str(corpus_file)]
    try:
        result = subprocess.run(  # nosec B603 (= argv は固定 binary path + corpus path、 shell なし)
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=120
        )
    except subprocess.TimeoutExpired:
        sys.exit("[FAIL] ローカル binary が timeout (120s)")
    actuals: dict[int, str] = {}
    pending_fail_idx: int | None = None
    for line in result.stdout.splitlines():
        # 例 OK: "OK   #5: input="灰桜" mode="hiragana" -> "はいざくら""
        # 例 FAIL: "FAIL #20: input="新橋" mode="romaji""
        #         "  expected: "shimbashi""
        #         "  actual:   "shinhashi""
        if line.startswith("OK   #"):
            idx_str, _, rest = line[6:].partition(":")
            try:
                idx = int(idx_str)
            except ValueError:
                continue
            if " -> " in rest:
                _, _, val = rest.rpartition(" -> ")
                actuals[idx] = val.strip().strip('"')
            pending_fail_idx = None
        elif line.startswith("FAIL #"):
            idx_str, _, _ = line[6:].partition(":")
            try:
                pending_fail_idx = int(idx_str)
            except ValueError:
                pending_fail_idx = None
        elif pending_fail_idx is not None and line.lstrip().startswith("actual:"):
            # 「  actual:   "..."」 を parse、 quote 内の文字列を抜き出す
            _, _, val = line.partition("actual:")
            actuals[pending_fail_idx] = val.strip().strip('"')
            pending_fail_idx = None
    return actuals


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("corpus", type=Path, help="corpus TOML")
    p.add_argument("--binary", required=True, help="furigana-corpus-check binary path")
    p.add_argument("--rules-dir", action="append", default=[])
    p.add_argument("--core-dict-dir", action="append", default=[])
    p.add_argument("--limit", type=int, default=50, help="比較する case 上限 (default 50)")
    p.add_argument("--rate-per-min", type=int, default=50, help="ryuuneko req/min")
    p.add_argument("--api-key", default=None)
    args = p.parse_args()

    if not args.corpus.is_file():
        sys.exit(f"[FAIL] corpus not found: {args.corpus}")

    with args.corpus.open("rb") as f:
        corpus = tomllib.load(f)
    cases = corpus.get("case", [])
    if not cases:
        sys.exit("[FAIL] corpus に [[case]] が無い")

    binary_args = []
    for r in args.rules_dir:
        binary_args.extend(["--rules-dir", r])
    for d in args.core_dict_dir:
        binary_args.extend(["--core-dict-dir", d])

    print(f"[info] ローカル binary 実行中 ({len(cases)} cases)...")
    local_actuals = call_local(args.binary, binary_args, args.corpus)

    sample = cases[: args.limit]
    print(f"[info] ryuuneko.com 比較開始 ({len(sample)} cases、 rate {args.rate_per_min}/min)...")
    interval = 60.0 / args.rate_per_min

    matches = 0
    diffs = 0
    errors = 0
    expected_total = 0
    local_correct = 0
    ref_correct = 0
    both_correct = 0
    only_local = 0
    only_ref = 0
    both_wrong = 0
    for i, case in enumerate(sample):
        text = case["input"]
        mode = case.get("mode", "ruby")
        expected = case.get("expected", "")

        local_actual = local_actuals.get(i, "<missing>")
        ref_actual = call_reference(text, mode, args.api_key)

        if ref_actual.startswith("<"):
            errors += 1
            print(f"[ERR ] #{i:3d} input={text!r} ref={ref_actual}")
            time.sleep(interval)
            continue

        if local_actual == ref_actual:
            matches += 1
        else:
            diffs += 1
            print(f"[DIFF] #{i:3d} input={text!r} mode={mode}")
            print(f"        expected: {expected!r}")
            print(f"        local:    {local_actual!r}")
            print(f"        ryuuneko: {ref_actual!r}")

        if expected:
            expected_total += 1
            local_ok = local_actual == expected
            ref_ok = ref_actual == expected
            if local_ok:
                local_correct += 1
            if ref_ok:
                ref_correct += 1
            if local_ok and ref_ok:
                both_correct += 1
            elif local_ok and not ref_ok:
                only_local += 1
            elif not local_ok and ref_ok:
                only_ref += 1
            else:
                both_wrong += 1

        time.sleep(interval)

    print()
    print("=== Summary ===")
    print(f"Total compared: {len(sample)}")
    print(f"Agreement:      {matches} ({matches * 100 / max(len(sample), 1):.1f}%)  ← local == ryuuneko 出力一致")
    print(f"Disagreement:   {diffs}")
    print(f"Errors:         {errors}")
    if expected_total:
        print()
        print("=== Accuracy vs corpus expected ===")
        pct = lambda n: f"{n * 100 / expected_total:.1f}%"
        print(f"  local-correct:  {local_correct}/{expected_total} ({pct(local_correct)})")
        print(f"  ryuuneko-correct: {ref_correct}/{expected_total} ({pct(ref_correct)})")
        print()
        print("=== Breakdown of 一致 / 不一致 ===")
        print(f"  both correct:  {both_correct} ({pct(both_correct)})")
        print(f"  only local:    {only_local} ({pct(only_local)})  ← local 勝ち")
        print(f"  only ryuuneko: {only_ref} ({pct(only_ref)})  ← ryuuneko 勝ち")
        print(f"  both wrong:    {both_wrong} ({pct(both_wrong)})  ← 両方失敗 (= dict gap 共通)")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
