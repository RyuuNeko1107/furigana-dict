#!/usr/bin/env python3
"""
core/ + rules/ 配下の TOML file 内 `[[test]]` array を抽出して、
ja-furigana binary で input → expected が一致するか検証する。

各 dict / rule file の末尾に「この file が担当する変換」 を inline test として
書けるようにする (corpus regression と違い、 file ごとの責務を明示するための
「ロック」 として機能):

    # rules/counters/objects.toml
    [counter."本"]
    default = "ホン"
    [[counter."本".rules]]
    last_digit = [1, 6, 8, 0]
    suffix = "ポン"
    sokuonize = true

    # ↓ inline test (この file の責務)
    [[test]]
    input = "1本"
    expected = "イッポン"

    [[test]]
    input = "3本"
    expected = "サンボン"

走らせ方:
    python tools/test_inline_rules.py --binary <path>            # default mode hiragana
    python tools/test_inline_rules.py --binary <path> --data-dir <path>

CI で validate.yml の 1 step として呼ぶ予定。 inline test 0 件の file は skip
(全 file での 必須化はせず、 contributor が書きたい file から書ける緩い制約)。

`subprocess.run` は argv list + shell=False で shell injection 経路無し。
"""
from __future__ import annotations

import argparse
import subprocess  # nosec B404 — fixed argv list, shell=False で安全
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def collect_inline_tests() -> list[tuple[Path, str, str]]:
    """`*.test.toml` ファイルから `[[test]]` を集める。

    戻り値: (file_path, input, expected) のリスト。

    test は **隣接した `<name>.test.toml`** に書く方針 (lib runtime memory にも
    release tar にも乗らないため、 release.yml が `--exclude='*.test.toml'`
    で除外、 lib loader も name match で skip)。 ペアで rule + test が並ぶので
    contributor 体験は「1 dir 内で隣接」 を維持する。
    """
    tests: list[tuple[Path, str, str]] = []
    targets: list[Path] = []
    for sub in ("core", "rules"):
        base = ROOT / sub
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.test.toml")):
            targets.append(p)

    for path in targets:
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        cases = data.get("test")
        if not isinstance(cases, list):
            continue
        for case in cases:
            if not isinstance(case, dict):
                continue
            inp = case.get("input")
            exp = case.get("expected")
            if isinstance(inp, str) and isinstance(exp, str):
                tests.append((path, inp, exp))
    return tests


def run_lookup(binary: str, text: str, mode: str, data_dir: str | None) -> str:
    cmd = [binary]
    if data_dir:
        cmd += ["--data-dir", data_dir]
    cmd += ["lookup", "--mode", mode, text]
    try:
        result = subprocess.run(  # nosec B603 — fixed argv, no shell
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "<TIMEOUT>"
    if result.returncode != 0:
        return f"<ERROR exit={result.returncode}: {result.stderr.strip()}>"
    return result.stdout.rstrip("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, help="furigana binary path")
    parser.add_argument("--data-dir", default=None, help="--data-dir for furigana")
    parser.add_argument("--mode", default="hiragana", help="lookup mode (default: hiragana)")
    args = parser.parse_args()

    tests = collect_inline_tests()
    if not tests:
        print("[skip] inline test 0 件 (どの file にも [[test]] が無い)")
        return

    print(f"[info] inline test {len(tests)} 件を実行")
    fails = 0
    by_file: dict[Path, list[str]] = {}
    for path, inp, exp in tests:
        actual = run_lookup(args.binary, inp, args.mode, args.data_dir)
        if actual == exp:
            continue
        fails += 1
        by_file.setdefault(path, []).append(
            f"  input={inp!r}\n    expected: {exp}\n    actual:   {actual}"
        )

    if fails == 0:
        print(f"[OK] 全 {len(tests)} 件 pass")
        return

    for path, msgs in by_file.items():
        rel = path.relative_to(ROOT)
        print(f"\n[FAIL] {rel} ({len(msgs)} 件):", file=sys.stderr)
        for m in msgs:
            print(m, file=sys.stderr)

    print(f"\n[FAIL] {fails}/{len(tests)} 件失敗", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
