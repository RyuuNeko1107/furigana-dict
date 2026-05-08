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
    "core/single_overrides.toml": "単漢字 default reading override (issue #15 限定解、 Lindera reading より優先)",
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


def effective_bytes(path: Path) -> int:
    """コメント行 (`#` 始まり) と空行を除いた UTF-8 bytes。

    ja-furigana lib (`toml::from_str` + serde Deserialize) は parse 時に
    コメント / 空行 / セクション区切り を破棄して、 entries の key→value
    だけを `HashMap<String, String>` に乗せる。 STATS.md の disk file size
    そのままだと利用者が memory 使用量を実態より大きく見積もる原因になる
    ため、 ここでは parse 後 memory に届く部分に **近似** する形で
    コメント / 空行を除外して bytes を数える。

    inline comment は ja-furigana-dict 内で使われていないため考慮しない。
    HashMap overhead や entries 以外 (`[meta]` 等) は本概算に含む — つまり
    「parse 入力として実質的に意味を持つ bytes」 のオーダー測定。
    """
    total = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            total += len(line.encode("utf-8"))
    return total


def gather_core() -> list[tuple[str, int, int]]:
    """core 配下の (relpath, count, size_bytes) を返す。

    順序: unihan → jukugo (件数 desc) → works (件数 desc) → compat。
    jukugo / works はどちらも全階層を再帰スキャン (ja-furigana 0.1.0-alpha.6
    以降の loader と挙動を揃える)。
    """
    rows: list[tuple[str, int, int]] = []

    def collect(subdir: str, sort_by_count: bool = True) -> list[tuple[str, int, int]]:
        base = ROOT / "core" / subdir
        if not base.is_dir():
            return []
        out = []
        for p in sorted(base.glob("**/*.toml")):
            # _genre.toml (STATS sub-section description) と *.test.toml (CI 専用 inline test)
            # は dict entries を持たないので集計対象外。
            if p.name == "_genre.toml" or p.name.endswith(".test.toml"):
                continue
            rel = p.relative_to(ROOT).as_posix()
            out.append((rel, count_entries(p), effective_bytes(p)))
        if sort_by_count:
            out.sort(key=lambda r: -r[1])
        return out

    # unihan/ は water level 順で表示したいので sort_by_count=False
    # (joyo → jinmeiyou → jis_basic → jis_supplement → extension)
    unihan_order = {
        "core/unihan/joyo.toml": 0,
        "core/unihan/jinmeiyou.toml": 1,
        "core/unihan/jis_basic.toml": 2,
        "core/unihan/jis_supplement.toml": 3,
        "core/unihan/extension.toml": 4,
    }
    unihan_rows = collect("unihan", sort_by_count=False)
    unihan_rows.sort(key=lambda r: unihan_order.get(r[0], 999))
    rows.extend(unihan_rows)
    rows.extend(collect("jukugo"))
    rows.extend(collect("works"))
    rows.extend(collect("loanwords"))
    p = ROOT / "core/single_overrides.toml"
    if p.exists():
        rows.append(("core/single_overrides.toml", count_entries(p), effective_bytes(p)))
    p = ROOT / "core/compat.toml"
    if p.exists():
        rows.append(("core/compat.toml", count_entries(p), effective_bytes(p)))
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
            rows.append((f"rules/{fname}", count_entries(p), effective_bytes(p)))
    for subdir, label in (("counters", "rules/counters/*.toml"),
                          ("context", "rules/context/*.toml")):
        files = sorted((ROOT / "rules" / subdir).glob("*.toml"))
        if not files:
            continue
        total_count = sum(count_entries(p) for p in files)
        total_size = sum(effective_bytes(p) for p in files)
        rows.append((label, total_count, total_size, len(files)))
    return rows


def gen_summary(core_rows: list, rules_rows: list) -> str:
    """unihan / jukugo / works / compat / rules の 5 区分で表示 (性質が違うため分離)。

    works が空の場合は行を出さない (大半のケースで visual noise になるため)。
    """
    def slice_(prefix: str) -> tuple[int, int]:
        sub = [r for r in core_rows if r[0] == prefix or r[0].startswith(prefix)]
        return sum(r[1] for r in sub), sum(r[2] for r in sub)

    unihan_count, unihan_size = slice_("core/unihan/")
    jukugo_count, jukugo_size = slice_("core/jukugo/")
    works_count, works_size = slice_("core/works/")
    loanwords_count, loanwords_size = slice_("core/loanwords/")
    single_ov_count, single_ov_size = slice_("core/single_overrides.toml")
    compat_count, compat_size = slice_("core/compat.toml")
    rules_count = sum(r[1] for r in rules_rows)
    rules_size = sum(r[2] for r in rules_rows)
    total_count = (
        unihan_count + jukugo_count + works_count + loanwords_count
        + single_ov_count + compat_count + rules_count
    )
    total_size = (
        unihan_size + jukugo_size + works_size + loanwords_size
        + single_ov_size + compat_size + rules_size
    )

    # 内訳の sub-section heading に anchor link でジャンプ可能にする。
    # GitHub の auto-anchor は heading の slugify 結果。
    lines = [
        "| カテゴリ | エントリ数 | サイズ |",
        "|---|---:|---:|",
        f"| [**単漢字**](#単漢字) (`core/unihan/*`、 水準別 5 ファイル) | **{unihan_count:,}** | **{fmt_size(unihan_size)}** |",
        f"| [**熟語**](#熟語) (`core/jukugo/*`、手動 PR メンテ) | **{jukugo_count:,}** | **{fmt_size(jukugo_size)}** |",
    ]
    if works_count > 0:
        lines.append(
            f"| [**作品造語**](#作品造語) (`core/works/*`、作品単位 1 ファイル) | **{works_count:,}** | **{fmt_size(works_size)}** |"
        )
    if loanwords_count > 0:
        lines.append(
            f"| [**外来語**](#外来語) (`core/loanwords/*`、IT 用語等の英字 surface) | **{loanwords_count:,}** | **{fmt_size(loanwords_size)}** |"
        )
    if single_ov_count > 0:
        lines.append(
            f"| [**単漢字 override**](#単漢字-override) (`core/single_overrides.toml`、 issue #15 限定解) | **{single_ov_count:,}** | **{fmt_size(single_ov_size)}** |"
        )
    lines.extend([
        f"| [**異体字**](#異体字) (`core/compat.toml`) | **{compat_count:,}** | **{fmt_size(compat_size)}** |",
        f"| [**エンジンルール**](#エンジンルール) (`rules/`) | **{rules_count:,}** | **{fmt_size(rules_size)}** |",
        f"| **合計** | **{total_count:,}** | **{fmt_size(total_size)}** |",
    ])
    return "\n".join(lines) + "\n"


def link_rel(rel: str) -> str:
    """relpath を markdown link 化。 glob (`*` 含む) は親ディレクトリに向ける。"""
    if "*" in rel:
        dir_part = rel.rsplit("/", 1)[0] + "/"
        return f"[`{rel}`]({dir_part})"
    return f"[`{rel}`]({rel})"


def _gen_subsection(
    title: str,
    note: str,
    rows: list[tuple[str, int, int]],
) -> str:
    """1 カテゴリ分の sub-section (heading + 説明 + table) を返す。"""
    lines = [f"### {title}", "", note, ""]
    if not rows:
        lines.append("(空)")
        return "\n".join(lines) + "\n"
    lines.append("| ファイル | エントリ数 | サイズ | 用途 |")
    lines.append("|---|---:|---:|---|")
    for rel, count, size in rows:
        desc = lookup_description(rel)
        lines.append(f"| {link_rel(rel)} | {count:,} | {fmt_size(size)} | {desc} |")
    if len(rows) > 1:
        n = sum(r[1] for r in rows)
        s = fmt_size(sum(r[2] for r in rows))
        lines.append(f"| **小計** ({len(rows)} ファイル) | **{n:,}** | **{s}** | |")
    return "\n".join(lines) + "\n"


def load_genre_meta(dir_path: Path) -> dict | None:
    """dir 内の `_genre.toml` の `[genre]` table を返す。 無ければ None。"""
    f = dir_path / "_genre.toml"
    if not f.is_file():
        return None
    try:
        with open(f, "rb") as fp:
            data = tomllib.load(fp)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    g = data.get("genre")
    return g if isinstance(g, dict) else None


def _gen_grouped_section(
    title: str,
    note: str,
    base_subdir: str,
    rows: list[tuple[str, int, int]],
) -> str:
    """jukugo / works のような genre dir 階層を持つカテゴリの sub-section。

    各 rows を `core/<base_subdir>/<genre>/<file>.toml` の `<genre>` で group 化、
    `_genre.toml` の `[genre]` メタから heading と description を引いて
    h4 sub-sub-section として出力。 各 group 内の table は count desc。
    `<genre>` = "" (= subdir 直下に flat 置き) の rows は最後にまとめる。
    """
    base = ROOT / "core" / base_subdir
    lines = [f"### {title}", "", note, ""]
    if not rows:
        lines.append("(空)")
        return "\n".join(lines) + "\n"

    # group by genre dir 名
    groups: dict[str, list[tuple[str, int, int]]] = {}
    for rel, count, size in rows:
        # rel = "core/<subdir>/<genre>/<file>.toml" or "core/<subdir>/<file>.toml"
        parts = rel.split("/")
        if len(parts) >= 4:
            genre_key = parts[2]
        else:
            genre_key = ""  # flat 直下
        groups.setdefault(genre_key, []).append((rel, count, size))

    # genre meta を読んで order でソート
    ordered: list[tuple[int, str, dict | None, list]] = []
    for key, files in groups.items():
        if key:
            meta = load_genre_meta(base / key)
            order = meta.get("order", 999) if meta else 999
        else:
            meta = None
            order = 9999
        ordered.append((order, key, meta, files))
    ordered.sort(key=lambda t: (t[0], t[1]))

    overall_n = sum(r[1] for r in rows)
    overall_s = fmt_size(sum(r[2] for r in rows))
    lines.append(f"**合計**: {overall_n:,} 件 / {overall_s} (genre {len(ordered)} 区分)")
    lines.append("")

    for _, key, meta, files in ordered:
        files = sorted(files, key=lambda r: -r[1])
        if meta and meta.get("name"):
            heading = meta["name"]
            desc = meta.get("description", "")
        elif key:
            heading = key
            desc = ""
        else:
            heading = "(直下)"
            desc = ""
        lines.append(f"#### {heading}")
        lines.append("")
        if desc:
            lines.append(desc)
            lines.append("")
        if key:
            lines.append(f"`core/{base_subdir}/{key}/` — {len(files)} ファイル")
        else:
            lines.append(f"`core/{base_subdir}/` 直下 — {len(files)} ファイル")
        lines.append("")
        lines.append("| ファイル | エントリ数 | サイズ | 用途 |")
        lines.append("|---|---:|---:|---|")
        for rel, count, size in files:
            d = lookup_description(rel)
            lines.append(f"| {link_rel(rel)} | {count:,} | {fmt_size(size)} | {d} |")
        if len(files) > 1:
            n = sum(r[1] for r in files)
            s = fmt_size(sum(r[2] for r in files))
            lines.append(f"| **小計** ({len(files)} ファイル) | **{n:,}** | **{s}** | |")
        lines.append("")

    return "\n".join(lines) + "\n"


def gen_core(core_rows: list) -> str:
    """core 内訳をカテゴリ別 sub-section に分割して出力。

    sub-section heading は GitHub auto-anchor に乗せやすいシンプルな日本語のみ
    (`### 単漢字` 等)。 summary 表の link は `#単漢字` 等の同名 anchor を指す。
    熟語 / 作品造語 はさらに genre dir 単位で h4 sub-sub-section に分割
    (`_genre.toml` の `[genre]` メタを heading + description として参照)。
    """
    unihan_rows = [r for r in core_rows if r[0].startswith("core/unihan/")]
    jukugo_rows = [r for r in core_rows if r[0].startswith("core/jukugo/")]
    works_rows = [r for r in core_rows if r[0].startswith("core/works/")]
    loanwords_rows = [r for r in core_rows if r[0].startswith("core/loanwords/")]
    single_rows = [r for r in core_rows if r[0] == "core/single_overrides.toml"]
    compat_rows = [r for r in core_rows if r[0] == "core/compat.toml"]

    sections = []
    sections.append(_gen_subsection(
        "単漢字",
        "`core/unihan/*` — 水準別 5 ファイル。 lib の resolve_reading 6 段階で最終 fallback (Step 6) として参照される。 default reading review は使用頻度の高い `joyo.toml` を中心に。",
        unihan_rows,
    ))
    sections.append(_gen_grouped_section(
        "熟語",
        "`core/jukugo/<genre>/*` — 手動 PR メンテのジャンル別 jukugo (≥ 2 字 surface)。 lib の Step 3 (jukugo lookup) で Lindera より優先採用。 各 genre dir の `_genre.toml` がカテゴリ description を持つ。",
        "jukugo",
        jukugo_rows,
    ))
    if works_rows:
        sections.append(_gen_grouped_section(
            "作品造語",
            "`core/works/<medium>/*` — 媒体 (game / literature 等) ごとに 1 作品 1 ファイル。 公式読みのみ採録、 出典コメント必須、 二次創作読み禁止のサブポリシー。",
            "works",
            works_rows,
        ))
    if loanwords_rows:
        sections.append(_gen_subsection(
            "外来語",
            "`core/loanwords/*` — ASCII surface (英字始まり) を完全一致 lookup する別管理辞書。 case-fold + 全角→半角 正規化。",
            loanwords_rows,
        ))
    if single_rows:
        sections.append(_gen_subsection(
            "単漢字 override",
            "`core/single_overrides.toml` — 1 字 surface に対する明示的 default 上書き ([issue #15](https://github.com/RyuuNeko1107/ja-furigana/issues/15) の限定解、 lib Step 4 で Lindera reading より優先)。",
            single_rows,
        ))
    sections.append(_gen_subsection(
        "異体字",
        "`core/compat.toml` — 異体字 → 標準字の正規化マッピング (例: 髙→高)。 reading lookup 前の前処理として lib が参照。",
        compat_rows,
    ))

    return "\n".join(sections)


def gen_rules(rules_rows: list) -> str:
    lines = ["| ファイル | エントリ数 | サイズ | 内容 |", "|---|---:|---:|---|"]
    for row in rules_rows:
        rel, count, size = row[0], row[1], row[2]
        desc = lookup_description(rel)
        if len(row) > 3:
            display = f"{link_rel(rel)} ({row[3]} ファイル)"
        else:
            display = link_rel(rel)
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
