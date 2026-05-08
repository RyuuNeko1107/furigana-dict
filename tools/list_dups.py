#!/usr/bin/env python3
"""
core/jukugo/*.toml と core/works/**/*.toml の cross-file 重複を検出して
STATS_DUPS.md に markdown レポートとして書き出す。

2 セクション:
- ## ⚠️ 異なる reading: validate.py が CI で fail させる対象 (修正必須)
- ## 同一 reading: 実害なし (jukugo merge で同値が後勝ち)、整理目安として list 化

CI から呼び出し想定: regen-stats workflow と並走。
exit code 0 = OK (生成成功)、 1 = I/O エラー等。

要 Python 3.11+ (tomllib)。
"""
from __future__ import annotations

import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'STATS_DUPS.md'


def normalize_kata(s: str) -> str:
    """ひらがな → 全角カタカナ正規化 (ja-furigana 内部の merge と同等価判定)。"""
    return ''.join(chr(ord(c) + 0x60) if 'ぁ' <= c <= 'ゖ' else c for c in s)


def gather() -> dict[str, list[tuple[str, str]]]:
    """jukugo / works 配下の (relpath, reading) を surface ごとに集める。"""
    seen: dict[str, list[tuple[str, str]]] = defaultdict(list)
    targets: list[Path] = []
    # jukugo / works とも genre dir 階層 (core/jukugo/<genre>/*.toml) があるので再帰。
    # _genre.toml (STATS sub-section description) と *.test.toml (CI 専用 inline test)
    # は dict entries を持たないので skip。
    def keep(p: Path) -> bool:
        return p.name != '_genre.toml' and not p.name.endswith('.test.toml')
    targets.extend(p for p in sorted((ROOT / 'core' / 'jukugo').glob('**/*.toml')) if keep(p))
    targets.extend(p for p in sorted((ROOT / 'core' / 'works').glob('**/*.toml')) if keep(p))
    for f in targets:
        with open(f, 'rb') as fp:
            data = tomllib.load(fp)
        rel = f.relative_to(ROOT).as_posix()
        for k, v in data.get('entries', {}).items():
            if isinstance(v, str):
                seen[k].append((rel, v))
    return seen


def main() -> int:
    seen = gather()
    same: list[tuple[str, list[tuple[str, str]]]] = []
    diverging: list[tuple[str, list[tuple[str, str]]]] = []
    for surface, lst in sorted(seen.items()):
        if len(lst) <= 1:
            continue
        normalized = {normalize_kata(r) for _, r in lst}
        if len(normalized) > 1:
            diverging.append((surface, lst))
        else:
            same.append((surface, lst))

    lines: list[str] = []
    lines.append('# Cross-file duplicates (`core/jukugo/` + `core/works/`)')
    lines.append('')
    lines.append('> `tools/list_dups.py` で自動生成。 commit 前にこのファイルが pull できれば')
    lines.append('> どのファイルのどの surface が cross-file 重複してるか一目で分かる。')
    lines.append('> divergent reading は `tools/validate.py` が CI で fail させる (修正必須)。')
    lines.append('')

    lines.append(f'## ⚠️ 異なる reading ({len(diverging)} 件 — critical)')
    lines.append('')
    if diverging:
        lines.append('CI で `validate.py` が fail させる。 同一 surface に複数読みが共存すると')
        lines.append('`Dict::from_toml_dir` の後勝ち merge でファイル名 alphabetical の末尾側が')
        lines.append('prevail し、 動作が予測不能になるため修正必須。')
        lines.append('')
        lines.append('| surface | files / readings |')
        lines.append('|---|---|')
        for surface, lst in diverging:
            details = ' · '.join(f'`{f}` → {r}' for f, r in lst)
            lines.append(f'| {surface} | {details} |')
    else:
        lines.append('(なし — divergent reading 0 件、 健全)')
    lines.append('')

    lines.append(f'## 同一 reading ({len(same)} 件)')
    lines.append('')
    lines.append('実害なし (jukugo merge で同値が上書きされても reading 不変)。 整理目安として list 化。')
    lines.append('長期的にどちらか 1 ファイルに寄せたいケースを発見する用。')
    lines.append('')
    if same:
        lines.append('| surface | reading | files |')
        lines.append('|---|---|---|')
        for surface, lst in same:
            reading = lst[0][1]
            files = ', '.join(f'`{f}`' for f, _ in lst)
            lines.append(f'| {surface} | {reading} | {files} |')
    else:
        lines.append('(なし)')
    lines.append('')

    try:
        OUT.write_text('\n'.join(lines), encoding='utf-8')
    except OSError as e:
        print(f'[FAIL] {OUT} 書き込み失敗: {e}', file=sys.stderr)
        return 1
    print(f'[OK] {OUT.name} regenerated (divergent={len(diverging)}, same={len(same)})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
