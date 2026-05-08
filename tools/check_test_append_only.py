#!/usr/bin/env python3
"""
PR で `*.test.toml` の inline test case が **削除されていない** ことを検証する。

CONTRIBUTING.md の append-only ポリシーを構造的に強制 (= 削除した PR は CI fail):
- inline test は corpus と同じ regression lock として機能する
- 既存 case を削除すると過去通せていた変換が再度壊れたとき検出できなくなる
- reading が変わった場合は新 case を追加して、 古いものは残す方針

使い方:
    python tools/check_test_append_only.py --base-ref <base-sha-or-tag>

CI workflow から呼び出される (validate.yml の append-only job)。 base ref は
GitHub Actions context の `github.event.pull_request.base.sha` を渡す。

判定ロジック:
- PR base の master 状態と HEAD で `*.test.toml` を全 walk
- 各 file で `[[test]]` の (input, expected) set を計算
- base に存在した (input, expected) tuple が HEAD で **欠落** していたら fail
- HEAD で値が変わった (= 同 input で違う expected) のも実質削除なので fail
- 新規 file / 新規 case の追加は OK

`subprocess.run` は argv list + shell=False で shell injection 経路無し。
"""
from __future__ import annotations

import argparse
import io
import subprocess  # nosec B404 — fixed argv list, shell=False で安全
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def collect_test_files_at(ref: str) -> list[str]:
    """ref 時点で tracked な *.test.toml の repo 相対 path 一覧。"""
    result = subprocess.run(  # nosec B603 — fixed argv, no shell
        ["git", "ls-tree", "-r", "--name-only", ref],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [
        p for p in result.stdout.splitlines()
        if p.endswith(".test.toml")
        and (p.startswith("core/") or p.startswith("rules/"))
    ]


def file_at(ref: str, path: str) -> str | None:
    """ref:<path> の content を返す (無ければ None)。"""
    try:
        result = subprocess.run(  # nosec B603 — fixed argv, no shell
            ["git", "show", f"{ref}:{path}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def parse_cases(content: str) -> set[tuple[str, str]]:
    """`[[test]]` array から (input, expected) tuple set を抽出。"""
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return set()
    cases = data.get("test")
    if not isinstance(cases, list):
        return set()
    out: set[tuple[str, str]] = set()
    for c in cases:
        if not isinstance(c, dict):
            continue
        inp = c.get("input")
        exp = c.get("expected")
        if isinstance(inp, str) and isinstance(exp, str):
            out.add((inp, exp))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref",
        required=True,
        help="PR base の SHA or ref (例: github.event.pull_request.base.sha)",
    )
    args = parser.parse_args()

    # cp932 console 対策で stdout を UTF-8 強制
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    base_files = set(collect_test_files_at(args.base_ref))
    head_files: list[str] = []
    for sub in ("core", "rules"):
        base = ROOT / sub
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.test.toml")):
            head_files.append(p.relative_to(ROOT).as_posix())
    head_files_set = set(head_files)

    # base にあって HEAD で消えている file は file 単位の削除 → 全 case 削除扱い
    removed_files = sorted(base_files - head_files_set)

    violations: list[str] = []
    for path in removed_files:
        base_content = file_at(args.base_ref, path) or ""
        base_cases = parse_cases(base_content)
        if base_cases:
            violations.append(
                f"{path}: file 全削除 ({len(base_cases)} cases 喪失)"
            )

    # 共通 file の case 比較
    for path in sorted(base_files & head_files_set):
        base_cases = parse_cases(file_at(args.base_ref, path) or "")
        head_cases = parse_cases((ROOT / path).read_text(encoding="utf-8"))
        # base に居て HEAD に居ない (= 削除 or reading 変更) を検出
        missing = base_cases - head_cases
        if not missing:
            continue
        # reading 変更 (input は同じだが expected 違い) も別途 detect
        head_inputs = {inp for inp, _ in head_cases}
        for inp, exp in sorted(missing):
            if inp in head_inputs:
                head_exp = next(e for i, e in head_cases if i == inp)
                violations.append(
                    f"{path}: reading 変更 input={inp!r} (base: {exp} → HEAD: {head_exp})"
                )
            else:
                violations.append(f"{path}: case 削除 input={inp!r} expected={exp!r}")

    if not violations:
        print("[OK] inline test の append-only ポリシー pass")
        return

    print(
        f"[FAIL] inline test を削除 / 変更している ({len(violations)} 件)。\n"
        "       既存 case を消す PR は禁止 (regression lock のため)。\n"
        "       reading が変わった場合は新 case を追加して、 古い case は残してください。\n",
        file=sys.stderr,
    )
    for v in violations:
        print(f"  - {v}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
