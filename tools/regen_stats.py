#!/usr/bin/env python3
"""
STATS.md の自動生成セクションを再生成する。

STATS.md 内の 3 つのマーカー区間を埋め直す:
- AUTO-GENERATED:SUMMARY : サマリ table (core / rules / 合計)
- AUTO-GENERATED:CORE    : core/*.toml ファイル別 table
- AUTO-GENERATED:RULES   : rules/*.toml ファイル別 table

用途列は **各 TOML ファイル先頭の `[meta] description = "..."`** から自動取得する。
ファイルに [meta] が無い場合は legacy fallback の DESCRIPTIONS dict を引く
(rules/*.toml や core/unihan.toml 等、構造が違って [meta] 入れにくいもの用)。

新規 TOML を追加したら、ファイル冒頭に以下を入れるだけで OK:

    [meta]
    description = "<カテゴリの 1 行説明>"

    [entries]
    ...

CI (`.github/workflows/regen-stats.yml`) は master push 時にこのスクリプトを走らせ、
diff があれば `chore: regen STATS.md [skip stats]` として auto-commit する。
contributor は手元で実行不要 (任意で実行は可、CI と同じ挙動)。

要 Python 3.11+ (tomllib)。
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATS_MD = ROOT / "STATS.md"

# Legacy fallback: ファイルに [meta] description が無い時に使う用途説明。
# 主に rules/*.toml や core/unihan.toml 等、[meta] テーブルを足しにくい
# ファイル用 (rules は構造が複雑、unihan は機械生成 dump)。
# 通常の jukugo / works ファイルは [meta] description で書く。
DESCRIPTIONS_FALLBACK: dict[str, str] = {
    "core/unihan.toml": "単漢字フォールバック (初期 seed + override 14 件)",
    "core/compat.toml": "異体字 → 標準字 (髙→高 等)",
    "rules/days.toml": "1〜31 日の特殊読み (1→ツイタチ 等)",
    "rules/scales.toml": "万 / 億 / 兆 / 京 等の大数スケール",
    "rules/units.toml": "SI 単位 (km / kg / mL …、case-insensitive)",
    "rules/symbols.toml": "記号読み (+ / − / % / ‰ …)",
    "rules/latin.toml": "ラテン文字読み (A→エー …)",
    "rules/numeric_phrases.toml": "数字を含む例外語句 (二十歳→ハタチ 等)",
    "rules/postprocess.toml": "後処理 regex 置換 (Step 7、mode 別)",
    "rules/counters/*.toml": "助数詞ルール (本 / 匹 / 個 / 年 / 月 / 日 …、連濁 / 促音化 / kana 末尾置換)",
    "rules/context/*.toml": "文脈依存読み (一日→ツイタチ/イチニチ 等)",
}


def read_description(path: Path) -> str | None:
    """ファイルの `[meta] description = "..."` を返す。無ければ None。"""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    meta = data.get("meta")
    if isinstance(meta, dict):
        desc = meta.get("description")
        if isinstance(desc, str) and desc:
            return desc
    return None


def lookup_description(rel: str) -> str:
    """relpath に対する用途説明を解決する。

    優先順位: ファイル内 [meta].description → DESCRIPTIONS_FALLBACK → placeholder。
    rules/counters/*.toml のような集約パターンは fallback dict のみ参照。
    """
    if not rel.endswith("*.toml"):
        path = ROOT / rel
        if path.is_file():
            desc = read_description(path)
            if desc is not None:
                return desc
    if rel in DESCRIPTIONS_FALLBACK:
        return DESCRIPTIONS_FALLBACK[rel]
    return "(用途未設定 — ファイル冒頭に `[meta] description = \"...\"` を追加)"


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
    if kb < 1024:
        return f"{round(kb)} KB"
    mb = kb / 1024
    return f"{mb:.2f} MB"


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
        f"| **単漢字** (`core/unihan.toml`、seed) | **{unihan_count:,}** | **{fmt_size(unihan_size)}** |",
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
        desc = lookup_description(rel)
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
        desc = lookup_description(rel)
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
