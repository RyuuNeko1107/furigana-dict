#!/usr/bin/env python3
"""
STATS.md の自動生成セクションを再生成する。

STATS.md 内の 3 つのマーカー区間を埋め直す:
- AUTO-GENERATED:SUMMARY : サマリ table (core / rules / 合計)
- AUTO-GENERATED:CORE    : core/*.toml ファイル別 table
- AUTO-GENERATED:RULES   : rules/*.toml ファイル別 table

用途列は下記 DESCRIPTIONS に記載 (件数 / サイズは自動算出)。
新規 TOML を追加したら DESCRIPTIONS にエントリを足すこと
(無い場合は placeholder が表示される)。

CI では再生成後 `git diff --exit-code STATS.md` で stale 検知に使う。

要 Python 3.11+ (tomllib)。
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATS_MD = ROOT / "STATS.md"

# 用途説明 (件数 / サイズは自動算出するのでここでは書かない)
DESCRIPTIONS: dict[str, str] = {
    "core/unihan.toml": "単漢字フォールバック (本番 ryuuneko.com 由来 + override 14 件)",
    "core/compat.toml": "異体字 → 標準字 (髙→高 等)",
    "core/jukugo/general.toml": "二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む)",
    "core/jukugo/four_char.toml": "四字熟語 (4 字 + 全 CJK 漢字)",
    "core/jukugo/place_names.toml": "地名 (47 都道府県 / 主要都市 / 駅 / 寺社仏閣 / 観光地)",
    "core/jukugo/personal_names.toml": "人名 (戦国 / 平安 / 江戸 / 明治大正 / 古典作家、現代私人除く)",
    "core/jukugo/proper_nouns.toml": "固有名詞 (大学 / 中央官庁 / 元号 / 歴史的事象、PR 募集中)",
    "core/jukugo/animals.toml": "動植物 / 魚介 / 鳥 / 昆虫 / 茸 / 海藻の難読",
    "core/jukugo/foods.toml": "食べ物 / 料理 / 和菓子 / 郷土料理 / 食材 / 調味料",
    "core/jukugo/specialized.toml": "専門用語 (医学 / 軍事 / 法学 / 経済 / IT / 工学)",
    "core/jukugo/body_parts.toml": "体の部位 / 内臓 / 骨格 / 筋肉 / 神経",
    "core/jukugo/weather.toml": "気象 / 天候 / 季語的気象 / 二十四節気 / 海洋気象",
    "core/jukugo/colors.toml": "色名 / 染色 / 模様 / 古典色 / 鉱物色",
    "core/jukugo/arts.toml": "古典芸能 / 武道 / 茶華香 / 工芸",
    "core/jukugo/abstracts.toml": "美意識 / 古典文学 / 仏教 / 儒教 / 思想",
    "core/jukugo/vehicles.toml": "乗り物 / 交通手段 / 船舶 / 航空 / 鉄道",
    "core/jukugo/clothes.toml": "衣服 / 装束 / アクセサリー / 履物",
    "core/jukugo/architecture.toml": "建築 / 建造物 / 寺社建築 / 城郭 / 庭園",
    "core/jukugo/literature.toml": "古典文学 / 作品名 / 文学用語 / 詩歌 / 評論",
    "core/jukugo/science.toml": "自然科学 (天文 / 物理 / 化学 / 生物 / 地学)",
    "core/jukugo/emotions.toml": "感情 / 心理状態 / 性格 / 心情",
    "core/jukugo/idioms.toml": "慣用句 / ことわざ / 故事成語 (フレーズ単位)",
    "core/jukugo/politics.toml": "政治 / 行政 / 立法 / 司法 / 国際関係",
    "core/jukugo/religions.toml": "神道 / 仏教 / キリスト教 / イスラム / 儀礼",
    "core/jukugo/music.toml": "音楽ジャンル / 楽典 / 楽器 / 演奏 / 音楽用語",
    "core/jukugo/sports.toml": "近代スポーツ / 球技 / 陸上 / 水泳 / 体操 / 大会",
    "core/works/game/touhou.toml": "東方Project (上海アリス幻樂団): キャラクター名 / 場所 / 用語 (公式読みベース)",
    "rules/days.toml": "1〜31 日の特殊読み (1→ツイタチ 等)",
    "rules/scales.toml": "万 / 億 / 兆 / 京 等の大数スケール",
    "rules/units.toml": "SI 単位 (km / kg / mL …、case-insensitive)",
    "rules/symbols.toml": "記号読み (+ / − / % / ‰ …)",
    "rules/latin.toml": "ラテン文字読み (A→エー …)",
    "rules/numeric_phrases.toml": "数字を含む例外語句 (二十歳→ハタチ 等)",
    "rules/postprocess.toml": "後処理 regex 置換 (本番 Step 7 互換)",
    "rules/counters/*.toml": "助数詞ルール (本 / 匹 / 個 / 年 / 月 / 日 …、連濁 / 促音化 / kana 末尾置換)",
    "rules/context/*.toml": "文脈依存読み (一日→ツイタチ/イチニチ 等)",
}


def count_entries(path: Path) -> int:
    """TOML の top-level エントリ数を返す。

    対応する形式:
    - [entries] / [map] dict   (jukugo, unihan, compat, units, latin, symbols, numeric_phrases)
    - [[entry]] / [[rule]] array of tables  (scales, postprocess, context/*, counters/*)
    - 直接 top-level に key=value が並ぶフラット形式 (days.toml: '1' = 'ツイタチ' ...)
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)
    for key in ("entries", "map"):
        if isinstance(data.get(key), dict):
            return len(data[key])
    for key in ("entry", "rule"):
        if isinstance(data.get(key), list):
            return len(data[key])
    # フラット (days.toml 等)
    flat = sum(1 for v in data.values() if isinstance(v, str))
    if flat > 0:
        return flat
    # 子テーブル合計フォールバック
    return sum(len(v) for v in data.values() if isinstance(v, dict))


def fmt_size(n_bytes: int) -> str:
    if n_bytes < 1024:
        return f"{n_bytes} B"
    kb = n_bytes / 1024
    if kb < 10:
        return f"{kb:.1f} KB"
    return f"{round(kb)} KB"


def gather_core() -> list[tuple[str, int, int]]:
    """core 配下の (relpath, count, size_bytes) を返す。

    順序: unihan → jukugo (件数 desc) → works (件数 desc) → compat。
    jukugo / works はどちらも全階層を再帰スキャン (ja-furigana 0.1.0-alpha.6
    以降の loader と挙動を揃える)。
    """
    rows: list[tuple[str, int, int]] = []
    p = ROOT / "core/unihan.toml"
    if p.exists():
        rows.append(("core/unihan.toml", count_entries(p), p.stat().st_size))

    def collect(subdir: str) -> list[tuple[str, int, int]]:
        base = ROOT / "core" / subdir
        if not base.is_dir():
            return []
        out = []
        for p in sorted(base.glob("**/*.toml")):
            rel = p.relative_to(ROOT).as_posix()
            out.append((rel, count_entries(p), p.stat().st_size))
        out.sort(key=lambda r: -r[1])
        return out

    rows.extend(collect("jukugo"))
    rows.extend(collect("works"))
    p = ROOT / "core/compat.toml"
    if p.exists():
        rows.append(("core/compat.toml", count_entries(p), p.stat().st_size))
    return rows


def gather_rules() -> list[tuple]:
    """rules 配下を返す。3-tuple (single file) または 4-tuple (集約された subdir) が混在。"""
    rows: list[tuple] = []
    flat_order = (
        "days.toml", "scales.toml", "units.toml", "symbols.toml",
        "latin.toml", "numeric_phrases.toml", "postprocess.toml",
    )
    for fname in flat_order:
        p = ROOT / "rules" / fname
        if p.exists():
            rows.append((f"rules/{fname}", count_entries(p), p.stat().st_size))
    for subdir, label in (("counters", "rules/counters/*.toml"),
                          ("context", "rules/context/*.toml")):
        files = sorted((ROOT / "rules" / subdir).glob("*.toml"))
        if not files:
            continue
        total_count = sum(count_entries(p) for p in files)
        total_size = sum(p.stat().st_size for p in files)
        rows.append((label, total_count, total_size, len(files)))
    return rows


def gen_summary(core_rows: list, rules_rows: list) -> str:
    """unihan / jukugo / works / compat / rules の 5 区分で表示 (性質が違うため分離)。

    works が空の場合は行を出さない (大半のケースで visual noise になるため)。
    """
    def slice_(prefix: str) -> tuple[int, int]:
        sub = [r for r in core_rows if r[0] == prefix or r[0].startswith(prefix)]
        return sum(r[1] for r in sub), sum(r[2] for r in sub)

    unihan_count, unihan_size = slice_("core/unihan.toml")
    jukugo_count, jukugo_size = slice_("core/jukugo/")
    works_count, works_size = slice_("core/works/")
    compat_count, compat_size = slice_("core/compat.toml")
    rules_count = sum(r[1] for r in rules_rows)
    rules_size = sum(r[2] for r in rules_rows)
    total_count = unihan_count + jukugo_count + works_count + compat_count + rules_count
    total_size = unihan_size + jukugo_size + works_size + compat_size + rules_size

    lines = [
        "| カテゴリ | エントリ数 | サイズ |",
        "|---|---:|---:|",
        f"| **単漢字** (`core/unihan.toml`、本番 dump) | **{unihan_count:,}** | **{fmt_size(unihan_size)}** |",
        f"| **熟語** (`core/jukugo/*`、手動 PR メンテ) | **{jukugo_count:,}** | **{fmt_size(jukugo_size)}** |",
    ]
    if works_count > 0:
        lines.append(
            f"| **作品造語** (`core/works/*`、作品単位 1 ファイル) | **{works_count:,}** | **{fmt_size(works_size)}** |"
        )
    lines.extend([
        f"| **異体字** (`core/compat.toml`) | **{compat_count:,}** | **{fmt_size(compat_size)}** |",
        f"| **エンジンルール** (`rules/`) | **{rules_count:,}** | **{fmt_size(rules_size)}** |",
        f"| **合計** | **{total_count:,}** | **{fmt_size(total_size)}** |",
    ])
    return "\n".join(lines) + "\n"


def gen_core(core_rows: list) -> str:
    lines = ["| ファイル | エントリ数 | サイズ | 用途 |", "|---|---:|---:|---|"]
    for rel, count, size in core_rows:
        desc = DESCRIPTIONS.get(rel, "(用途未設定 — `tools/regen_stats.py` DESCRIPTIONS に追加)")
        lines.append(f"| `{rel}` | {count:,} | {fmt_size(size)} | {desc} |")
    total_count = sum(r[1] for r in core_rows)
    total_size = sum(r[2] for r in core_rows)
    jukugo_rows = [r for r in core_rows if r[0].startswith("core/jukugo/")]
    works_rows = [r for r in core_rows if r[0].startswith("core/works/")]
    breakdown_parts = []
    if jukugo_rows:
        n = sum(r[1] for r in jukugo_rows)
        s = fmt_size(sum(r[2] for r in jukugo_rows))
        breakdown_parts.append(f"jukugo: {len(jukugo_rows)} ファイル / **{n:,} 件** / {s}")
    if works_rows:
        n = sum(r[1] for r in works_rows)
        s = fmt_size(sum(r[2] for r in works_rows))
        breakdown_parts.append(f"works: {len(works_rows)} ファイル / **{n:,} 件** / {s}")
    breakdown = " ・ ".join(breakdown_parts)
    lines.append(
        f"| **小計** | **{total_count:,}** | **{fmt_size(total_size)}** | "
        f"({breakdown}) |"
    )
    return "\n".join(lines) + "\n"


def gen_rules(rules_rows: list) -> str:
    lines = ["| ファイル | エントリ数 | サイズ | 内容 |", "|---|---:|---:|---|"]
    for row in rules_rows:
        rel, count, size = row[0], row[1], row[2]
        desc = DESCRIPTIONS.get(rel, "(用途未設定)")
        if len(row) > 3:
            display = f"`{rel}` ({row[3]} ファイル)"
        else:
            display = f"`{rel}`"
        lines.append(f"| {display} | {count:,} | {fmt_size(size)} | {desc} |")
    total_count = sum(r[1] for r in rules_rows)
    total_size = sum(r[2] for r in rules_rows)
    lines.append(f"| **小計** | **{total_count:,}** | **{fmt_size(total_size)}** | |")
    return "\n".join(lines) + "\n"


def replace_marker(text: str, marker: str, content: str) -> str:
    pattern = re.compile(
        rf"(<!-- AUTO-GENERATED:{marker}:BEGIN -->\n)(.*?)(<!-- AUTO-GENERATED:{marker}:END -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"marker pair not found in STATS.md: {marker}")
    return pattern.sub(lambda m: m.group(1) + content + m.group(3), text)


def main() -> None:
    core_rows = gather_core()
    rules_rows = gather_rules()
    text = STATS_MD.read_text(encoding="utf-8")
    text = replace_marker(text, "SUMMARY", gen_summary(core_rows, rules_rows))
    text = replace_marker(text, "CORE", gen_core(core_rows))
    text = replace_marker(text, "RULES", gen_rules(rules_rows))
    STATS_MD.write_text(text, encoding="utf-8")
    core_count = sum(r[1] for r in core_rows)
    rules_count = sum(r[1] for r in rules_rows)
    print(f"regenerated STATS.md (core={core_count:,} / rules={rules_count:,})")


if __name__ == "__main__":
    main()
