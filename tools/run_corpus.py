#!/usr/bin/env python3
# ruff: noqa: T201
"""
ja-furigana の corpus 回帰テスト runner。

corpus 内の各 case を、 ローカルの `furigana` バイナリで実行して
expected と一致するか検証する。 失敗があれば exit 1 で抜ける (CI gate 前提)。

引数 `corpus` は **file または directory** のどちらでも OK:

- file 指定 (例: `tests/corpus/should_read.toml`) → その file 単体を実行
- dir 指定 (例: `tests/corpus/should_read/`) → 配下の `*.toml` を再帰的に全部実行
- 同名 file + 同名 dir が両方ある場合 (例: `should_read.toml` + `should_read/` 共存) →
  file 引数で渡しても dir 配下も自動的に併合される (gradual な分割移行を支援)

Usage:
    python3 tools/run_corpus.py                                     # default は should_read.toml
    python3 tools/run_corpus.py tests/corpus/should_read.toml       # 単一 file
    python3 tools/run_corpus.py tests/corpus/should_read/           # dir 再帰
    python3 tools/run_corpus.py --binary /path/to/furigana
    python3 tools/run_corpus.py --data-dir /var/lib/furigana        # 辞書を mount

ja-furigana CLI が PATH にある必要があります (`cargo install ja-furigana-cli` または
`furigana dict pull` 後の binary)。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS = REPO_ROOT / "tests" / "corpus" / "should_read.toml"


def find_furigana_binary(override: str | None) -> str:
    """`furigana` バイナリの解決。--binary > PATH > エラー."""
    if override:
        if not Path(override).is_file():
            sys.exit(f"[FAIL] --binary {override} が存在しません")
        return override
    found = shutil.which("furigana")
    if not found:
        sys.exit(
            "[FAIL] `furigana` バイナリが PATH に見つかりません。\n"
            "       `cargo install ja-furigana-cli` でインストールするか、\n"
            "       `--binary /path/to/furigana` で明示してください。"
        )
    return found


def run_lookup(binary: str, text: str, mode: str, data_dir: str | None) -> str:
    """`furigana lookup <text> --mode <mode>` を呼び出して stdout を返す."""
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


def collect_corpus_files(corpus_arg: Path) -> list[Path]:
    """corpus 引数を file / dir / 両者併合 として解決し、 toml file の list を返す。

    - file 指定: `[corpus_arg]` 単体。 同名 dir (`<stem>/`) が同階層にあれば併合
    - dir 指定: 再帰 `*.toml` 全部
    - file も dir も無い: SystemExit
    """
    files: list[Path] = []
    if corpus_arg.is_file():
        files.append(corpus_arg)
        # 同名 dir (例: should_read.toml + should_read/) が共存する場合は併合する
        sibling_dir = corpus_arg.with_suffix("")
        if sibling_dir.is_dir():
            files.extend(sorted(sibling_dir.rglob("*.toml")))
    elif corpus_arg.is_dir():
        files.extend(sorted(corpus_arg.rglob("*.toml")))
    else:
        # file が無くても dir があれば dir として扱う (例: `should_read.toml` 廃止後)
        sibling_dir = corpus_arg.with_suffix("")
        if sibling_dir.is_dir():
            files.extend(sorted(sibling_dir.rglob("*.toml")))
        else:
            sys.exit(f"[FAIL] corpus file/dir not found: {corpus_arg}")
    return files


def run_corpus(
    corpus_path: Path,
    binary: str,
    data_dir: str | None,
    *,
    verbose: bool,
) -> tuple[int, int, list[str]]:
    """corpus toml を読み出して全 case を実行、(passed, total, failures) を返す。

    `corpus_path` は file または dir。 dir の場合は配下 `*.toml` を再帰的に全部実行する。
    """
    files = collect_corpus_files(corpus_path)
    if not files:
        sys.exit(f"[FAIL] no toml files found under: {corpus_path}")

    if verbose or len(files) > 1:
        print(f"[info] corpus files ({len(files)}):")
        for f in files:
            print(f"  - {f}")
        print()

    failures: list[str] = []
    passed = 0
    case_index = 0
    for f in files:
        with f.open("rb") as fp:
            data = tomllib.load(fp)
        cases = data.get("case", [])
        if not cases:
            if verbose:
                print(f"[WARN] {f} に case がありません")
            continue

        for case in cases:
            case_index += 1
            text = case.get("input", "")
            mode = case.get("mode", "tts")
            expected = case.get("expected")
            note = case.get("note", "")
            # 新 schema (alpha.10+): [[case.targets]] で 1 例文内の N 個の対象語句を
            # (surface, reading) ペアで列挙。 expected の full match assertion とは別に
            # 各 target について「surface に対する reading が output 中に含まれるか」
            # の追加 assertion を行う。 backward compat: targets 無ければ skip。
            targets = case.get("targets") or []

            if expected is None and not targets:
                # should_not_read_yet / out_of_scope では expected_failure_reason を持つ
                # ことになっているので、 そちらは ここでは検証対象外として skip。
                continue

            actual = run_lookup(binary, text, mode, data_dir)

            # ── (1) full match (expected) ──
            full_match_ok = expected is None or actual == expected

            # ── (2) per-target match (substring) ──
            target_failures: list[str] = []
            for t in targets:
                if not isinstance(t, dict):
                    continue
                surf = t.get("surface")
                rdg = t.get("reading")
                if not (isinstance(surf, str) and isinstance(rdg, str)):
                    continue
                if rdg not in actual:
                    target_failures.append(
                        f"             - 対象 `{surf}` の reading `{rdg}` が output に含まれない"
                    )

            if full_match_ok and not target_failures:
                passed += 1
                if verbose:
                    tgt_note = f" + {len(targets)} target" if targets else ""
                    print(f"  [OK]   {case_index:>3}. {text!r} ({mode}){tgt_note} → {actual!r}")
            else:
                msg_parts = [f"  [FAIL] {case_index:>3}. {text!r} ({mode}) [{f.name}]"]
                if not full_match_ok:
                    msg_parts.append(f"           expected: {expected!r}")
                    msg_parts.append(f"           actual:   {actual!r}")
                if target_failures:
                    msg_parts.append("           target 検証失敗:")
                    msg_parts.extend(target_failures)
                if note:
                    msg_parts.append(f"           note:     {note}")
                msg = "\n".join(msg_parts)
                failures.append(msg)
                print(msg)

    total = passed + len(failures)
    return passed, total, failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ja-furigana の corpus 回帰テスト runner"
    )
    parser.add_argument(
        "corpus",
        nargs="?",
        type=Path,
        default=DEFAULT_CORPUS,
        help=(
            f"対象 corpus toml file または dir (default: "
            f"{DEFAULT_CORPUS.relative_to(REPO_ROOT)}、 同名 dir があれば併合)"
        ),
    )
    parser.add_argument(
        "--binary",
        help="furigana バイナリの絶対 path (default: PATH から探す)",
    )
    parser.add_argument(
        "--data-dir",
        help="furigana に渡す --data-dir (辞書 / ルールの mount 先)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="成功 case も逐一表示",
    )
    args = parser.parse_args()

    binary = find_furigana_binary(args.binary)
    print(f"[info] binary  : {binary}")
    print(f"[info] corpus  : {args.corpus}")
    if args.data_dir:
        print(f"[info] data-dir: {args.data_dir}")
    print()

    passed, total, failures = run_corpus(
        args.corpus, binary, args.data_dir, verbose=args.verbose
    )

    print()
    if failures:
        print(f"[FAIL] {len(failures)}/{total} 件失敗 ({passed} pass)")
        return 1
    if total == 0:
        print("[WARN] 検証対象の case が 0 件でした (`expected` 持ち case がない?)")
        return 0
    print(f"[OK] 全 {total} 件 pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
