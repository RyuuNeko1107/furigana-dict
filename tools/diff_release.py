#!/usr/bin/env python3
"""
前回 tag と今回 tag (or HEAD) の TOML 辞書差分を集計して markdown を出力。

release.yml workflow から呼ばれて release notes に同梱される。

usage:
    python tools/diff_release.py <prev-tag> <now-tag-or-HEAD>

両 tag 時点のファイル内容を `git show <tag>:<path>` で取得 → tomllib で
parse → entries (= surface→reading) を比較。 集計対象は core/ + rules/ 配下
の `[entries]` / `[map]` を持つ TOML。 `_genre.toml` / `*.test.toml` は対象外。

出力 (stdout、 markdown、 すべて table 形式):

    # ja-furigana-dict release diff: <prev> → <now>

    ## 集計
    | 項目 | 値 |
    | 追加 entries | +N |
    | ...

    ## 新規 file / 削除 file (table)

    ## 詳細 (file 別、 追加 / 削除 / 読み変更 を table で)

    ## リリース時点スナップショット (now tag 時点の全 file + entries 数)

`subprocess.run` は argv list + shell=False で shell injection 経路無し。
"""
from __future__ import annotations

import subprocess  # nosec B404 — fixed argv list, shell=False で安全
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def git_show(tag: str, path: str) -> str | None:
    """`git show <tag>:<path>` を返す。 tag 時点で path が存在しなければ None。"""
    try:
        result = subprocess.run(  # nosec B603 — fixed argv, no shell
            ["git", "show", f"{tag}:{path}"],
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


def git_ls_all(tag: str) -> list[str]:
    """tag 時点で tracked な全 file path を返す (raw)。"""
    result = subprocess.run(  # nosec B603 — fixed argv, no shell
        ["git", "ls-tree", "-r", "--name-only", tag],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.splitlines()


def git_ls_files(tag: str) -> list[str]:
    """tag 時点で tracked な core/ + rules/ 配下の *.toml file 一覧を返す。

    `_genre.toml` (STATS sub-section description) と `*.test.toml` (CI 専用 inline test)
    は集計対象外なので除外。
    """
    return [
        p for p in git_ls_all(tag)
        if (p.startswith("core/") or p.startswith("rules/"))
        and p.endswith(".toml")
        and not p.endswith("_genre.toml")
        and not p.endswith(".test.toml")
    ]


def load_genre_meta_at_tag(tag: str, dir_rel: str) -> dict | None:
    """tag 時点の `<dir_rel>/_genre.toml` の `[genre]` table を返す。 無ければ None。"""
    content = git_show(tag, f"{dir_rel}/_genre.toml")
    if not content:
        return None
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return None
    g = data.get("genre")
    return g if isinstance(g, dict) else None


# rules / の下のサブカテゴリ heading 表示用 (rules/<bucket>/)
RULES_BUCKET_HEADINGS = {
    "numbers": "数値系",
    "text": "テキスト系",
    "context": "文脈ルール",
}


def gen_snapshot_section(now_label: str, now_files: list[str], now_tag: str) -> list[str]:
    """STATS.md と同じカテゴリ階層で release tag 時点 snapshot を生成。"""
    # ── (1) ファイルを path prefix でカテゴリ分け ──
    cats: dict[str, list[tuple[str, int, str]]] = {
        "unihan": [], "jukugo": [], "works": [], "loanwords": [],
        "inbox": [], "single_overrides": [], "compat": [], "rules": [],
    }
    for p in sorted(now_files):
        content = git_show(now_tag, p) or ""
        n = count_top_level_items(content)
        desc = description_with_fallback(content, p)
        item = (p, n, desc)
        if p.startswith("core/unihan/"):
            cats["unihan"].append(item)
        elif p.startswith("core/jukugo/"):
            cats["jukugo"].append(item)
        elif p.startswith("core/works/"):
            cats["works"].append(item)
        elif p.startswith("core/loanwords/"):
            cats["loanwords"].append(item)
        elif p == "core/_inbox.toml":
            cats["inbox"].append(item)
        elif p == "core/single_overrides.toml":
            cats["single_overrides"].append(item)
        elif p == "core/compat.toml":
            cats["compat"].append(item)
        elif p.startswith("rules/"):
            cats["rules"].append(item)

    out: list[str] = [
        f"## リリース時点スナップショット (`{now_label}`)",
        "",
        (
            "release tag 時点での dict / rule file 一覧 + entries 数。 古い release との"
            "比較は GitHub Releases や `git diff <prev> <now> -- core/ rules/` で。 "
            "STATS.md と同じカテゴリ階層で並べる。"
        ),
        "",
    ]

    # ── (2) flat sub-section helper ──
    def render_flat(title: str, note: str, items: list[tuple[str, int, str]]):
        if not items:
            return
        out.append(f"### {title}")
        out.append("")
        if note:
            out.append(note)
            out.append("")
        out.append("| ファイル | entries | 用途 |")
        out.append("|---|---:|---|")
        subtotal = 0
        for p, n, d in items:
            out.append(f"| `{p}` | {n:,} | {d} |")
            subtotal += n
        if len(items) > 1:
            out.append(f"| **小計** ({len(items)} ファイル) | **{subtotal:,}** | |")
        out.append("")

    # ── (3) genre 階層付き sub-section helper (jukugo / works / rules) ──
    def render_grouped(
        title: str, note: str, items: list[tuple[str, int, str]],
        base_subdir: str, headings_override: dict[str, str] | None = None,
    ):
        if not items:
            return
        # group by parts[N] (depending on base depth)
        groups: dict[str, list[tuple[str, int, str]]] = {}
        base_depth = base_subdir.count("/") + 1  # core/jukugo → 2 (parts[0]=core, parts[1]=jukugo)
        for item in items:
            p = item[0]
            parts = p.split("/")
            if len(parts) > base_depth + 1:
                groups.setdefault(parts[base_depth], []).append(item)
            else:
                groups.setdefault("(直下)", []).append(item)
        # sort by genre meta order if available
        ordered: list[tuple[int, str, list[tuple[str, int, str]]]] = []
        for genre_name, files in groups.items():
            order = 999
            heading = genre_name
            if headings_override and genre_name in headings_override:
                heading = headings_override[genre_name]
            elif genre_name != "(直下)":
                meta = load_genre_meta_at_tag(now_tag, f"{base_subdir}/{genre_name}")
                if meta:
                    order = meta.get("order", 999) if isinstance(meta.get("order"), int) else 999
                    if meta.get("name"):
                        heading = meta["name"]
            ordered.append((order, heading, files))
        ordered.sort(key=lambda t: (t[0], t[1]))

        overall_n = sum(it[1] for it in items)
        out.append(f"### {title}")
        out.append("")
        if note:
            out.append(note)
            out.append("")
        out.append(
            f"**合計**: {overall_n:,} entries / {len(items)} ファイル / "
            f"{len(ordered)} 区分"
        )
        out.append("")
        for _, heading, files in ordered:
            files_sorted = sorted(files, key=lambda r: -r[1])
            out.append(f"#### {heading}")
            out.append("")
            out.append("| ファイル | entries | 用途 |")
            out.append("|---|---:|---|")
            sub = 0
            for p, n, d in files_sorted:
                out.append(f"| `{p}` | {n:,} | {d} |")
                sub += n
            if len(files_sorted) > 1:
                out.append(
                    f"| **小計** ({len(files_sorted)} ファイル) | **{sub:,}** | |"
                )
            out.append("")

    # ── (4) 各 section を順番に出力 (STATS.md と同じ並び) ──
    render_flat(
        "単漢字",
        "`core/unihan/*` — 水準別。 lib の resolve_reading 6 段階で最終 fallback (Step 6) として参照。",
        cats["unihan"],
    )
    render_grouped(
        "熟語",
        "`core/jukugo/<genre>/*` — ジャンル別 jukugo (≥ 2 字 surface)、 lib Step 3。",
        cats["jukugo"], base_subdir="core/jukugo",
    )
    render_grouped(
        "作品造語",
        "`core/works/<medium>/*` — 作品単位 1 ファイル、 公式読みベース。",
        cats["works"], base_subdir="core/works",
    )
    render_flat(
        "外来語",
        "`core/loanwords/*` — ASCII surface (英字始まり)、 完全一致 lookup。",
        cats["loanwords"],
    )
    render_flat(
        "分類前 inbox",
        "`core/_inbox.toml` — genre 判断付かない jukugo の一時置き場。",
        cats["inbox"],
    )
    render_flat(
        "単漢字 override",
        "`core/single_overrides.toml` — 1 字 surface に対する明示的 default 上書き。",
        cats["single_overrides"],
    )
    render_flat(
        "異体字",
        "`core/compat.toml` — 異体字 → 標準字の正規化マップ。",
        cats["compat"],
    )
    render_grouped(
        "エンジンルール",
        "`rules/<bucket>/*` — 助数詞 / 文脈 / 後処理 / 大数 / SI 単位 等。",
        cats["rules"], base_subdir="rules",
        headings_override=RULES_BUCKET_HEADINGS,
    )

    # ── (5) 全体合計 (重複含む / ユニーク) ──
    grand_total = sum(it[1] for items in cats.values() for it in items)
    # ユニーク count: iter_top_level_keys で count_top_level_items と同 scope の
    # (key1, key2) tuple を de-dup。 grand_total - unique_count = 純粋な cross-file 重複。
    unique_pairs: set[tuple[str, str]] = set()
    for p in now_files:
        c = git_show(now_tag, p) or ""
        for kp in iter_top_level_keys(c):
            unique_pairs.add(kp)
    duplicates = grand_total - len(unique_pairs)
    out.append("### 全体合計")
    out.append("")
    if duplicates > 0:
        out.append(
            f"**{len(now_files)} ファイル / {grand_total:,} entries (重複含む) "
            f"/ {len(unique_pairs):,} unique / cross-file 重複 {duplicates:,} 件**"
        )
        out.append("")
        out.append(
            f"> **数値の補足**: \n"
            f"> - **重複含む** ({grand_total:,}) = 全 file の top-level item 数を合算 "
            f"(同じ surface が複数 file にあれば多重 count)。 STATS.md の「エントリ数」 と同値\n"
            f"> - **unique** ({len(unique_pairs):,}) = (key1, key2) tuple で de-dup した数\n"
            f"> - **cross-file 重複 {duplicates} 件** = repo 全体 scope での 純粋な重複 "
            f"((surface, reading) が複数 file にまたがって登録されてる数)。 大半は rules/ と "
            f"core/ の **意図的な overlap** (例: 「大人」 が jukugo/general + "
            f"rules/context/special 両方に同 reading) で、 bug ではない\n"
            f"> - actionable な cleanup 対象 (jukugo / works / loanwords scope のみ) は "
            f"下の [cross-file 重複検出](#cross-file-重複検出) section で別途集計"
        )
    else:
        out.append(f"**{len(now_files)} ファイル / {grand_total:,} entries (重複なし)**")
    out.append("")

    return out


def gather_duplicates_at_tag(
    tag: str, now_files: list[str]
) -> tuple[list[tuple[str, str, list[str]]], list[tuple[str, list[tuple[str, str]]]]]:
    """tag 時点で同 surface が複数 file にまたがる cross-file 重複を検出する。

    対象: jukugo / works / loanwords / inbox 系 (entries dict を持つもの)。
    `core/unihan/`、 `core/compat.toml`、 `core/single_overrides.toml`、 rules 系は
    意図的な構造 (水準別分割 / 異体字 map / 単漢字 override / rule) なので除外。

    Returns:
      (same_reading, divergent_reading) のタプル:
      - same_reading: list of (surface, reading, [file, ...]) — 同 surface + 同 reading
      - divergent_reading: list of (surface, [(file, reading), ...]) — 同 surface 異 reading
    """
    # surface → [(file, reading), ...]
    index: dict[str, list[tuple[str, str]]] = {}
    for p in now_files:
        if (
            p.startswith("core/unihan/")
            or p == "core/compat.toml"
            or p == "core/single_overrides.toml"
            or p.startswith("rules/")
        ):
            continue
        c = git_show(tag, p) or ""
        for s, r in parse_entries(c).items():
            index.setdefault(s, []).append((p, r))

    same: list[tuple[str, str, list[str]]] = []
    divergent: list[tuple[str, list[tuple[str, str]]]] = []
    for surface, entries in index.items():
        if len(entries) < 2:
            continue
        readings = {r for _, r in entries}
        if len(readings) == 1:
            same.append((surface, next(iter(readings)), [f for f, _ in entries]))
        else:
            divergent.append((surface, entries))
    same.sort(key=lambda t: t[0])
    divergent.sort(key=lambda t: t[0])
    return same, divergent


def gather_qa_at_tag(tag: str) -> dict:
    """tag 時点の corpus / inline test 件数を集計して返す。

    Returns:
      {
        "corpus": {"should_read": N, "should_not_read_yet": M, "out_of_scope": K},
        "inline_files": F,
        "inline_cases": L,
      }
    """
    paths = git_ls_all(tag)
    qa = {
        "corpus": {"should_read": 0, "should_not_read_yet": 0, "out_of_scope": 0},
        "inline_files": 0,
        "inline_cases": 0,
    }

    # corpus (tests/corpus/*.toml、 bucket 名で振り分け)
    for p in paths:
        if not p.startswith("tests/corpus/") or not p.endswith(".toml"):
            continue
        bucket = None
        for name in qa["corpus"]:
            # `should_read.toml` 単独 or `should_read/<topic>.toml` dir のどちらも
            if f"/{name}.toml" in f"/{p}" or f"/{name}/" in f"/{p}":
                bucket = name
                break
        if bucket is None:
            continue
        content = git_show(tag, p) or ""
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            continue
        cases = data.get("case")
        if isinstance(cases, list):
            # expected を持つ case のみ実行対象 (should_not_read_yet / out_of_scope は
            # expected_failure_reason のみで expected が無いものが多い)
            actionable = sum(
                1 for c in cases if isinstance(c, dict) and "expected" in c
            )
            qa["corpus"][bucket] += actionable

    # inline test (`*.test.toml`、 core/ + rules/ 配下)
    for p in paths:
        if not p.endswith(".test.toml"):
            continue
        if not (p.startswith("core/") or p.startswith("rules/")):
            continue
        content = git_show(tag, p) or ""
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            continue
        cases = data.get("test")
        if isinstance(cases, list):
            qa["inline_files"] += 1
            qa["inline_cases"] += len(cases)

    return qa


def parse_entries(content: str) -> dict[str, str]:
    """TOML 文字列から entries (key→string value) を取り出す (diff 比較用)。

    対応 layout:
    - `[entries]` / `[map]` dict (jukugo / unihan / compat / numeric_phrases / etc.)
    - `[entries]` 内の inline-table value (units.toml: `"km" = { kana = "..." }`)
    - `[[entry]]` array (scales.toml: `[[entry]] kanji=X kana=Y`)
    - top-level flat (旧 days.toml: `'1' = 'ツイタチ'` …)

    `[[rule]]` (postprocess / context) や `[counter."X"]` (counters) のような
    rule-shape の構造は **word-level diff の対象外** (空 dict 返却)。
    これらの top-level エントリ数は `count_top_level_items()` で別取得すること
    (snapshot / 新規 / 削除 file の「entries」 列はそちら経由)。
    """
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return {}

    # [entries] / [map] dict
    for key in ("entries", "map"):
        v = data.get(key)
        if isinstance(v, dict):
            result: dict[str, str] = {}
            for k, vv in v.items():
                if isinstance(vv, str):
                    result[k] = vv
                elif isinstance(vv, dict):
                    # inline-table value (units 等の `{kana = "..."}` 形式)
                    kana = vv.get("kana") or vv.get("reading")
                    if isinstance(kana, str):
                        result[k] = kana
            if result:
                return result

    # [[entry]] array (scales.toml の `kanji = X / kana = Y` 形式)
    arr = data.get("entry")
    if isinstance(arr, list):
        result = {}
        for item in arr:
            if isinstance(item, dict):
                k = item.get("kanji") or item.get("surface")
                v = item.get("kana") or item.get("reading")
                if isinstance(k, str) and isinstance(v, str):
                    result[k] = v
        if result:
            return result

    # flat top-level (旧 days.toml の compat 経路)
    flat = {k: v for k, v in data.items() if isinstance(v, str)}
    return flat


def iter_top_level_keys(content: str):
    """TOML の各 top-level item に対して **重複検査用の key tuple** を yield する。

    snapshot / 集計 / unique 計算で「同じ scope」 で count するための共通 iterator。
    rule-shape file も含めて全 file 共通の (k1, k2) tuple を返すので、
    `len(list(iter_top_level_keys(c)))` が count_top_level_items と一致し、
    `set(iter_top_level_keys(c))` を file 跨ぎで union すれば unique count 取得可。

    対応 layout (返す tuple の意味):
    - `[entries]` / `[map]`: (surface, reading_str) — string value はそのまま
      / inline-table value (units.toml の {kana=...}) は kana / reading を取り出す
    - `[[entry]]` (scales.toml): (kanji, kana)
    - `[[rule]]` (postprocess / context): (surface or pattern, default or replacement)
    - flat top-level (旧 days.toml): (surface, reading)
    - rule-shape (counters の `[counter."本"]`): (top_table_name, sub_key)
      例: ("counter", "本") ("counter", "匹")
    """
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return

    for key in ("entries", "map"):
        v = data.get(key)
        if isinstance(v, dict):
            for k, val in v.items():
                if isinstance(val, str):
                    yield (k, val)
                elif isinstance(val, dict):
                    kana = val.get("kana") or val.get("reading") or ""
                    yield (k, kana if isinstance(kana, str) else "")
            return
    arr = data.get("entry")
    if isinstance(arr, list):
        for item in arr:
            if isinstance(item, dict):
                k = item.get("kanji") or item.get("surface") or ""
                vv = item.get("kana") or item.get("reading") or ""
                if isinstance(k, str) and isinstance(vv, str):
                    yield (k, vv)
        return
    arr = data.get("rule")
    if isinstance(arr, list):
        for item in arr:
            if isinstance(item, dict):
                k = item.get("surface") or item.get("pattern") or ""
                vv = item.get("default") or item.get("replacement") or ""
                yield (
                    k if isinstance(k, str) else "",
                    vv if isinstance(vv, str) else "",
                )
        return
    flat = {k: v for k, v in data.items() if isinstance(v, str)}
    if flat:
        for k, v in flat.items():
            yield (k, v)
        return
    # rule-shape (counters): top-level table 名 + sub key を tuple として返す
    for top, v in data.items():
        if top == "meta" or not isinstance(v, dict):
            continue
        for sub in v:
            yield (top, sub)


def count_top_level_items(content: str) -> int:
    """TOML の top-level item 数を返す (STATS.md の「エントリ数」 と一致)。"""
    return sum(1 for _ in iter_top_level_keys(content))


def parse_meta_description(content: str) -> str | None:
    """TOML 文字列から `[meta] description` を取り出す。 無ければ None。

    各 dict / rule TOML の冒頭に `[meta] description = "..."` を declare して
    file の用途を 1 行説明する慣行 (STATS.md 用途列も同じ source)。 release diff
    で「新規 / 削除 file は何なのか」 を contributor が判断できるよう、 file 名
    の横に description を併記する。
    """
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return None
    meta = data.get("meta")
    if isinstance(meta, dict):
        desc = meta.get("description")
        if isinstance(desc, str) and desc:
            return desc
    return None


def description_with_fallback(content: str, rel_path: str) -> str:
    """tag 時点の content から description、 無ければ working tree (= 現状) から fallback。

    `[meta] description` は metadata で意味的に重要ではない (file の機能を変えない)
    ので、 古い tag 時点では未設定だった file でも、 reader が「これは何 file か」 を
    分かるよう **後付けされた description** を fallback として表示する。

    優先順位:
    1. tag 時点の content の `[meta] description`
    2. working tree (= 現状の HEAD) の **同 path** の `[meta] description`
    3. working tree の **同 basename** の `[meta] description` (rename 移行対応、
       例: `rules/counters/objects.toml` → `rules/numbers/counters/objects.toml`)
    4. **同名 dir への split 検知** (例: `core/unihan.toml` → `core/unihan/*.toml` が
       存在 → split 移行と推定して generic 説明を返す)
    5. `_(用途未設定)_`
    """
    desc = parse_meta_description(content)
    if desc:
        return desc
    # 同 path
    p = REPO_ROOT / rel_path
    if p.is_file():
        try:
            current = p.read_text(encoding="utf-8")
        except OSError:
            current = ""
        desc = parse_meta_description(current)
        if desc:
            return desc
    # 同 basename (rename 検知): core/ + rules/ 配下を再帰探索
    basename = rel_path.rsplit("/", 1)[-1]
    if basename and not basename.endswith(".test.toml") and basename != "_genre.toml":
        for root in (REPO_ROOT / "core", REPO_ROOT / "rules"):
            if not root.is_dir():
                continue
            for cand in root.rglob(basename):
                if not cand.is_file():
                    continue
                try:
                    current = cand.read_text(encoding="utf-8")
                except OSError:
                    continue
                desc = parse_meta_description(current)
                if desc:
                    return f"{desc} _(rename: 現在は `{cand.relative_to(REPO_ROOT).as_posix()}`)_"
    # 同名 dir への split 検知 (`<name>.toml` → `<name>/*.toml`)
    stem = rel_path.removesuffix(".toml")
    split_dir = REPO_ROOT / stem
    if split_dir.is_dir():
        children = sorted(
            c.relative_to(REPO_ROOT).as_posix()
            for c in split_dir.glob("*.toml")
            if c.is_file() and not c.name.endswith(".test.toml")
        )
        if children:
            sample = ", ".join(f"`{c}`" for c in children[:3])
            more = f" 他 {len(children) - 3} file" if len(children) > 3 else ""
            return f"_(旧 single-file 形式、 現在は `{stem}/` 配下に split: {sample}{more})_"
    return "_(用途未設定)_"


def diff_file(prev_content: str, now_content: str) -> tuple[list[str], list[str], list[tuple[str, str, str]]]:
    """1 file 分の (added, removed, changed[(key, prev_v, now_v)]) を返す。"""
    prev = parse_entries(prev_content)
    now = parse_entries(now_content)
    prev_keys = set(prev)
    now_keys = set(now)
    added = sorted(now_keys - prev_keys)
    removed = sorted(prev_keys - now_keys)
    changed = sorted(
        (k, prev[k], now[k]) for k in (prev_keys & now_keys) if prev[k] != now[k]
    )
    return added, removed, changed


def md_escape(s: str) -> str:
    """markdown table cell で `|` を壊さないよう escape。"""
    return s.replace("|", "\\|")


def fmt_two_col_entries(entries: list[str], full: dict[str, str]) -> list[str]:
    """`| 表記 | 読み |` の table rows を返す (header 含む)。 全件出力 (truncate なし)。"""
    rows = ["| 表記 | 読み |", "|---|---|"]
    for k in entries:
        rows.append(f"| `{md_escape(k)}` | `{md_escape(full.get(k, ''))}` |")
    return rows


def fmt_removed_with_moves(
    entries: list[str],
    full: dict[str, str],
    move_finder,
    except_path: str,
) -> list[str]:
    """削除 entries の table。 同 release で他 file に移動が見つかれば「移動先」 列に表示。"""
    # 移動先 column を出すかどうかは「いずれかに移動先がある」 ときのみ
    moves = {k: move_finder(k, full.get(k, ""), except_path) for k in entries}
    has_any_move = any(v for v in moves.values())
    if not has_any_move:
        return fmt_two_col_entries(entries, full)
    rows = ["| 表記 | 読み | 移動先 |", "|---|---|---|"]
    for k in entries:
        target = moves.get(k)
        target_str = f"→ `{target}`" if target else ""
        rows.append(
            f"| `{md_escape(k)}` | `{md_escape(full.get(k, ''))}` | {target_str} |"
        )
    return rows


def fmt_changed_entries(changed: list[tuple[str, str, str]]) -> list[str]:
    """`| 表記 | 旧 | 新 |` の table rows を返す (header 含む)。 全件出力 (truncate なし)。"""
    rows = ["| 表記 | 旧 | 新 |", "|---|---|---|"]
    for k, pv, nv in changed:
        rows.append(
            f"| `{md_escape(k)}` | `{md_escape(pv)}` | `{md_escape(nv)}` |"
        )
    return rows


def main() -> None:
    # 簡易 arg parse (argparse 入れるほどでもない、 positional 2 + 任意 --label-* 2)
    args = sys.argv[1:]
    label_prev = None
    label_now = None
    positional = []
    i = 0
    while i < len(args):
        if args[i] == "--label-prev" and i + 1 < len(args):
            label_prev = args[i + 1]
            i += 2
        elif args[i] == "--label-now" and i + 1 < len(args):
            label_now = args[i + 1]
            i += 2
        else:
            positional.append(args[i])
            i += 1
    if len(positional) < 1:
        print(
            "usage: diff_release.py <prev-tag-or-commit> [<now-tag-or-HEAD>] "
            "[--label-prev <name>] [--label-now <name>]\n"
            "       --label-* は title / heading 表示用の別名 (commit hash で参照する時の "
            "「本来の tag 名」 を指定する用途)",
            file=sys.stderr,
        )
        sys.exit(2)
    prev_tag = positional[0]
    now_tag = positional[1] if len(positional) > 1 else "HEAD"
    # display 用の label。 未指定なら tag/commit そのまま
    prev_label = label_prev or prev_tag
    now_label = label_now or now_tag

    prev_files = set(git_ls_files(prev_tag))
    now_files = set(git_ls_files(now_tag))

    new_files_raw = sorted(now_files - prev_files)
    removed_files_raw = sorted(prev_files - now_files)
    common = sorted(prev_files & now_files)

    # ── rename 検出 (semantic 比較、 [meta] 除く) ──
    # pure rename (= entries / rules の中身に変化なし、 path だけ移動) は 新規 / 削除
    # から外して 「rename」 section に表示。 集計 (total_added / total_removed) からも
    # 除外する。 [meta] block (role / description) や comment / block marker (`===`) の
    # 形式変更は semantic に変化していないとみなす — 実際の data (entries / counter
    # rules / context rules 等) が一致すれば rename として扱う。
    renames: list[tuple[str, str]] = []  # (old_path, new_path)
    matched_old: set[str] = set()
    matched_new: set[str] = set()

    def _semantic_data(content: str):
        if not content:
            return None
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            return None
        # [meta] は metadata (role / description) なので semantic data から除外
        body = {k: v for k, v in data.items() if k != "meta"}
        # `[entries]` block と top-level flat (`'1' = 'ツイタチ'` 等) を等価扱いに
        # 正規化 — `[entries]` block migration (例: days.toml の alpha.9 改修) を
        # rename pair として検出するため。
        if set(body.keys()) == {"entries"} and isinstance(body["entries"], dict):
            return body["entries"]
        # body 全部が string value (flat top-level) なら、 そのまま entries dict として扱う
        if body and all(isinstance(v, str) for v in body.values()):
            return body
        return body

    if removed_files_raw and new_files_raw:
        prev_sigs = {p: _semantic_data(git_show(prev_tag, p) or "") for p in removed_files_raw}
        now_sigs = {p: _semantic_data(git_show(now_tag, p) or "") for p in new_files_raw}
        for old in removed_files_raw:
            old_sig = prev_sigs[old]
            if old_sig is None:
                continue
            for new in new_files_raw:
                if new in matched_new:
                    continue
                if now_sigs[new] == old_sig:
                    renames.append((old, new))
                    matched_old.add(old)
                    matched_new.add(new)
                    break
    new_files = [p for p in new_files_raw if p not in matched_new]
    removed_files = [p for p in removed_files_raw if p not in matched_old]

    # 詳細 + 全体集計
    total_added = 0
    total_removed = 0
    total_changed = 0
    file_diffs: list[tuple[str, list[str], list[str], list[tuple[str, str, str]], dict[str, str], dict[str, str]]] = []

    for path in common:
        prev_c = git_show(prev_tag, path) or ""
        now_c = git_show(now_tag, path) or ""
        if prev_c == now_c:
            continue
        added, removed, changed = diff_file(prev_c, now_c)
        if not (added or removed or changed):
            continue
        prev_e = parse_entries(prev_c)
        now_e = parse_entries(now_c)
        file_diffs.append((path, added, removed, changed, prev_e, now_e))
        total_added += len(added)
        total_removed += len(removed)
        total_changed += len(changed)

    # 新規 file は全 entries が added 扱い (rule-shape file も top-level item 数で count)
    for path in new_files:
        now_c = git_show(now_tag, path) or ""
        total_added += count_top_level_items(now_c)

    # 削除 file は全 entries が removed 扱い
    for path in removed_files:
        prev_c = git_show(prev_tag, path) or ""
        total_removed += count_top_level_items(prev_c)

    # ── unique 集計 (重複 key は de-dup) ──
    # iter_top_level_keys は count_top_level_items と同 scope なので、 raw 合計と
    # unique 合計が同じ統計対象 (entries / counter rules / context rules / etc 全部)
    # で揃う。 raw 合計と unique 合計の差分 = 純粋な cross-file 重複。
    def _collect_pairs(paths: list[str], tag: str) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for path in paths:
            c = git_show(tag, path) or ""
            for kp in iter_top_level_keys(c):
                pairs.add(kp)
        return pairs

    prev_all = _collect_pairs(common + removed_files_raw, prev_tag)
    now_all = _collect_pairs(common + new_files_raw, now_tag)
    unique_added = len(now_all - prev_all)
    unique_removed = len(prev_all - now_all)

    # ── cross-file 移動検出 (削除エントリの引き先候補を作る) ──
    # 同 release で「file A から (surface, reading) が削除」 + 「file B に同じ
    # (surface, reading) が追加」 されている場合、 移動として annotate する。
    # 実体としては「カテゴリ振り分け直し」 (例: jukugo → unihan、 general → specialized)
    # が大半。 reason 欄は手書きできないが、 引き先 file 名は機械的に判定できる。
    added_index: dict[tuple[str, str], list[str]] = {}
    for path, added, _r, _c, _prev_e, now_e in file_diffs:
        for surf in added:
            rdg = now_e.get(surf, "")
            added_index.setdefault((surf, rdg), []).append(path)
    # 新規 file 内の entries も引き先候補
    for path in new_files:
        now_c = git_show(now_tag, path) or ""
        ne = parse_entries(now_c)
        for surf, rdg in ne.items():
            added_index.setdefault((surf, rdg), []).append(path)

    def find_move_target(surface: str, reading: str, except_path: str) -> str | None:
        """同 release で追加された同じ (surface, reading) の引き先 path を返す。
        複数候補あれば最初の 1 つ。 except_path (= 削除元 file) は除外。"""
        candidates = added_index.get((surface, reading), [])
        for c in candidates:
            if c != except_path:
                return c
        return None

    # ── markdown 出力 ──
    out: list[str] = []
    out.append(f"# ja-furigana-dict release diff: `{prev_label}` → `{now_label}`")
    if prev_label != prev_tag or now_label != now_tag:
        # commit hash 参照の場合は実 ref を注記 (削除済み tag の歴史 archive 用途)
        notes = []
        if prev_label != prev_tag:
            notes.append(f"`{prev_label}` (commit `{prev_tag}`)")
        if now_label != now_tag:
            notes.append(f"`{now_label}` (commit `{now_tag}`)")
        out.append("")
        out.append(
            f"> 削除済み tag を commit hash で参照: {' / '.join(notes)}"
        )
    out.append("")

    # ── 集計 (table) ──
    # 「重複含む」 = file 単位の合算 (同じ (surface, reading) が複数 file にあれば多重 count)
    # 「ユニーク」 = (surface, reading) tuple で de-dup (cross-file 重複を 1 件扱い)
    out.append("## 集計")
    out.append("")
    out.append("| 項目 | 値 |")
    out.append("|---|---:|")
    out.append(f"| 追加 entries (重複含む / ユニーク) | **+{total_added:,}** / **+{unique_added:,}** |")
    out.append(f"| 削除 entries (重複含む / ユニーク) | **-{total_removed:,}** / **-{unique_removed:,}** |")
    out.append(f"| 読み変更 | **~{total_changed:,}** |")
    out.append(f"| 新規 file | **{len(new_files)}** |")
    out.append(f"| 削除 file | **{len(removed_files)}** |")
    if renames:
        out.append(f"| rename (内容変化なし) | **{len(renames)}** |")
    out.append("")

    # ── rename (table) ──
    if renames:
        out.append("## rename (内容変化なし、 path 移動のみ)")
        out.append("")
        out.append(
            "prev tag 時点の content と now tag 時点の content が完全一致する file を "
            "rename pair として検出。 集計の 追加 / 削除 entries には含めない。"
        )
        out.append("")
        out.append("| 旧 path | 新 path | entries |")
        out.append("|---|---|---:|")
        for old, new in renames:
            now_c = git_show(now_tag, new) or ""
            n = count_top_level_items(now_c)
            out.append(f"| `{old}` | `{new}` | {n:,} |")
        out.append("")

    # ── 新規 file (table) ──
    if new_files:
        out.append("## 新規 file")
        out.append("")
        out.append("| ファイル | entries | 用途 |")
        out.append("|---|---:|---|")
        for p in new_files:
            now_c = git_show(now_tag, p) or ""
            n = count_top_level_items(now_c)
            desc = description_with_fallback(now_c, p)
            out.append(f"| `{p}` | {n:,} | {desc} |")
        out.append("")

    # ── 削除 file (table) ──
    if removed_files:
        out.append("## 削除 file")
        out.append("")
        out.append("| ファイル | entries | 用途 |")
        out.append("|---|---:|---|")
        for p in removed_files:
            prev_c = git_show(prev_tag, p) or ""
            n = count_top_level_items(prev_c)
            # 削除済 file は同 path の working tree には存在しないが、 同 basename の
            # 移転先がある可能性があるので fallback で探す (rename 移行対応)
            desc = description_with_fallback(prev_c, p)
            out.append(f"| `{p}` | {n:,} | {desc} |")
        out.append("")

    # ── 詳細 (file 別、 各 1 file 内も table で) ──
    if file_diffs:
        out.append("## 詳細 (file 別、 追加 / 削除 / 読み変更 を全件)")
        out.append("")
        for path, added, removed, changed, prev_e, now_e in file_diffs:
            out.append(f"### `{path}`")
            out.append("")
            # file の用途説明 (now tag 側を優先、 無ければ working tree fallback) を
            # heading 直下に表示
            now_c_for_desc = git_show(now_tag, path) or ""
            desc = parse_meta_description(now_c_for_desc)
            if not desc:
                # tag 時点で未設定 → working tree (現状) を fallback
                desc = description_with_fallback(now_c_for_desc, path)
                if desc == "_(用途未設定)_":
                    # 最後に prev tag 側も試す
                    prev_c_for_desc = git_show(prev_tag, path) or ""
                    desc = parse_meta_description(prev_c_for_desc) or ""
            if desc and desc != "_(用途未設定)_":
                out.append(f"_{desc}_")
                out.append("")
            if added:
                out.append(f"**追加 ({len(added):,} 件)**:")
                out.append("")
                out.extend(fmt_two_col_entries(added, now_e))
                out.append("")
            if removed:
                out.append(f"**削除 ({len(removed):,} 件)**:")
                out.append("")
                out.extend(
                    fmt_removed_with_moves(removed, prev_e, find_move_target, path)
                )
                out.append("")
            if changed:
                out.append(f"**読み変更 ({len(changed):,} 件)**:")
                out.append("")
                out.extend(fmt_changed_entries(changed))
                out.append("")

    # ── リリース時点スナップショット (STATS.md と同じカテゴリ階層で) ──
    out.extend(gen_snapshot_section(now_label, sorted(now_files), now_tag))

    # ── cross-file 重複検出 (same reading / divergent reading) ──
    same_dups, divergent_dups = gather_duplicates_at_tag(now_tag, sorted(now_files))
    out.append("## cross-file 重複検出")
    out.append("")
    out.append(
        "tag 時点で **同じ surface が複数 file にまたがって登録** されているもの。 "
        "対象 scope: jukugo / works / loanwords / inbox (= **actionable な cleanup 対象**)。 "
        "`core/unihan/` / `core/compat.toml` / `core/single_overrides.toml` / `rules/` は "
        "意図的構造のため除外。 STATS_DUPS.md と同じ source の release tag 時点 snapshot。"
    )
    out.append("")
    out.append(
        "> **scope の違い**: snapshot の「全体合計」 で出る cross-file 重複数は repo 全体 "
        "(rules / unihan 含む) の **生 fact** で、 大半は intentional overlap (例: rules で "
        "default 提供しつつ core にも entry)。 ここで出すのは **bug 候補 (jukugo/works "
        "スコープでの重複)** に絞った数。 repo の cleanliness を測る指標としてはこちらを見る。"
    )
    out.append("")
    out.append(f"### 同じ読みの重複 ({len(same_dups):,} 件)")
    out.append("")
    if same_dups:
        out.append(
            "_意味的影響なし (genre 振り分けの判断材料、 重複してても lib 動作は変わらない)。_"
        )
        out.append("")
        out.append("| surface | reading | 重複 file |")
        out.append("|---|---|---|")
        for surface, reading, files in same_dups:
            files_str = ", ".join(f"`{f}`" for f in files)
            out.append(f"| `{surface}` | `{reading}` | {files_str} |")
    else:
        out.append("_(無し)_")
    out.append("")
    out.append(f"### 読みが異なる重複 — divergent ({len(divergent_dups):,} 件)")
    out.append("")
    if divergent_dups:
        out.append(
            "**⚠️ validate.py が CI fail させる対象** (どちらが正しいか曖昧、 "
            "merge 後の lookup で後勝ちになって辞書間で読みが揺れる)。 release 時点で "
            "残っている場合は要修正。"
        )
        out.append("")
        out.append("| surface | reading 1 | file 1 | reading 2 | file 2 | (3 件以上は省略) |")
        out.append("|---|---|---|---|---|---|")
        for surface, entries in divergent_dups:
            cells = []
            for f, r in entries[:2]:
                cells.append(f"`{r}`")
                cells.append(f"`{f}`")
            while len(cells) < 4:
                cells.append("")
            extra = (
                f"+{len(entries) - 2} 件" if len(entries) > 2 else ""
            )
            out.append(
                f"| `{surface}` | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {extra} |"
            )
    else:
        out.append("_(無し — クリーン)_")
    out.append("")

    # ── QA カバレッジ (release tag 時点の corpus + inline test 件数) ──
    qa = gather_qa_at_tag(now_tag)
    out.append("## QA カバレッジ")
    out.append("")
    out.append(
        "release tag 時点での test カバレッジ snapshot。 release tar から "
        "`*.test.toml` は exclude されるため lib runtime には影響しないが、 CI 時点の "
        "回帰防御の厚みを記録として残す。"
    )
    out.append("")
    out.append("| 種別 | ケース数 |")
    out.append("|---|---:|")
    out.append(f"| corpus / `should_read` (回帰) | {qa['corpus']['should_read']} |")
    out.append(
        f"| corpus / `should_not_read_yet` (将来 fix 期待) | "
        f"{qa['corpus']['should_not_read_yet']} |"
    )
    out.append(
        f"| corpus / `out_of_scope` (仕様上諦め) | {qa['corpus']['out_of_scope']} |"
    )
    out.append(
        f"| inline test (`*.test.toml`、 {qa['inline_files']} ファイル) | "
        f"{qa['inline_cases']} |"
    )
    qa_total = (
        sum(qa["corpus"].values()) + qa["inline_cases"]
    )
    out.append(f"| **合計** | **{qa_total}** |")
    out.append("")

    if not file_diffs and not new_files and not removed_files:
        out.append("(差分なし)")

    print("\n".join(out))


if __name__ == "__main__":
    main()
