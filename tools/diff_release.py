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

# 1 file の追加 / 削除 / 読み変更 リストの上限 (越えたら省略)
TRUNCATE_LIMIT = 20

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


def count_top_level_items(content: str) -> int:
    """TOML の **top-level エントリ数** を返す (snapshot / 新規 / 削除 file 表示用)。

    parse_entries は (key→reading) を返すので rule-shape file (counters / context /
    postprocess) では空になり、 表示上 「0 entries」 となってしまう問題を回避。 STATS.md
    の「エントリ数」 column と同じ count を返す:

    - `[entries]` / `[map]` dict → key 数
    - `[[entry]]` / `[[rule]]` array → 要素数
    - flat top-level (旧 days.toml) → string value 数
    - 上記いずれも該当しない (counters の `[counter."X"]` 等) → top-level dict
      子要素数 (= counter 名の数、 [meta] は除外)
    """
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return 0

    for key in ("entries", "map"):
        v = data.get(key)
        if isinstance(v, dict):
            return len(v)
    for key in ("entry", "rule"):
        v = data.get(key)
        if isinstance(v, list):
            return len(v)
    flat = sum(1 for v in data.values() if isinstance(v, str))
    if flat > 0:
        return flat
    # [counter."本"] / [counter."匹"] のような rule-shape file の fallback
    return sum(
        len(v) for k, v in data.items()
        if isinstance(v, dict) and k != "meta"
    )


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
    """`| 表記 | 読み |` の table rows を返す (header 含む)。 上限 TRUNCATE_LIMIT。"""
    rows = ["| 表記 | 読み |", "|---|---|"]
    for k in entries[:TRUNCATE_LIMIT]:
        rows.append(f"| `{md_escape(k)}` | `{md_escape(full.get(k, ''))}` |")
    if len(entries) > TRUNCATE_LIMIT:
        rows.append(
            f"| _(他 {len(entries) - TRUNCATE_LIMIT} 件、 commit log 参照)_ | |"
        )
    return rows


def fmt_changed_entries(changed: list[tuple[str, str, str]]) -> list[str]:
    """`| 表記 | 旧 | 新 |` の table rows を返す (header 含む)。"""
    rows = ["| 表記 | 旧 | 新 |", "|---|---|---|"]
    for k, pv, nv in changed[:TRUNCATE_LIMIT]:
        rows.append(
            f"| `{md_escape(k)}` | `{md_escape(pv)}` | `{md_escape(nv)}` |"
        )
    if len(changed) > TRUNCATE_LIMIT:
        rows.append(
            f"| _(他 {len(changed) - TRUNCATE_LIMIT} 件、 commit log 参照)_ | | |"
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

    new_files = sorted(now_files - prev_files)
    removed_files = sorted(prev_files - now_files)
    common = sorted(prev_files & now_files)

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
    out.append("## 集計")
    out.append("")
    out.append("| 項目 | 値 |")
    out.append("|---|---:|")
    out.append(f"| 追加 entries | **+{total_added:,}** |")
    out.append(f"| 削除 entries | **-{total_removed:,}** |")
    out.append(f"| 読み変更 | **~{total_changed:,}** |")
    out.append(f"| 新規 file | **{len(new_files)}** |")
    out.append(f"| 削除 file | **{len(removed_files)}** |")
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
        out.append(f"## 詳細 (file 別、 各セクション上位 {TRUNCATE_LIMIT} 件まで)")
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
                out.extend(fmt_two_col_entries(removed, prev_e))
                out.append("")
            if changed:
                out.append(f"**読み変更 ({len(changed):,} 件)**:")
                out.append("")
                out.extend(fmt_changed_entries(changed))
                out.append("")

    # ── リリース時点スナップショット (now tag 時点の全 file + entries 数) ──
    out.append(f"## リリース時点スナップショット (`{now_label}`)")
    out.append("")
    out.append(
        "release tag 時点での dict / rule file 一覧 + entries 数。 古い release との"
        "比較は GitHub Releases や `git diff <prev> <now> -- core/ rules/` で。"
    )
    out.append("")
    out.append("| ファイル | entries | 用途 |")
    out.append("|---|---:|---|")
    snapshot_total = 0
    for p in sorted(now_files):
        now_c = git_show(now_tag, p) or ""
        n = count_top_level_items(now_c)
        desc = description_with_fallback(now_c, p)
        out.append(f"| `{p}` | {n:,} | {desc} |")
        snapshot_total += n
    out.append(f"| **合計** ({len(now_files)} ファイル) | **{snapshot_total:,}** | |")
    out.append("")

    # ── QA カバレッジ (release tag 時点の corpus + inline test 件数) ──
    qa = gather_qa_at_tag(now_tag)
    out.append("### QA カバレッジ")
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
