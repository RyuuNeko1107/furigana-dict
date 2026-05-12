#!/usr/bin/env python3
"""
STATS.md の自動生成セクションを再生成する。

STATS.md 内の 4 つのマーカー区間を埋め直す:
- AUTO-GENERATED:SUMMARY : サマリ table (core / rules / 合計)
- AUTO-GENERATED:CORE    : core/*.toml ファイル別 table
- AUTO-GENERATED:RULES   : rules/*.toml ファイル別 table
- AUTO-GENERATED:QA      : QA カバレッジ (corpus + inline test、 サイズは出さない)

加えて CONTRIBUTING.md 内の 1 つのマーカー区間も同 source で埋め直す:
- AUTO-GENERATED:PLACEMENT : 「追加したいもの → 配置 file」 quickpath table

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
CONTRIBUTING_MD = ROOT / "CONTRIBUTING.md"

# 全 dict / rule TOML は冒頭に `[meta] description = "..."` を持つことを前提。
# 念のため各 file が本当に description を持ってるか確認するための無き fallback も用意
# (counters / context は file 内 description あり、 単漢字 unihan は別経路で取得)。
DESCRIPTIONS_FALLBACK: dict[str, str] = {}


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

    優先順位: ファイル内 [meta].description → DESCRIPTIONS_FALLBACK
    → genre dir substring fallback → placeholder。
    """
    if not rel.endswith("*.toml"):
        path = ROOT / rel
        if path.is_file():
            desc = read_description(path)
            if desc is not None:
                return desc
    if rel in DESCRIPTIONS_FALLBACK:
        return DESCRIPTIONS_FALLBACK[rel]
    # genre dir substring fallback (counters / context は file 内 description
    # を持たない設計、 サブカテゴリは file 名で識別)
    if "/counters/" in rel:
        return "助数詞ルール (本 / 匹 / 個 / 年 / 月 / 日 …、 連濁 / 促音化 / kana 末尾置換)"
    if "/context/" in rel:
        return "文脈依存読み (一日→ツイタチ/イチニチ 等の同形異音語)"
    return "(用途未設定 — ファイル冒頭に `[meta] description = \"...\"` を追加)"


def count_entries(path: Path) -> int:
    """TOML の top-level エントリ数を返す。

    対応する形式:
    - [entries] / [map] dict   (jukugo, unihan, compat, units, symbols, numeric_phrases)
    - [[entry]] / [[rule]] / [[kanji]] array of tables (scales, postprocess, context/*, counters/*, kanji/*)
    - 直接 top-level に key=value が並ぶフラット形式 (days.toml: '1' = 'ツイタチ' ...)

    新 format ★A2 対応 (alpha.11): `[entries]` の値は string (Simple) でも
    table (Detailed) でも両方カウント、 `[[kanji]]` array は list 長で件数扱い。
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)
    for key in ("entries", "map"):
        if isinstance(data.get(key), dict):
            return len(data[key])
    for key in ("entry", "rule", "kanji"):
        if isinstance(data.get(key), list):
            return len(data[key])
    # フラット (days.toml 等)
    flat = sum(1 for v in data.values() if isinstance(v, str))
    if flat > 0:
        return flat
    # 子テーブル合計フォールバック ([meta] は管理用 table なので除外)
    return sum(len(v) for k, v in data.items() if isinstance(v, dict) and k != "meta")


def count_rule_patterns(path: Path) -> int:
    """rules file の **実 rule pattern 数** を返す (深掘り count)。

    `count_entries` は top-level エントリ (counter 名 / [[rule]] surface) を返すが、
    counters の `[[counter."X".rules]]` や context の `[[rule.match]]` のような内部
    配列要素は含めない。 こちらは内部までフラットに数えた合計を返す:

    - counters (`{counter."X" = {default, rules=[...]}}` 構造): counter 数 + 全 rules 合計
      (各 counter の default が 1 pattern + 各 rules 配列要素が 1 pattern)
    - context (`[[rule]]` array): rule 数 + 全 [[rule.match]] 合計
      (各 rule の surface が 1 pattern + 各 match が 1 branch)
    - 上記以外 (entries / map / 単純 [[rule]]): count_entries と同じ
    """
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return 0

    # counter 構造 (objects.toml / time.toml / 等)
    if isinstance(data.get("counter"), dict):
        counters = data["counter"]
        total = 0
        for _, c in counters.items():
            if not isinstance(c, dict):
                continue
            total += 1  # default 自体を 1 pattern として数える
            rules = c.get("rules")
            if isinstance(rules, list):
                total += len(rules)
        return total

    # context 構造 ([[rule]] array で各 rule に [[rule.match]] が複数)
    if isinstance(data.get("rule"), list):
        rules = data["rule"]
        # context で「surface + match の総数」= len(rules) + sum(match)
        # postprocess 等の単純 [[rule]] では match を持たないので len(rules) のみ
        total = len(rules)
        for r in rules:
            if isinstance(r, dict):
                m = r.get("match")
                if isinstance(m, list):
                    total += len(m)
        return total

    # それ以外は count_entries と同じ挙動 (entries / map / フラット)
    return count_entries(path)


def count_kanji_patterns(path: Path) -> int:
    """[[kanji]] format file の **block 数 + 全 [[kanji.match]] 合計** を返す。

    各 [[kanji]] block は char + default + 文脈分岐 [[kanji.match]] 配列を持つ。
    block 数は char 数 (= entries 数と同じ) だが、 ルール総数としては match の
    数も加算したい (= 文脈分岐の richness を可視化、 default reading + 各 match
    で 1 つの「ルール」 を消費するカウント)。

    [entries."X".match] 形式 (jukugo の Detailed entry 文脈分岐) も将来同じ思想で
    集計可能だが、 現状は kanji block のみ。
    """
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return 0
    kanji = data.get("kanji")
    if not isinstance(kanji, list):
        return count_entries(path)
    total = len(kanji)  # 各 block の default 自体を 1 ルールとして数える
    for k in kanji:
        if isinstance(k, dict):
            m = k.get("match")
            if isinstance(m, list):
                total += len(m)
    return total


def count_inline_tests(path: Path) -> int:
    """`<base>.toml` に対する隣接 `<base>.test.toml` の `[[test]]` 件数を返す。

    test file が存在しない / `[[test]]` array が無い / parse 失敗時は 0。
    """
    if path.name.endswith(".test.toml"):
        return 0
    test_path = path.with_suffix("").with_suffix(".test.toml")
    if not test_path.is_file():
        return 0
    try:
        with open(test_path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return 0
    cases = data.get("test")
    return len(cases) if isinstance(cases, list) else 0


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
    rows: list[tuple[str, int, int, int]] = []

    def collect(subdir: str, sort_by_count: bool = True) -> list[tuple[str, int, int, int]]:
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
            out.append((rel, count_entries(p), count_inline_tests(p), effective_bytes(p)))
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
    # ★A2 alpha.11: core/kanji/ ([[kanji]] block format、 旧 single_overrides の後継)
    rows.extend(collect("kanji"))
    p = ROOT / "core/_inbox.toml"
    if p.exists():
        rows.append(
            ("core/_inbox.toml", count_entries(p), count_inline_tests(p), effective_bytes(p))
        )
    # ★A2 alpha.11: core/single_overrides.toml は削除済 (= core/kanji/ に migration)、
    # ファイルが残っていれば旧 alpha 期 dict 互換のため取り込む (= 通常は不在)
    p = ROOT / "core/single_overrides.toml"
    if p.exists():
        rows.append(
            ("core/single_overrides.toml", count_entries(p), count_inline_tests(p), effective_bytes(p))
        )
    p = ROOT / "core/compat.toml"
    if p.exists():
        rows.append(
            ("core/compat.toml", count_entries(p), count_inline_tests(p), effective_bytes(p))
        )
    return rows


def gather_rules() -> list[tuple[str, int, int, int, int]]:
    """rules 配下の全 *.toml を再帰 walk で集めて (rel, count, patterns, test, size) を返す。

    新階層化 (rules/<genre>/<file>.toml or rules/<genre>/<sub>/<file>.toml) に
    対応。 _genre.toml と *.test.toml は集計対象外。 表示は gen_rules で
    genre dir 別 sub-section 化。

    `count` は top-level エントリ数 (counter 名 / [[rule]] surface 数 / [entries] key 数)、
    `patterns` は rule の深掘り count (counters の sub-rules、 context の match 含めた合計)。
    counters / context 以外では patterns == count。
    """
    rows: list[tuple[str, int, int, int, int]] = []
    base = ROOT / "rules"
    if not base.is_dir():
        return rows
    for p in sorted(base.rglob("*.toml")):
        if p.name == "_genre.toml" or p.name.endswith(".test.toml"):
            continue
        rel = p.relative_to(ROOT).as_posix()
        rows.append((
            rel,
            count_entries(p),
            count_rule_patterns(p),
            count_inline_tests(p),
            effective_bytes(p),
        ))
    return rows


def gen_summary(core_rows: list, rules_rows: list) -> str:
    """unihan / jukugo / works / compat / rules の 5 区分で表示 (性質が違うため分離)。

    works が空の場合は行を出さない (大半のケースで visual noise になるため)。
    """
    def slice_(prefix: str) -> tuple[int, int, int]:
        sub = [r for r in core_rows if r[0] == prefix or r[0].startswith(prefix)]
        return (
            sum(r[1] for r in sub),
            sum(r[2] for r in sub),
            sum(r[3] for r in sub),
        )

    unihan_c, _unihan_t, unihan_s = slice_("core/unihan/")
    jukugo_c, _jukugo_t, jukugo_s = slice_("core/jukugo/")
    works_c, _works_t, works_s = slice_("core/works/")
    loanwords_c, _loanwords_t, loanwords_s = slice_("core/loanwords/")
    kanji_c, _kanji_t, kanji_s = slice_("core/kanji/")
    inbox_c, _inbox_t, inbox_s = slice_("core/_inbox.toml")
    single_ov_c, _single_ov_t, single_ov_s = slice_("core/single_overrides.toml")
    compat_c, _compat_t, compat_s = slice_("core/compat.toml")
    rules_c = sum(r[1] for r in rules_rows)
    rules_s = sum(r[4] for r in rules_rows)
    total_c = unihan_c + jukugo_c + works_c + loanwords_c + kanji_c + inbox_c + single_ov_c + compat_c + rules_c
    total_s = unihan_s + jukugo_s + works_s + loanwords_s + kanji_s + inbox_s + single_ov_s + compat_s + rules_s

    # 内訳の sub-section heading に anchor link でジャンプ可能にする。
    # GitHub の auto-anchor は heading の slugify 結果。
    # テスト件数は別 section (## テストカバレッジ) に集約するため、 ここの table には含めない。
    lines = [
        "| カテゴリ | エントリ数 | サイズ |",
        "|---|---:|---:|",
        f"| [**単漢字**](#単漢字) (`core/unihan/*`、 水準別 5 ファイル) | **{unihan_c:,}** | **{fmt_size(unihan_s)}** |",
        f"| [**熟語**](#熟語) (`core/jukugo/*`、手動 PR メンテ) | **{jukugo_c:,}** | **{fmt_size(jukugo_s)}** |",
    ]
    if works_c > 0:
        lines.append(
            f"| [**作品造語**](#作品造語) (`core/works/*`、作品単位 1 ファイル) | **{works_c:,}** | **{fmt_size(works_s)}** |"
        )
    if loanwords_c > 0:
        lines.append(
            f"| [**外来語**](#外来語) (`core/loanwords/*`、IT 用語等の英字 surface) | **{loanwords_c:,}** | **{fmt_size(loanwords_s)}** |"
        )
    # inbox は普段空 (=0) でも存在を可視化したいので無条件で表示
    lines.append(
        f"| [**分類前 inbox**](#分類前-inbox) (`core/_inbox.toml`、 後で振り分ける一時置き場) | **{inbox_c:,}** | **{fmt_size(inbox_s)}** |"
    )
    if single_ov_c > 0:
        lines.append(
            f"| [**単漢字 override**](#単漢字-override) (`core/single_overrides.toml`、 issue #15 限定解) | **{single_ov_c:,}** | **{fmt_size(single_ov_s)}** |"
        )
    if kanji_c > 0:
        lines.append(
            f"| [**単漢字 [[kanji]] format**](#単漢字-kanji-format) (`core/kanji/*`、 default + 文脈分岐 reading) | **{kanji_c:,}** | **{fmt_size(kanji_s)}** |"
        )
    lines.extend([
        f"| [**異体字**](#異体字) (`core/compat.toml`) | **{compat_c:,}** | **{fmt_size(compat_s)}** |",
        f"| [**エンジンルール**](#エンジンルール) (`rules/`) | **{rules_c:,}** | **{fmt_size(rules_s)}** |",
        f"| **合計** | **{total_c:,}** | **{fmt_size(total_s)}** |",
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
    rows: list[tuple[str, int, int, int]],
) -> str:
    """1 カテゴリ分の sub-section (heading + 説明 + table) を返す。

    test 件数は別 section (## テストカバレッジ) に集約するため、 ここの table
    には含めない (rows tuple の tcount field は読み捨てる)。
    """
    lines = [f"### {title}", "", note, ""]
    if not rows:
        lines.append("(空)")
        return "\n".join(lines) + "\n"
    lines.append("| ファイル | エントリ数 | サイズ | 用途 |")
    lines.append("|---|---:|---:|---|")
    for rel, count, _tcount, size in rows:
        desc = lookup_description(rel)
        lines.append(
            f"| {link_rel(rel)} | {count:,} | {fmt_size(size)} | {desc} |"
        )
    if len(rows) > 1:
        n = sum(r[1] for r in rows)
        s = sum(r[3] for r in rows)
        lines.append(
            f"| **小計** ({len(rows)} ファイル) | **{n:,}** | **{fmt_size(s)}** | |"
        )
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
    groups: dict[str, list[tuple[str, int, int, int]]] = {}
    for rel, count, tcount, size in rows:
        # rel = "core/<subdir>/<genre>/<file>.toml" or "core/<subdir>/<file>.toml"
        parts = rel.split("/")
        if len(parts) >= 4:
            genre_key = parts[2]
        else:
            genre_key = ""  # flat 直下
        groups.setdefault(genre_key, []).append((rel, count, tcount, size))

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
    overall_s = sum(r[3] for r in rows)
    lines.append(
        f"**合計**: {overall_n:,} 件 / {fmt_size(overall_s)} (genre {len(ordered)} 区分)"
    )
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
        for rel, count, _tcount, size in files:
            d = lookup_description(rel)
            lines.append(
                f"| {link_rel(rel)} | {count:,} | {fmt_size(size)} | {d} |"
            )
        if len(files) > 1:
            n = sum(r[1] for r in files)
            s = sum(r[3] for r in files)
            lines.append(
                f"| **小計** ({len(files)} ファイル) | **{n:,}** | **{fmt_size(s)}** | |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def _gen_kanji_subsection(rows: list[tuple[str, int, int, int]]) -> str:
    """単漢字 [[kanji]] format 専用 subsection ([[kanji.match]] 数も別列で表示)。

    block 数 (= char 数) と pattern 数 (= block + match 配列合計) を別列で出すことで、
    「default だけ書いた block」 と 「文脈分岐多めの block」 の比率が見える。
    """
    title = "単漢字 [[kanji]] format"
    note = "`core/kanji/*` — 1 字 surface に対する `[[kanji]]` block 形式 entry。 各 block は `char` (1 字必須) + `default` reading + optional `[[kanji.match]]` 配列 (= 文脈分岐 reading、 matcher vocabulary は entry inline match と同一)。 「ルール数」 列は **block 数 + 各 [[kanji.match]] 合計** (= default + 文脈分岐の総ルール数)。"
    lines = [f"### {title}", "", note, ""]
    if not rows:
        lines.append("(空)")
        return "\n".join(lines) + "\n"
    lines.append("| ファイル | 文字数 | ルール数 | サイズ | 用途 |")
    lines.append("|---|---:|---:|---:|---|")
    total_count = 0
    total_patterns = 0
    total_size = 0
    for rel, count, _tcount, size in rows:
        patterns = count_kanji_patterns(ROOT / rel)
        desc = lookup_description(rel)
        lines.append(
            f"| {link_rel(rel)} | {count:,} | {patterns:,} | {fmt_size(size)} | {desc} |"
        )
        total_count += count
        total_patterns += patterns
        total_size += size
    if len(rows) > 1:
        lines.append(
            f"| **小計** ({len(rows)} ファイル) | **{total_count:,}** | **{total_patterns:,}** | **{fmt_size(total_size)}** | |"
        )
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
    kanji_rows = [r for r in core_rows if r[0].startswith("core/kanji/")]
    inbox_rows = [r for r in core_rows if r[0] == "core/_inbox.toml"]
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
            "`core/works/<medium>/*` — 媒体 (game / literature 等) ごとに 1 作品 1 ファイル。 原則は公式読み (一般通称として定着していれば採録可)、 出典コメント必須、 古典読みは現代読み無い場合のみ。",
            "works",
            works_rows,
        ))
    if loanwords_rows:
        sections.append(_gen_subsection(
            "外来語",
            "`core/loanwords/*` — ASCII surface (英字始まり) を完全一致 lookup する別管理辞書。 case-fold + 全角→半角 正規化。",
            loanwords_rows,
        ))
    sections.append(_gen_subsection(
        "分類前 inbox",
        "`core/_inbox.toml` — 「読みは追加したいが genre dir の振り分け判断付かない」 用の一時置き場。 lib 側は `[meta] role = \"jukugo\"` で jukugo として load される (≥2 字 surface 限定)。 maintainer の整理タイミングで適切な `core/jukugo/<genre>/<file>.toml` に移動する。",
        inbox_rows,
    ))
    if single_rows:
        sections.append(_gen_subsection(
            "単漢字 override",
            "`core/single_overrides.toml` — 1 字 surface に対する明示的 default 上書き ([issue #15](https://github.com/RyuuNeko1107/ja-furigana/issues/15) の限定解、 lib Step 4 で Lindera reading より優先)。",
            single_rows,
        ))
    if kanji_rows:
        sections.append(_gen_kanji_subsection(kanji_rows))
    sections.append(_gen_subsection(
        "異体字",
        "`core/compat.toml` — 異体字 → 標準字の正規化マッピング (例: 髙→高)。 reading lookup 前の前処理として lib が参照。",
        compat_rows,
    ))

    return "\n".join(sections)


def gen_rules(rules_rows: list[tuple[str, int, int, int, int]]) -> str:
    """rules 内訳を genre dir (`rules/<genre>/...`) 単位で sub-section 化。

    各 file の rel = `rules/<genre>/<sub?>/<file>.toml`。 第 2 segment (genre)
    で group 化、 各 genre dir 直下の `_genre.toml` から heading + description を
    引く (jukugo / works と同じ仕組み)。 genre dir 内に subdir (例 counters)
    がある場合は file 一覧にそのまま並べる (path 先頭の `rules/<genre>/` は
    link_rel が省略せずに表示)。

    各 file 行は **エントリ数** (top-level) と **ルール数** (深掘り pattern count) の
    両方を出す。 counters / context 以外は同値。
    """
    if not rules_rows:
        return "(空)\n"

    # group by 第 2 segment (= genre dir 名)
    groups: dict[str, list[tuple[str, int, int, int, int]]] = {}
    for row in rules_rows:
        rel = row[0]
        parts = rel.split("/")
        # rel = "rules/<genre>/..." → parts[1] が genre
        genre_key = parts[1] if len(parts) >= 3 else ""
        groups.setdefault(genre_key, []).append(row)

    # genre meta を読んで order でソート
    ordered: list[tuple[int, str, dict | None, list]] = []
    for key, files in groups.items():
        if key:
            meta = load_genre_meta(ROOT / "rules" / key)
            order = meta.get("order", 999) if meta else 999
        else:
            meta = None
            order = 9999
        ordered.append((order, key, meta, files))
    ordered.sort(key=lambda t: (t[0], t[1]))

    overall_n = sum(r[1] for r in rules_rows)
    overall_p = sum(r[2] for r in rules_rows)
    overall_s = sum(r[4] for r in rules_rows)
    lines = [
        f"**合計**: {overall_n:,} エントリ / {overall_p:,} ルール / {fmt_size(overall_s)} (genre {len(ordered)} 区分)",
        "",
    ]

    for _, key, meta, files in ordered:
        files = sorted(files, key=lambda r: -r[2])
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
            lines.append(f"`rules/{key}/` — {len(files)} ファイル")
        else:
            lines.append(f"`rules/` 直下 — {len(files)} ファイル")
        lines.append("")
        lines.append("| ファイル | エントリ数 | ルール数 | サイズ | 用途 |")
        lines.append("|---|---:|---:|---:|---|")
        for rel, count, patterns, _tcount, size in files:
            d = lookup_description(rel)
            lines.append(
                f"| {link_rel(rel)} | {count:,} | {patterns:,} | {fmt_size(size)} | {d} |"
            )
        if len(files) > 1:
            n = sum(r[1] for r in files)
            p = sum(r[2] for r in files)
            s = sum(r[4] for r in files)
            lines.append(
                f"| **小計** ({len(files)} ファイル) | **{n:,}** | **{p:,}** | **{fmt_size(s)}** | |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def gather_inline_tests() -> list[tuple[str, str, int]]:
    """全 *.test.toml を再帰 walk して (rel, parent_rel, case_count) を返す。

    parent_rel は隣接する本体 file (例: `objects.test.toml` → `objects.toml`) の
    relpath。 親 file が存在しない孤立 test file は parent_rel = "" (防御的)。
    test 系 file は release tar から exclude されるためサイズは集計しない。
    """
    rows: list[tuple[str, str, int]] = []
    for base in (ROOT / "core", ROOT / "rules"):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.test.toml")):
            rel = p.relative_to(ROOT).as_posix()
            try:
                with open(p, "rb") as f:
                    data = tomllib.load(f)
            except (OSError, tomllib.TOMLDecodeError):
                cases = []
            else:
                raw = data.get("test")
                cases = raw if isinstance(raw, list) else []
            parent = p.with_suffix("").with_suffix(".toml")
            parent_rel = (
                parent.relative_to(ROOT).as_posix() if parent.is_file() else ""
            )
            rows.append((rel, parent_rel, len(cases)))
    return rows


def gather_corpus() -> dict[str, list[tuple[str, int]]]:
    """corpus toml の case 数を bucket 別 (should_read / should_not_read_yet / out_of_scope)
    に集計して返す。 値は (rel, case_count) の list。

    bucket 判定: file 名 (or 親 dir 名) に bucket 名を含むかで分類。
    `tests/corpus/should_read.toml` も `tests/corpus/should_read/<topic>.toml` も同じ
    "should_read" bucket。 release tar から exclude されるためサイズは集計しない。
    """
    buckets = {"should_read": [], "should_not_read_yet": [], "out_of_scope": []}
    base = ROOT / "tests" / "corpus"
    if not base.is_dir():
        return buckets
    for p in sorted(base.rglob("*.toml")):
        rel = p.relative_to(ROOT).as_posix()
        # bucket 判定: rel に bucket 名 (file or dir 名として) を含むか
        bucket = None
        for name in buckets:
            if f"/{name}.toml" in f"/{rel}" or f"/{name}/" in f"/{rel}":
                bucket = name
                break
        if bucket is None:
            continue
        try:
            with open(p, "rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            cases = []
        else:
            raw = data.get("case")
            cases = raw if isinstance(raw, list) else []
        # expected があるものだけ実行対象 case として数える (should_not_read_yet /
        # out_of_scope は expected_failure_reason のみで expected を持たない)
        actionable = sum(1 for c in cases if isinstance(c, dict) and "expected" in c)
        buckets[bucket].append((rel, actionable))
    return buckets


def gen_qa(
    corpus_buckets: dict[str, list[tuple[str, int]]],
    inline_tests: list[tuple[str, str, int]],
) -> str:
    """QA カバレッジ section (corpus + inline test 統合)。 サイズ列は出さない。

    test 系 file は release tar から exclude / lib runtime memory にも乗らないため、
    case 数のみが意味のある metric。
    """
    lines: list[str] = []

    # ── corpus (回帰) ──
    total_should_read = sum(c for _, c in corpus_buckets["should_read"])
    total_pending = sum(c for _, c in corpus_buckets["should_not_read_yet"])
    total_oos = sum(c for _, c in corpus_buckets["out_of_scope"])

    lines.append("### Corpus (回帰)")
    lines.append("")
    lines.append(
        f"**合計**: should_read {total_should_read} ケース / "
        f"should_not_read_yet {total_pending} ケース / "
        f"out_of_scope {total_oos} ケース"
    )
    lines.append("")
    lines.append("| バケット | ファイル | ケース数 |")
    lines.append("|---|---|---:|")
    for bucket_name in ("should_read", "should_not_read_yet", "out_of_scope"):
        files = corpus_buckets[bucket_name]
        if not files:
            lines.append(f"| `{bucket_name}` | _(無し)_ | 0 |")
            continue
        for i, (rel, count) in enumerate(files):
            label = f"`{bucket_name}`" if i == 0 else ""
            lines.append(f"| {label} | {link_rel(rel)} | {count} |")
    lines.append("")

    # ── inline test ──
    lines.append("### Inline test (`*.test.toml`)")
    lines.append("")
    if not inline_tests:
        lines.append("_inline test はまだ 1 件も書かれていない。_")
        lines.append("詳細は [`docs/INLINE_TESTS.md`](docs/INLINE_TESTS.md) を参照。")
        return "\n".join(lines) + "\n"

    total_inline = sum(c for _, _, c in inline_tests)
    lines.append(
        f"**合計**: {len(inline_tests)} ファイル / {total_inline} ケース"
    )
    lines.append("")
    lines.append("| テストファイル | 対象本体 | ケース数 |")
    lines.append("|---|---|---:|")
    for rel, parent, count in inline_tests:
        parent_link = link_rel(parent) if parent else "(孤立)"
        lines.append(f"| {link_rel(rel)} | {parent_link} | {count} |")
    return "\n".join(lines) + "\n"


def gen_placement(
    core_rows: list[tuple[str, int, int, int]],
    rules_rows: list[tuple[str, int, int, int, int]],
) -> str:
    """CONTRIBUTING.md の「追加したいもの → 配置 file」 quickpath table。

    現在の dir 構成 / file 数 / genre 名 から動的に生成する (構造変化に追随)。
    用途別に行を作って、 各 file 数や genre 名を実数で埋める。
    """

    # ── core 側 ──
    jukugo_genres = sorted({
        rel.split("/")[2] for rel, *_ in core_rows
        if rel.startswith("core/jukugo/") and len(rel.split("/")) >= 4
    })
    # unihan は水準順 (joyo → jinmeiyou → jis_basic → jis_supplement → extension) で表示
    # 利用頻度の高い順なので、 alphabetical sort で並べ替えると意味が変わる
    unihan_level_order = {
        "joyo": 0, "jinmeiyou": 1, "jis_basic": 2,
        "jis_supplement": 3, "extension": 4,
    }
    unihan_levels = sorted(
        [
            rel.split("/")[-1].removesuffix(".toml")
            for rel, *_ in core_rows
            if rel.startswith("core/unihan/")
        ],
        key=lambda lv: unihan_level_order.get(lv, 999),
    )
    works_media = sorted({
        rel.split("/")[2] for rel, *_ in core_rows
        if rel.startswith("core/works/") and len(rel.split("/")) >= 4
    })
    loanwords_files = sorted([
        rel.split("/")[-1].removesuffix(".toml")
        for rel, *_ in core_rows
        if rel.startswith("core/loanwords/")
    ])
    has_inbox = any(rel == "core/_inbox.toml" for rel, *_ in core_rows)
    has_single_overrides = any(
        rel == "core/single_overrides.toml" for rel, *_ in core_rows
    )

    # ── rules 側 ──
    counters_files = sorted([
        rel.split("/")[-1].removesuffix(".toml")
        for rel, *_ in rules_rows
        if "/counters/" in rel
    ])
    context_files = sorted([
        rel.split("/")[-1].removesuffix(".toml")
        for rel, *_ in rules_rows
        if "/context/" in rel
    ])

    lines = [
        "| 追加したいもの | 配置 | 補足 |",
        "|---|---|---|",
    ]

    if jukugo_genres:
        lines.append(
            f"| **熟語** (≥ 2 字 surface) | [`core/jukugo/<genre>/<file>.toml`](core/jukugo/) | "
            f"genre {len(jukugo_genres)} 区分 ({' / '.join(jukugo_genres)})、 "
            f"内訳は [STATS.md](STATS.md#熟語) |"
        )
    if has_inbox:
        lines.append(
            "| **熟語 (genre 判断付かない)** | [`core/_inbox.toml`](core/_inbox.toml) | "
            "一時 inbox、 maintainer が後で振り分け |"
        )
    if unihan_levels:
        lines.append(
            f"| **単漢字** (1 字 surface) | [`core/unihan/<水準>.toml`](core/unihan/) | "
            f"{len(unihan_levels)} 水準 ({' / '.join(unihan_levels)}) |"
        )
    if has_single_overrides:
        lines.append(
            "| **単漢字 default override** | [`core/single_overrides.toml`](core/single_overrides.toml) | "
            "[issue #15](https://github.com/RyuuNeko1107/ja-furigana/issues/15) の限定解 (1 字 surface 限定) |"
        )
    lines.append(
        "| **異体字 → 標準字** | [`core/compat.toml`](core/compat.toml) | "
        "lib Step 1 で入力テキストを正規化 |"
    )
    if loanwords_files:
        lines.append(
            f"| **外来語** (英字始まり surface) | [`core/loanwords/<file>.toml`](core/loanwords/) | "
            f"{len(loanwords_files)} file ({' / '.join(loanwords_files)})、 完全一致 lookup |"
        )
    if works_media:
        lines.append(
            f"| **作品造語** (作品単位 1 ファイル) | [`core/works/<medium>/<title>.toml`](core/works/) | "
            f"medium {len(works_media)} 区分 ({' / '.join(works_media)})、 "
            f"サブポリシー: [`core/works/README.md`](core/works/README.md) |"
        )
    if counters_files:
        lines.append(
            f"| **助数詞ルール** | [`rules/numbers/counters/<file>.toml`](rules/numbers/counters/) | "
            f"{len(counters_files)} file ({' / '.join(counters_files)})、 連濁 / 促音化 / kana 末尾置換 |"
        )
    lines.append(
        "| **数字慣用語句** | [`rules/numbers/numeric_phrases.toml`](rules/numbers/numeric_phrases.toml) | "
        "二十歳→ハタチ 等、 助数詞ルールより先に確定 |"
    )
    if context_files:
        lines.append(
            f"| **文脈依存読み** | [`rules/context/<file>.toml`](rules/context/) | "
            f"{len(context_files)} file ({' / '.join(context_files)})、 同形異音語の動的読み分け |"
        )
    lines.append(
        "| **後処理 regex** | [`rules/text/postprocess.toml`](rules/text/postprocess.toml) | "
        "mode 別 (hiragana / ruby / tts / romaji) の出力直前 regex 置換 |"
    )
    lines.append(
        "| **記号 / SI 単位 / 大数** | "
        "[`rules/text/{symbols,units}.toml`](rules/text/) / "
        "[`rules/numbers/scales.toml`](rules/numbers/scales.toml) | "
        "単純 surface→reading mapping |"
    )

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
    inline_tests = gather_inline_tests()
    corpus_buckets = gather_corpus()

    # ── STATS.md ──
    text = STATS_MD.read_text(encoding="utf-8")
    text = replace_marker(text, "SUMMARY", gen_summary(core_rows, rules_rows))
    text = replace_marker(text, "CORE", gen_core(core_rows))
    text = replace_marker(text, "RULES", gen_rules(rules_rows))
    text = replace_marker(text, "QA", gen_qa(corpus_buckets, inline_tests))
    STATS_MD.write_text(text, encoding="utf-8")

    # ── CONTRIBUTING.md (placement quickpath) ──
    contrib_text = CONTRIBUTING_MD.read_text(encoding="utf-8")
    contrib_text = replace_marker(
        contrib_text, "PLACEMENT", gen_placement(core_rows, rules_rows)
    )
    CONTRIBUTING_MD.write_text(contrib_text, encoding="utf-8")

    core_count = sum(r[1] for r in core_rows)
    rules_count = sum(r[1] for r in rules_rows)
    inline_cases = sum(c for _, _, c in inline_tests)
    corpus_cases = sum(
        c for files in corpus_buckets.values() for _, c in files
    )
    print(
        f"regenerated STATS.md + CONTRIBUTING.md (core={core_count:,} / rules={rules_count:,} / "
        f"corpus={corpus_cases} / inline_tests={inline_cases})"
    )


if __name__ == "__main__":
    main()
