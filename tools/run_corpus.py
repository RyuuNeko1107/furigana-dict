#!/usr/bin/env python3
# ruff: noqa: T201
"""
ja-furigana の corpus 回帰テスト runner。

`tests/corpus/should_read.toml` の各 case を、ローカルの `furigana` バイナリで実行して
expected と一致するか検証する。失敗があれば exit 1 で抜ける (CI gate 前提)。

Usage:
    python3 tools/run_corpus.py                       # should_read.toml を実行 (default)
    python3 tools/run_corpus.py tests/corpus/should_read.toml
    python3 tools/run_corpus.py --binary /path/to/furigana
    python3 tools/run_corpus.py --data-dir /var/lib/furigana    # 辞書を mount

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
        result = subprocess.run(  # noqa: S603 — fixed argv, no shell
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


def run_corpus(
    corpus_path: Path,
    binary: str,
    data_dir: str | None,
    *,
    verbose: bool,
) -> tuple[int, int, list[str]]:
    """corpus toml を読み出して全 case を実行、(passed, total, failures) を返す."""
    if not corpus_path.is_file():
        sys.exit(f"[FAIL] corpus file not found: {corpus_path}")

    with corpus_path.open("rb") as f:
        data = tomllib.load(f)

    cases = data.get("case", [])
    if not cases:
        print(f"[WARN] {corpus_path} に case がありません")
        return 0, 0, []

    failures: list[str] = []
    passed = 0
    for i, case in enumerate(cases, 1):
        text = case.get("input", "")
        mode = case.get("mode", "tts")
        expected = case.get("expected")
        note = case.get("note", "")

        if expected is None:
            # should_not_read_yet / out_of_scope では expected_failure_reason を持つ
            # ことになっているので、そちらは ここでは検証対象外として skip。
            continue

        actual = run_lookup(binary, text, mode, data_dir)
        if actual == expected:
            passed += 1
            if verbose:
                print(f"  [OK]   {i:>3}. {text!r} ({mode}) → {actual!r}")
        else:
            msg = (
                f"  [FAIL] {i:>3}. {text!r} ({mode})\n"
                f"           expected: {expected!r}\n"
                f"           actual:   {actual!r}"
            )
            if note:
                msg += f"\n           note:     {note}"
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
        help=f"対象 corpus toml (default: {DEFAULT_CORPUS.relative_to(REPO_ROOT)})",
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
