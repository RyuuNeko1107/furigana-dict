#!/usr/bin/env python3
"""
core/jukugo/general.toml の entries をカテゴリへ機械的に振り分ける (メンテナ専用)。

方針 (保守的):
- 単漢字 (key 1 字)             → general から削除 (unihan が正典)
  - reading が unihan と本質的に異なる (kata/hira 正規化後でも不一致) なら
    unihan 側を general の値で上書き (本番 override を伝播、情報損失なし)
- 4 字 + 全部 CJK 漢字           → four_char.toml (四字熟語) へ
- 末尾が地名接尾語              → place_names.toml へ (誤分類しやすい一般語はブラックリスト)
- それ以外 (人名 / 固有名詞 / 一般語) → general.toml に残置 (機械判定だと誤分類率が高いので手動 PR で別途)

使い方:
    python tools/classify_jukugo.py            # dry-run (差分のサマリだけ表示、ファイルは触らない)
    python tools/classify_jukugo.py --apply    # 実ファイルに反映

要 Python 3.11+ (tomllib)。
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 末尾がこれで終われば「地名」候補 (3 字以上を要求して誤分類を避ける)。
# 「○○道」「○○島」「○○原」のような誤分類しやすい接尾語は PLACE_BLACKLIST で個別除外する。
PLACE_SUFFIXES = (
    # 都道府県・行政区分 (確実)
    '都', '道', '府', '県', '市', '区', '町', '村', '郡',
    # 交通
    '駅', '港', '空港',
    # 宗教施設 (実質地名)
    '神社', '寺',
    # 地名要素 (一般語と被るのでブラックリスト併用)
    '島', '原', '街道', '城',
)

# 接尾語ベースで地名と判定されるが実は一般語 / 抽象語 / 武芸名のもの。
# 完全一致でブラックリスト (key 全体がここにあれば地名扱いしない)。
PLACE_BLACKLIST = {
    # 武道・芸道系の「○○道」
    '合気道', '弓道', '剣道', '書道', '茶道', '華道', '柔道', '空手道',
    '居合道', '香道', '武士道', '極道',
    # 「○○道」の抽象 / 制度 / 一般語
    '王道', '邪道', '報道', '軌道', '鉄道', '国道', '県道', '林道',
    '山道', '高速道', '横道', '修羅道', '人道', '王道楽土',
    '一本道', '抜け道', '近道', '回り道', '寄り道', '夜道', '山道',
    '通り道', '一筋道', '別道', '小道', '近道', '裏道',
    # 「○○島」一般語
    '半島', '列島', '群島', '諸島', '孤島', '無人島',
    # 「○○原」一般語
    '平原', '草原', '砂原', '高原', '雪原', '湿原', '河原', '荒原',
    '樹海原', '広原',
}


def looks_like_place(surface: str) -> bool:
    if surface in PLACE_BLACKLIST:
        return False
    # 単漢字や 2 字以下は判定しない (誤分類リスク)
    if len(surface) < 3:
        return False
    for suffix in PLACE_SUFFIXES:
        if surface.endswith(suffix):
            return True
    return False


import re

# 全角 CJK 漢字 (基本 + 拡張 A + CJK 互換 + 々) のみで構成されているか
KANJI_ONLY_RE = re.compile(r'^[㐀-䶿一-鿿豈-﫿々]+$')


def is_all_kanji(s: str) -> bool:
    return bool(s) and bool(KANJI_ONLY_RE.fullmatch(s))


def looks_like_four_char(surface: str) -> bool:
    """四字熟語: 4 字 + 全部 CJK 漢字。
    地名 (秋葉原 / 北海道 等の 3 字以上) と被らないよう、四字限定。
    """
    return len(surface) == 4 and is_all_kanji(surface)


def normalize_kana(s: str) -> str:
    """カタカナ → ひらがなで比較用キーを作る。
    「ハス」と「はす」を同一視する用途。
    """
    out: list[str] = []
    for c in s:
        cp = ord(c)
        if 0x30A1 <= cp <= 0x30F3:  # ァ - ン
            out.append(chr(cp - 0x60))
        elif c == 'ヴ':
            out.append('ゔ')
        else:
            out.append(c)
    return ''.join(out)


def load_entries(path: Path, section: str = 'entries') -> dict[str, str]:
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text(encoding='utf-8'))
    table = data.get(section, {})
    if not isinstance(table, dict):
        return {}
    return {k: v for k, v in table.items() if isinstance(v, str)}


def extract_header(path: Path, section_marker: str) -> str:
    if not path.exists():
        return ''
    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    out: list[str] = []
    for line in lines:
        out.append(line)
        if line.strip() == section_marker:
            return ''.join(out)
    return ''


def toml_quote(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')


def write_entries(path: Path, entries: dict[str, str], default_header: str | None = None) -> None:
    fallback = default_header or '[entries]\n'
    header = extract_header(path, '[entries]') or fallback
    if not header.endswith('\n'):
        header += '\n'
    body = ''.join(f'"{toml_quote(k)}" = "{toml_quote(entries[k])}"\n' for k in sorted(entries))
    path.write_text(header + body, encoding='utf-8')


def main(argv: list[str]) -> int:
    apply = '--apply' in argv

    general_path = ROOT / 'core' / 'jukugo' / 'general.toml'
    places_path = ROOT / 'core' / 'jukugo' / 'place_names.toml'
    four_char_path = ROOT / 'core' / 'jukugo' / 'four_char.toml'
    unihan_path = ROOT / 'core' / 'unihan.toml'

    general = load_entries(general_path)
    places = load_entries(places_path)
    four_char_existing = load_entries(four_char_path)
    unihan = load_entries(unihan_path)

    moved_to_places: dict[str, str] = {}
    moved_to_four_char: dict[str, str] = {}
    dropped_singles: dict[str, str] = {}
    unihan_overrides: dict[str, tuple[str, str]] = {}  # surface → (general_reading, old_unihan_reading)
    new_general: dict[str, str] = {}

    for surface, reading in general.items():
        if len(surface) == 1:
            # 単漢字 → unihan が正典。general からは落とす。
            dropped_singles[surface] = reading
            # ただし general と unihan の reading が「kata/hira 正規化後でも違う」場合は
            # 本番 override の意図 (ryuuneko.com TTS で自然な読み) を unihan に伝播。
            if surface in unihan and normalize_kana(unihan[surface]) != normalize_kana(reading):
                unihan_overrides[surface] = (reading, unihan[surface])
            continue
        if looks_like_four_char(surface):
            moved_to_four_char[surface] = reading
            continue
        if looks_like_place(surface):
            moved_to_places[surface] = reading
            continue
        new_general[surface] = reading

    print(f"## 振り分け結果 (dry-run)" if not apply else "## 振り分け実行")
    print(f"general 元エントリ数:          {len(general)}")
    print(f"  → 単漢字削除:                 {len(dropped_singles)} (うち unihan 上書き {len(unihan_overrides)} 件)")
    print(f"  → four_char へ移動:           {len(moved_to_four_char)}")
    print(f"  → place_names へ移動:         {len(moved_to_places)}")
    print(f"  → general に残置:             {len(new_general)}")
    print(f"four_char 既存:               {len(four_char_existing)}")
    print(f"four_char 結合後:             {len(four_char_existing) + len(moved_to_four_char)} (重複あれば置換)")
    print(f"places 既存:                  {len(places)}")
    print(f"places 結合後:                {len(places) + len(moved_to_places)} (重複あれば置換)")
    print(f"unihan 既存:                  {len(unihan)}")
    print(f"unihan 上書き後:              {len(unihan)} (件数は変わらず、{len(unihan_overrides)} 件の reading 更新)")
    print()
    if unihan_overrides:
        print(f"[INFO] 本番 override を unihan に伝播 ({len(unihan_overrides)} 件):")
        for s, (gen_r, uni_r) in sorted(unihan_overrides.items()):
            print(f"    {s}: unihan {uni_r!r} → {gen_r!r} (general から)")
        print()
    if moved_to_four_char:
        print(f"four_char へ移動 (最初 15 / {len(moved_to_four_char)} 件):")
        for s, r in list(sorted(moved_to_four_char.items()))[:15]:
            print(f"    {s} → {r}")
        print()
    if moved_to_places:
        print(f"places へ移動 ({len(moved_to_places)} 件):")
        for s, r in sorted(moved_to_places.items()):
            print(f"    {s} → {r}")
        print()

    if not apply:
        print("※ dry-run のみ。実ファイル更新は --apply を付けて再実行してください。")
        return 0

    # apply
    merged_places = {**places, **moved_to_places}
    merged_four_char = {**four_char_existing, **moved_to_four_char}
    write_entries(places_path, merged_places)
    write_entries(
        four_char_path,
        merged_four_char,
        default_header=(
            "# 四字熟語 (4 字 + 全部 CJK 漢字)\n"
            "#\n"
            "# 「一期一会」「四面楚歌」「優柔不断」 等。\n"
            "# 一般的な二字 / 三字熟語は general.toml、固有名詞は proper_nouns.toml に。\n"
            "#\n"
            "# - key (表層): ダブルクォート必須\n"
            "# - value (読み): ひらがな または 全角カタカナ (慣習: 訓=ひら / 音=カタ)\n"
            "# - 50 音順 を推奨 (PR diff が読みやすい)\n"
            "\n"
            "[entries]\n"
        ),
    )
    write_entries(general_path, new_general)

    # unihan: 既存に general 由来の override を上書き
    new_unihan = dict(unihan)
    for s, (gen_r, _old) in unihan_overrides.items():
        new_unihan[s] = gen_r
    if unihan_overrides:
        write_entries(unihan_path, new_unihan)

    print(f"[OK] 書き換え完了:")
    print(f"   {general_path}:   {len(general)} → {len(new_general)} entries")
    print(f"   {four_char_path}: {len(four_char_existing)} → {len(merged_four_char)} entries")
    print(f"   {places_path}:    {len(places)} → {len(merged_places)} entries")
    if unihan_overrides:
        print(f"   {unihan_path}:   {len(unihan_overrides)} 件の reading 更新")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
