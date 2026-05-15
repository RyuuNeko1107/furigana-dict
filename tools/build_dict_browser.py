"""
辞書全 entry を 1 つの static HTML に集約、 ブラウザ側 JS で検索可能にする。

GitHub Pages で公開する dict_browser.html を生成する。 CI (= .github/workflows/build-pages.yml)
からは `--out _site/dict_browser.html` 付きで呼ばれる。 contributor が手元で確認したいときは
引数なしで実行すれば `build/dict_browser.html` に出力される。

機能:
- surface / reading / file path / type filter の incremental 検索 (50k+ entry でも軽量)
- 構成漢字 breakdown ([[kanji]] block + unihan を併記、 「default 連結と一致」 redundancy 警告)
- 漢字 click で reverse lookup (= その漢字を含む全 entry を絞り込み)

CLI:
    python tools/build_dict_browser.py                          # → build/dict_browser.html
    python tools/build_dict_browser.py --out _site/dict_browser.html
    python tools/build_dict_browser.py --dict-dir /path/to/core --out /tmp/x.html
"""

import argparse
import json
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _is_kanji(c: str) -> bool:
    cp = ord(c)
    return (
        0x4E00 <= cp <= 0x9FFF or   # CJK Unified
        0x3400 <= cp <= 0x4DBF or   # Extension A
        0xF900 <= cp <= 0xFAFF or   # Compatibility
        0x20000 <= cp <= 0x2A6DF or # Extension B
        0x2A700 <= cp <= 0x2EBEF or # Extensions C..F
        0x2F00 <= cp <= 0x2FDF      # Kangxi Radicals
    )


def _kata_to_hira(s: str) -> str:
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def collect(dict_dir: Path, rules_dir: Path | None = None):
    """全 TOML を走査して entry list + kanji index を返す。

    core/: 通常の entry (t='e') / [[kanji]] block (t='k') / compat map (t='c')
    rules/: rule entry (t='r')、 [entries] / [counter.X] / [[rule]] (postprocess) を抽出
    """
    entries = []
    kanji_idx = {}
    files_seen = []

    def push_kanji_idx(char, rec):
        kanji_idx.setdefault(char, []).append(rec)

    for toml_path in sorted(dict_dir.rglob("*.toml")):
        rel = toml_path.relative_to(dict_dir.parent).as_posix()
        files_seen.append(rel)
        try:
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as exc:
            print(f"WARN: parse failed: {rel}: {exc}", file=sys.stderr)
            continue

        meta = data.get("meta", {})
        role = meta.get("role", "")
        is_unihan = role == "unihan"

        ent_table = data.get("entries", {})
        if isinstance(ent_table, dict):
            for surface, val in ent_table.items():
                if isinstance(val, str):
                    entries.append({
                        "t": "e", "s": surface, "r": val,
                        "f": rel, "role": role,
                    })
                    if is_unihan and len(surface) == 1:
                        push_kanji_idx(surface, {
                            "src": "u", "r": val, "f": rel, "role": role,
                        })
                elif isinstance(val, dict):
                    rec = {
                        "t": "e", "s": surface, "r": val.get("reading", ""),
                        "f": rel, "role": role,
                    }
                    matches = val.get("match")
                    if matches:
                        rec["m"] = matches
                    entries.append(rec)
                    if is_unihan and len(surface) == 1:
                        idx_rec = {
                            "src": "u", "r": rec["r"], "f": rel, "role": role,
                        }
                        if matches:
                            idx_rec["m"] = matches
                        push_kanji_idx(surface, idx_rec)

        kanji_blocks = data.get("kanji")
        if isinstance(kanji_blocks, list):
            for kb in kanji_blocks:
                if not isinstance(kb, dict):
                    continue
                char = kb.get("char", "")
                default = kb.get("default", "")
                matches = kb.get("match")
                rec = {
                    "t": "k", "s": char, "r": default,
                    "f": rel, "role": role,
                }
                if matches:
                    rec["m"] = matches
                entries.append(rec)
                if char:
                    idx_rec = {"src": "k", "r": default, "f": rel, "role": role}
                    if matches:
                        idx_rec["m"] = matches
                    push_kanji_idx(char, idx_rec)

        map_table = data.get("map")
        if isinstance(map_table, dict):
            for src, dst in map_table.items():
                if isinstance(dst, str):
                    entries.append({
                        "t": "c", "s": src, "r": dst,
                        "f": rel, "role": role,
                    })

    # rules/ 配下も walk (= counters / numbers / text / postprocess を audit 対象に)
    if rules_dir and rules_dir.is_dir():
        for toml_path in sorted(rules_dir.rglob("*.toml")):
            if toml_path.name.endswith(".test.toml"):
                continue
            rel = toml_path.relative_to(rules_dir.parent).as_posix()
            files_seen.append(rel)
            try:
                with open(toml_path, "rb") as f:
                    data = tomllib.load(f)
            except Exception as exc:
                print(f"WARN: parse failed: {rel}: {exc}", file=sys.stderr)
                continue

            meta = data.get("meta", {})
            role = meta.get("role", "")

            # [entries] form (= symbols / units / days / kansuji 等)
            ent_table = data.get("entries", {})
            if isinstance(ent_table, dict):
                for surface, val in ent_table.items():
                    if isinstance(val, str):
                        entries.append({
                            "t": "r", "s": surface, "r": val,
                            "f": rel, "role": role,
                        })

            # [counter."X"] tables (= 助数詞: default + specials + rules)
            counter_table = data.get("counter")
            if isinstance(counter_table, dict):
                for ctr_name, ctr_data in counter_table.items():
                    if not isinstance(ctr_data, dict):
                        continue
                    rec = {
                        "t": "r", "s": ctr_name,
                        "r": ctr_data.get("default", ""),
                        "f": rel, "role": role,
                    }
                    blocks = []
                    specials = ctr_data.get("specials") or {}
                    for digit, sp in specials.items():
                        blocks.append({"digit": digit, "reading": sp})
                    sub_rules = ctr_data.get("rules") or []
                    for sr in sub_rules:
                        if isinstance(sr, dict):
                            blocks.append(sr)
                    if blocks:
                        rec["m"] = blocks
                    entries.append(rec)

            # [[rule]] (= postprocess regex pairs)
            rule_array = data.get("rule")
            if isinstance(rule_array, list):
                for r in rule_array:
                    if not isinstance(r, dict):
                        continue
                    rec = {
                        "t": "r",
                        "s": r.get("pattern", ""),
                        "r": r.get("replacement", ""),
                        "f": rel, "role": role,
                    }
                    extra = {k: v for k, v in r.items() if k not in ("pattern", "replacement")}
                    if extra:
                        rec["m"] = [extra]
                    entries.append(rec)

    # post-process 1: precompute redundancy flag (= 構成漢字 default 連結と一致)
    for e in entries:
        if e.get("t") != "e":
            continue
        if e.get("m"):
            continue
        s = e.get("s", "")
        r = e.get("r", "")
        if not s or not r:
            continue
        kchars = [c for c in s if _is_kanji(c)]
        if len(kchars) < 2:
            continue
        concat = ""
        all_have = True
        for ch in kchars:
            idx_list = kanji_idx.get(ch)
            if not idx_list:
                all_have = False
                break
            primary = next((x for x in idx_list if x["src"] == "k"), None) or idx_list[0]
            concat += primary.get("r") or ""
        if not all_have:
            continue
        if _kata_to_hira(r) == _kata_to_hira(concat):
            e["red"] = True

    # post-process 2: precompute combo flag (= 既存 entry の連結で再現可能)
    # surface_index = 単純 entry (t='e', no match) + [[kanji]] block (1 字 default)
    # match-block 持ちは文脈依存なので combo 計算から除外
    surface_index = {}
    for e in entries:
        if e.get("t") not in ("e", "k"):
            continue
        if e.get("m"):
            continue
        s = e.get("s", "")
        r = e.get("r", "")
        if not s or not r:
            continue
        # 既存登録があれば短い key を優先 (普通 1 つだが念のため)
        if s not in surface_index:
            surface_index[s] = r

    def find_combo_split(surface, reading_kata):
        """surface を 2 個以上の既存 entry に分割し、 reading 連結が一致するなら split を返す。"""
        n = len(surface)
        if n < 2 or n > 12:
            return None
        target = _kata_to_hira(reading_kata)
        if not target:
            return None
        # 単純 DFS + backtrack (entry の reading 長で target prefix 一致を厳密 check)
        result = [None]
        def dfs(i, rp, segs):
            if result[0] is not None:
                return
            if i == n:
                if rp == len(target) and len(segs) >= 2:
                    result[0] = segs[:]
                return
            # avoid using full surface as a single seg (= entry 自身を 1 piece で使う)
            for j in range(i + 1, n + 1):
                if i == 0 and j == n:
                    continue
                seg = surface[i:j]
                if seg not in surface_index:
                    continue
                seg_read = _kata_to_hira(surface_index[seg])
                seg_len = len(seg_read)
                if not seg_read:
                    continue
                if target[rp:rp + seg_len] != seg_read:
                    continue
                segs.append(seg)
                dfs(j, rp + seg_len, segs)
                segs.pop()
        dfs(0, 0, [])
        return result[0]

    for e in entries:
        if e.get("t") != "e":
            continue
        if e.get("m"):
            continue
        if e.get("red"):
            # redundancy (default-concat) 既に flag 立ってる場合、 combo は重複情報なのでスキップ
            continue
        s = e.get("s", "")
        r = e.get("r", "")
        if not s or not r or len(s) < 2:
            continue
        splits = find_combo_split(s, r)
        if splits:
            e["combo"] = splits

    return entries, kanji_idx, files_seen


HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>furigana-dict 検索 (__COUNT__ entries)</title>
<style>
:root {
  --fg: #24292f; --bg: #fff; --muted: #57606a; --line: #d0d7de;
  --soft: #f6f8fa; --accent: #0969da; --soft-blue: #ddf4ff;
  --green: #1a7f37; --yellow: #bf8700; --red: #cf222e; --purple: #8250df;
  --soft-purple: #fbefff; --soft-yellow: #fff8c5; --soft-yellow-2: #fff3b0;
  --soft-green: #f0fdf4; --soft-gray: #eaeef2;
  --gray-mid: #6e7781; --gray-text: #57606a; --gray-faint: #8b949e;
  --warn-border: #f0d050;
}
/* dark theme: 1) OS preference (auto), 2) explicit override via html[data-theme="dark"] */
@media (prefers-color-scheme: dark) {
  :root {
    --fg: #e6edf3; --bg: #0d1117; --muted: #8b949e; --line: #30363d;
    --soft: #161b22; --accent: #2f81f7; --soft-blue: #0c2d4a;
    --green: #3fb950; --yellow: #d29922; --red: #f85149; --purple: #a371f7;
    --soft-purple: #2d1b3d; --soft-yellow: #3d3416; --soft-yellow-2: #4d4220;
    --soft-green: #1c3d28; --soft-gray: #21262d;
    --gray-mid: #6e7781; --gray-text: #c9d1d9; --gray-faint: #8b949e;
    --warn-border: #6c5510;
  }
}
html[data-theme="dark"] {
  --fg: #e6edf3; --bg: #0d1117; --muted: #8b949e; --line: #30363d;
  --soft: #161b22; --accent: #2f81f7; --soft-blue: #0c2d4a;
  --green: #3fb950; --yellow: #d29922; --red: #f85149; --purple: #a371f7;
  --soft-purple: #2d1b3d; --soft-yellow: #3d3416; --soft-yellow-2: #4d4220;
  --soft-green: #1c3d28; --soft-gray: #21262d;
  --gray-mid: #6e7781; --gray-text: #c9d1d9; --gray-faint: #8b949e;
  --warn-border: #6c5510;
}
/* light force: OS が dark でも light variables に戻す */
html[data-theme="light"] {
  --fg: #24292f; --bg: #fff; --muted: #57606a; --line: #d0d7de;
  --soft: #f6f8fa; --accent: #0969da; --soft-blue: #ddf4ff;
  --green: #1a7f37; --yellow: #bf8700; --red: #cf222e; --purple: #8250df;
  --soft-purple: #fbefff; --soft-yellow: #fff8c5; --soft-yellow-2: #fff3b0;
  --soft-green: #f0fdf4; --soft-gray: #eaeef2;
  --gray-mid: #6e7781; --gray-text: #57606a; --gray-faint: #8b949e;
  --warn-border: #f0d050;
}
.theme-toggle {
  background: var(--soft); color: var(--muted); border: 1px solid var(--line);
  padding: .25em .65em; font-size: .85em; font-family: inherit;
  border-radius: 4px; cursor: pointer; line-height: 1;
}
.theme-toggle:hover { background: var(--soft-blue); border-color: var(--accent); color: var(--accent); }
.nav { display: flex; align-items: center; gap: .8em; }
.nav .repo-link { flex: 1; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Segoe UI", "Yu Gothic UI", "Meiryo", sans-serif;
  margin: 0; color: var(--fg); background: var(--bg); line-height: 1.5;
}
header {
  position: sticky; top: 0; z-index: 10;
  background: var(--bg); border-bottom: 1px solid var(--line);
  padding: .8em 1.2em;
}
.nav { font-size: .85em; color: var(--muted); margin-bottom: .5em; }
.nav a { color: var(--accent); text-decoration: none; }
.nav a:hover { text-decoration: underline; }
h1 { font-size: 1.2em; margin: 0 0 .5em 0; display: inline-block; }
h1 .count { font-size: .75em; color: var(--muted); font-weight: 400; margin-left: .5em; }

.controls { display: grid; grid-template-columns: 1fr auto auto; gap: .6em; align-items: center; }
@media (max-width: 720px) { .controls { grid-template-columns: 1fr; } }
#q {
  width: 100%; padding: .55em .8em; font-size: 1em;
  border: 1px solid var(--line); border-radius: 6px;
  font-family: inherit;
}
#q:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--soft-blue); }
select {
  padding: .55em .8em; border: 1px solid var(--line); border-radius: 6px;
  background: var(--bg); font-family: inherit; font-size: .95em;
}

.filters { margin-top: .6em; display: flex; flex-wrap: wrap; gap: .4em; align-items: center; }
.chip {
  display: inline-flex; align-items: center; gap: .3em;
  padding: .25em .7em; font-size: .8em; border-radius: 14px;
  background: var(--soft); color: var(--muted); cursor: pointer;
  border: 1px solid var(--line); user-select: none;
}
.chip.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.chip.t-e.active { background: var(--accent); }
.chip.t-k.active { background: var(--purple); border-color: var(--purple); }
.chip.t-c.active { background: var(--yellow); border-color: var(--yellow); }
#dir-filter { font-size: .85em; padding: .25em .5em; }
#stat { color: var(--muted); font-size: .85em; margin-left: auto; }

main { padding: 1em 1.2em 4em; max-width: 1100px; margin: 0 auto; }
.card {
  border: 1px solid var(--line); border-radius: 8px;
  padding: .7em 1em; margin: .5em 0; background: var(--bg);
}
.card.t-e { border-left: 4px solid var(--accent); }
.card.t-k { border-left: 4px solid var(--purple); }
.card.t-c { border-left: 4px solid var(--yellow); }
.row1 { display: flex; align-items: baseline; gap: .8em; flex-wrap: wrap; }
.surface { font-size: 1.25em; font-weight: 600; }
.reading { font-size: 1.0em; color: var(--green); font-family: "Yu Gothic UI", sans-serif; }
.reading::before { content: "→ "; color: var(--muted); }
.badge {
  font-size: .7em; padding: .1em .55em; border-radius: 10px;
  background: var(--soft); color: var(--muted); border: 1px solid var(--line);
}
.badge.t-e { background: var(--soft-blue); color: var(--accent); border-color: transparent; }
.badge.t-k { background: var(--soft-purple); color: var(--purple); border-color: transparent; }
.badge.t-c { background: var(--soft-yellow); color: var(--yellow); border-color: transparent; }
.path { font-family: Consolas, "Cascadia Mono", monospace; font-size: .78em; color: var(--gray-faint); margin-top: .25em; }
.match-section { margin-top: .55em; padding-top: .5em; border-top: 1px dashed var(--line); }
.match-title { font-size: .8em; color: var(--muted); margin-bottom: .3em; }
.match {
  font-family: Consolas, "Cascadia Mono", monospace; font-size: .82em;
  background: var(--soft); padding: .35em .6em; border-radius: 4px; margin: .25em 0;
}
.match .cond { color: var(--accent); }
.match .arr { color: var(--muted); margin: 0 .4em; }
.match .res { color: var(--green); font-weight: 600; }
.empty { text-align: center; padding: 3em 1em; color: var(--muted); }
mark { background: var(--soft-yellow); color: inherit; padding: 0 1px; }

.surface .kc {
  cursor: pointer; padding: 0 2px; border-radius: 3px;
  border-bottom: 2px dotted transparent; transition: background .1s, border-color .1s;
}
.surface .kc.has-kanji { border-bottom-color: var(--purple); }
.surface .kc.has-unihan { border-bottom-color: var(--gray-faint); }
.surface .kc:hover { background: var(--soft-blue); }
.breakdown {
  margin-top: .55em; padding-top: .5em; border-top: 1px dashed var(--line);
  display: flex; flex-wrap: wrap; gap: .35em;
}
.bd-title { font-size: .8em; color: var(--muted); width: 100%; margin-bottom: .2em; }
.kchip {
  display: inline-flex; align-items: center; gap: .35em;
  padding: .2em .55em; background: var(--soft); border-radius: 4px;
  font-size: .85em; border-left: 3px solid transparent; cursor: pointer;
}
.kchip:hover { background: var(--soft-blue); }
.kchip.k-block { border-left-color: var(--purple); }
.kchip.k-unihan { border-left-color: var(--gray-faint); }
.kchip.k-none { border-left-color: var(--line); color: var(--muted); }
.kchip .kc-char { font-weight: 600; font-size: 1.05em; }
.kchip .kc-read { color: var(--green); font-family: "Yu Gothic UI", sans-serif; }
.kchip .kc-extra { font-size: .75em; color: var(--muted); }
.kchip .kc-none { color: var(--muted); font-style: italic; }
.redundant-flag {
  display: inline-block; padding: .1em .55em; font-size: .75em;
  background: var(--soft-yellow); color: var(--yellow); border-radius: 10px;
  margin-left: .4em;
}

.help-toggle {
  background: none; border: 1px solid var(--line); border-radius: 4px;
  padding: .2em .6em; font-size: .8em; color: var(--muted); cursor: pointer;
}
#help {
  display: none; background: var(--soft); padding: 1em 1.4em;
  border-radius: 6px; margin-top: .6em; font-size: .88em;
}
#help.shown { display: block; }
#help code { background: var(--bg); padding: 1px 5px; border-radius: 3px; font-size: .9em; }
#help ul { margin: .3em 0; padding-left: 1.4em; }
.repo-link { font-size: .8em; }

/* view tabs */
.view-tabs { display: flex; gap: .4em; margin: .3em 0 .7em; }
.vtab {
  padding: .4em 1em; border: 1px solid var(--line); border-radius: 6px;
  cursor: pointer; background: var(--bg); color: var(--muted);
  font-size: .9em; font-family: inherit;
}
.vtab.active { background: var(--accent); color: white; border-color: var(--accent); }
.vtab:hover:not(.active) { background: var(--soft); }

.chip.kf.active { background: var(--accent); color: white; border-color: var(--accent); }
.chip.kf.warn-chip.active { background: var(--yellow); border-color: var(--yellow); color: white; }
#ufile-filter { font-size: .85em; padding: .25em .5em; }

/* kanji card */
.kanji-card {
  display: grid; grid-template-columns: 4.5em 1fr; gap: 1em;
  padding: .8em 1em; margin: .5em 0;
  border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg);
}
.kanji-card.has-warn { border-left: 4px solid var(--yellow); }
.kanji-card .big-char {
  font-size: 2.8em; font-weight: 600; text-align: center;
  cursor: pointer; line-height: 1;
  align-self: start; border-radius: 8px; padding: .15em 0;
  transition: background .1s;
}
.kanji-card .big-char:hover { background: var(--soft-blue); }
.kanji-card .kinfo { min-width: 0; }
.kanji-card .ksec { padding: .35em 0; border-top: 1px dashed var(--line); }
.kanji-card .ksec:first-child { border-top: none; padding-top: 0; }
.kanji-card .ksec.usec { color: var(--muted); }
.kanji-card .src-tag {
  display: inline-block; padding: 0 .5em; font-size: .7em;
  border-radius: 10px; background: var(--soft-purple); color: var(--purple);
  font-family: Consolas, monospace; margin-right: .4em;
}
.kanji-card .src-tag.unihan { background: var(--soft); color: var(--muted); }
.kanji-card .kreading {
  color: var(--green); font-family: "Yu Gothic UI", sans-serif;
  font-size: 1.05em; font-weight: 600;
}
.kanji-card .kpath {
  font-family: Consolas, monospace; font-size: .75em;
  color: var(--gray-faint); margin-left: .5em;
}
.kanji-card .kmatch { margin-top: .35em; }
.kanji-card .kbare { font-size: .8em; color: var(--muted); margin-top: .2em; font-style: italic; }
.kanji-card .warn {
  display: inline-block; padding: .2em .65em; font-size: .8em;
  background: var(--soft-yellow); color: var(--yellow); border-radius: 6px;
  margin: .15em .25em .25em 0;
}

/* type 'r' (rule) */
.card.t-r { border-left: 4px solid var(--gray-mid); }
.badge.t-r { background: var(--soft-gray); color: var(--gray-text); border-color: transparent; }
.chip.t-r.active { background: var(--gray-mid); border-color: var(--gray-mid); }

/* dashboard */
.dashboard {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: .5em; margin: .3em 0 .7em;
}
.stat-card {
  background: var(--soft); padding: .5em .8em;
  border-radius: 6px; text-align: center;
  border: 1px solid var(--line); cursor: pointer;
  transition: background .1s, border-color .1s;
}
.stat-card:hover { background: var(--soft-blue); border-color: var(--accent); }
.stat-card .stat-num { font-size: 1.3em; font-weight: 600; color: var(--accent); line-height: 1.2; }
.stat-card .stat-label { font-size: .73em; color: var(--muted); }
.stat-card.warn { background: var(--soft-yellow); border-color: var(--warn-border); }
.stat-card.warn .stat-num { color: var(--yellow); }
.stat-card.warn:hover { background: var(--soft-yellow-2); }

/* edit link */
.edit-link {
  font-size: .72em; color: var(--muted); margin-left: .5em;
  text-decoration: none; padding: .05em .45em; border-radius: 4px;
  border: 1px solid transparent; white-space: nowrap;
}
.edit-link:hover {
  background: var(--soft-blue); border-color: var(--accent);
  color: var(--accent); text-decoration: none;
}

/* pagination */
.pagination {
  display: flex; align-items: center; justify-content: center; gap: .5em;
  margin: 1em 0 .5em; padding: .8em 0;
  border-top: 1px solid var(--line);
}
.pagination button {
  padding: .35em .8em; border: 1px solid var(--line); border-radius: 4px;
  background: var(--bg); color: var(--fg); cursor: pointer; font-family: inherit;
  font-size: .9em;
}
.pagination button:disabled { color: var(--muted); cursor: not-allowed; background: var(--soft); }
.pagination button:not(:disabled):hover { background: var(--soft-blue); border-color: var(--accent); }
.pagination .page-info { font-size: .85em; color: var(--muted); padding: 0 .5em; }
.pagination .page-input {
  width: 4em; padding: .35em .5em; text-align: center;
  border: 1px solid var(--line); border-radius: 4px; font-family: inherit;
}

/* redundancy filter chip */
.chip.rf {
  background: var(--soft-yellow); color: var(--yellow); border-color: var(--warn-border);
}
.chip.rf.active { background: var(--yellow); color: white; border-color: var(--yellow); }

/* sweep progress tracker */
.card.sw-done { border-left-color: var(--green) !important; background: var(--soft-green); }
.card.sw-hold { border-left-color: var(--yellow) !important; background: var(--soft-yellow); }
.card.sw-skip { border-left-color: var(--muted) !important; background: var(--soft); opacity: .65; }
.sw-btns { display: inline-flex; gap: .2em; margin-left: .6em; vertical-align: middle; }
.sw-btn {
  padding: .15em .55em; font-size: .78em; border: 1px solid var(--line);
  border-radius: 4px; background: var(--bg); cursor: pointer;
  font-family: inherit; line-height: 1.3;
}
.sw-btn:hover { background: var(--soft); }
.sw-btn.active[data-sw="done"] { background: var(--green); color: white; border-color: var(--green); }
.sw-btn.active[data-sw="hold"] { background: var(--yellow); color: white; border-color: var(--yellow); }
.sw-btn.active[data-sw="skip"] { background: var(--muted); color: white; border-color: var(--muted); }

.chip.sf.active[data-sfilter="done"] { background: var(--green); color: white; border-color: var(--green); }
.chip.sf.active[data-sfilter="hold"] { background: var(--yellow); color: white; border-color: var(--yellow); }
.chip.sf.active[data-sfilter="skip"] { background: var(--muted); color: white; border-color: var(--muted); }
.chip.sf.active[data-sfilter="todo"] { background: var(--accent); color: white; border-color: var(--accent); }

.progress-bar {
  height: 8px; background: var(--line); border-radius: 4px;
  margin: .4em 0; overflow: hidden; display: flex;
}
.progress-bar .fill { height: 100%; transition: width .2s; }
.progress-bar .fill.done { background: var(--green); }
.progress-bar .fill.hold { background: var(--yellow); }
.progress-bar .fill.skip { background: var(--muted); }
.progress-text {
  font-size: .82em; color: var(--muted);
  display: flex; gap: .8em; align-items: center; flex-wrap: wrap;
}
.progress-text .legend { display: inline-flex; align-items: center; gap: .25em; }
.progress-text .swatch { display: inline-block; width: .8em; height: .8em; border-radius: 2px; }
.progress-text .swatch.done { background: var(--green); }
.progress-text .swatch.hold { background: var(--yellow); }
.progress-text .swatch.skip { background: var(--muted); }

.sw-toolbar {
  display: flex; gap: .5em; margin-left: auto; font-size: .82em; align-items: center;
}
.sw-toolbar button {
  padding: .25em .6em; font-size: .82em; border: 1px solid var(--line);
  background: var(--bg); border-radius: 4px; cursor: pointer; font-family: inherit;
}
.sw-toolbar button:hover { background: var(--soft); }
</style>
<script>
// FOUC 回避: localStorage から saved theme を即座に html[data-theme] に反映、
// CSS が解釈される前に attribute を立てておく (= 「auto」 は attribute 削除)
(function() {
  try {
    var t = localStorage.getItem('theme');
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
  } catch (e) {}
})();
</script>
</head>
<body>

<header>
  <div class="nav">
    <span class="repo-link">repo: <a href="https://github.com/RyuuNeko1107/ja-furigana-dict">github.com/RyuuNeko1107/ja-furigana-dict</a></span>
    <button id="theme-toggle" class="theme-toggle" title="theme: auto (OS) → light → dark → auto">🖥 auto</button>
  </div>
  <h1>furigana-dict 検索 <span class="count">__COUNT__ entries / __FILES__ files / __KANJI_COUNT__ kanji</span></h1>
  <div class="dashboard" id="dashboard"></div>
  <div class="view-tabs">
    <button class="vtab active" data-view="entry">📘 entries view</button>
    <button class="vtab" data-view="kanji">🈳 単漢字 view (audit 用)</button>
  </div>
  <div class="controls">
    <input id="q" type="search" placeholder="検索 (例: 「魔理沙」「contains:魔」「reading:マリサ」「file:works」)" autofocus>
    <select id="mode">
      <option value="auto">auto (← / 「:」 で切替)</option>
      <option value="contains">surface に含む</option>
      <option value="starts">surface の頭一致</option>
      <option value="exact">surface 完全一致</option>
      <option value="reading">reading に含む</option>
      <option value="file">file path に含む</option>
    </select>
    <button class="help-toggle" onclick="document.getElementById('help').classList.toggle('shown')">使い方</button>
  </div>
  <div id="help">
    <strong>検索の仕組み</strong>:
    <ul>
      <li>普通に入力 → mode セレクタに従う (default: auto)</li>
      <li>auto モード: <code>「:」</code> を含まなければ surface contains、 含めば prefix 命令として解釈</li>
      <li><code>contains:魔</code> = surface に「魔」を含む / <code>starts:お</code> = 「お」始まり / <code>exact:猫</code> = 完全一致</li>
      <li><code>reading:マリサ</code> = reading 部分一致 / <code>file:works</code> = source path 部分一致</li>
      <li>複数 token は空白で AND (例: <code>contains:魔 file:works</code>)</li>
      <li>type chip / dir filter で結果を絞り込める</li>
      <li>surface の漢字 / 構成漢字 chip を click → reverse lookup (= その漢字を含む全 entry)</li>
      <li><strong>🈳 単漢字 view</strong>: 全 [[kanji]] block + unihan を 1 字 surface 軸で audit、 警告 chip で sweep 対象を絞る</li>
    </ul>
  </div>
  <div class="filters" data-for="entry">
    <span class="chip t-e active" data-type="e">📘 entry (<span id="cnt-e">0</span>)</span>
    <span class="chip t-k active" data-type="k">🈳 [[kanji]] (<span id="cnt-k">0</span>)</span>
    <span class="chip t-c active" data-type="c">🔄 compat (<span id="cnt-c">0</span>)</span>
    <span class="chip t-r active" data-type="r">📐 rule (<span id="cnt-r">0</span>)</span>
    <span class="chip rf" id="rf-chip" data-rfilter="red" title="default 連結と一致 (= 構成漢字 default だけで reading が再現できる冗長 entry) のみ表示">⚠ default 連結のみ</span>
    <span class="chip rf" id="cf-chip" data-rfilter="combo" title="既存 entry の連結で再現可能 (= 2 個以上の登録済 surface の組み合わせで reading 一致) のみ表示">📦 既存組み合わせのみ</span>
    <select id="dir-filter">
      <option value="">全 dir</option>
    </select>
    <span id="stat"></span>
  </div>
  <div class="filters" style="margin-top:.3em">
    <span style="font-size:.82em; color:var(--muted); margin-right:.3em">sweep:</span>
    <span class="chip sf active" data-sfilter="all">すべて</span>
    <span class="chip sf" data-sfilter="todo">未着手</span>
    <span class="chip sf" data-sfilter="done">✅ 済</span>
    <span class="chip sf" data-sfilter="hold">⏸ 保留</span>
    <span class="chip sf" data-sfilter="skip">✖ skip</span>
    <span class="sw-toolbar">
      <button id="sw-export" title="進捗を JSON で書き出し (clipboard に copy)">📤 export</button>
      <button id="sw-import" title="JSON を貼り付けて進捗を復元">📥 import</button>
      <button id="sw-clear" title="現在の filter にマッチする全 entry の sweep 状態を未着手に戻す">🗑 clear</button>
    </span>
  </div>
  <div id="progress-row" style="margin:.4em 0; display:none">
    <div class="progress-bar" id="progress-bar"></div>
    <div class="progress-text" id="progress-text"></div>
  </div>
  <div class="filters" data-for="kanji" style="display:none">
    <span class="chip kf active" data-kfilter="all">すべて</span>
    <span class="chip kf" data-kfilter="block">[[kanji]] block 有り</span>
    <span class="chip kf warn-chip" data-kfilter="dup">⚠ unihan と重複</span>
    <span class="chip kf warn-chip" data-kfilter="hira">⚠ char_type=ひらがな</span>
    <span class="chip kf" data-kfilter="bare">match 無し default のみ</span>
    <select id="ufile-filter">
      <option value="">全 unihan 水準</option>
      <option value="joyo">joyo (常用)</option>
      <option value="jinmeiyou">jinmeiyou (人名用)</option>
      <option value="jis_basic">JIS 第一水準</option>
      <option value="jis_supplement">JIS 第二水準</option>
      <option value="extension">extension (Ext B+)</option>
    </select>
    <span id="kstat"></span>
  </div>
</header>

<main>
  <div id="results"></div>
  <div id="kresults" style="display:none"></div>
  <div id="pagination" class="pagination" style="display:none"></div>
</main>

<script id="data" type="application/json">__DATA__</script>
<script id="kanji_idx" type="application/json">__KANJI_IDX__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const KANJI_IDX = JSON.parse(document.getElementById('kanji_idx').textContent);
const RESULT_CAP = 500;
const KANJI_RE = /\\p{Script=Han}/u;
const isKanji = ch => KANJI_RE.test(ch);

function kataToHira(s) {
  return (s || '').replace(/[\\u30A1-\\u30F6]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

const GH_EDIT_BASE = 'https://github.com/RyuuNeko1107/ja-furigana-dict/edit/master/';
const PER_PAGE = 200;
let entryPage = 1, kanjiPage = 1;
let redundancyFilter = false;
let comboFilter = false;
let urlSyncEnabled = true;  // 初期 readUrl() 中の writeUrl 抑止

// sweep progress tracker
const SWEEP_KEY = 'dict_browser_sweep_v1';
let sweepState = new Map();
let sweepFilter = 'all';  // 'all' | 'todo' | 'done' | 'hold' | 'skip'

function entryKey(e) { return e.f + '::' + e.s; }
function kanjiKey(ch) { return 'kanji::' + ch; }

function loadSweep() {
  try {
    const raw = localStorage.getItem(SWEEP_KEY);
    if (!raw) return;
    const obj = JSON.parse(raw);
    for (const [k, v] of Object.entries(obj)) sweepState.set(k, v);
  } catch (e) { console.warn('sweep load failed:', e); }
}
function saveSweep() {
  try {
    const obj = {};
    for (const [k, v] of sweepState) obj[k] = v;
    localStorage.setItem(SWEEP_KEY, JSON.stringify(obj));
  } catch (e) { console.warn('sweep save failed:', e); }
}
function renderSweepBtns(key, status) {
  const mk = (s, label, title) =>
    '<button class="sw-btn' + (status === s ? ' active' : '') + '" data-sw="' + s + '" data-sw-key="' + escapeHtmlAttr(key) + '" title="' + title + '">' + label + '</button>';
  return '<span class="sw-btns">' +
    mk('done', '✅', '済') +
    mk('hold', '⏸', '保留') +
    mk('skip', '✖', 'skip') +
    '</span>';
}

function editLink(file) {
  if (!file) return '';
  return '<a class="edit-link" href="' + GH_EDIT_BASE + escapeHtmlAttr(file) +
         '" target="_blank" rel="noopener" title="GitHub で編集">✏️ edit</a>';
}

function escapeHtmlAttr(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

const dirOf = f => {
  const parts = f.split('/');
  return parts.length >= 3 ? parts[1] : '';
};

const typeCounts = { e: 0, k: 0, c: 0, r: 0 };
const dirsSet = new Set();
let redundantCount = 0;
for (const e of DATA) {
  typeCounts[e.t] = (typeCounts[e.t] || 0) + 1;
  dirsSet.add(dirOf(e.f));
  if (e.red) redundantCount++;
}
document.getElementById('cnt-e').textContent = typeCounts.e || 0;
document.getElementById('cnt-k').textContent = typeCounts.k || 0;
document.getElementById('cnt-c').textContent = typeCounts.c || 0;
document.getElementById('cnt-r').textContent = typeCounts.r || 0;

const dirFilter = document.getElementById('dir-filter');
[...dirsSet].sort().forEach(d => {
  if (!d) return;
  const opt = document.createElement('option');
  opt.value = d; opt.textContent = d;
  dirFilter.appendChild(opt);
});

const activeTypes = new Set(['e', 'k', 'c', 'r']);

function parseQuery(q, mode) {
  q = q.trim();
  if (!q) return [];
  const tokens = q.split(/\\s+/).filter(Boolean);
  const filters = [];
  for (const tok of tokens) {
    const m = tok.match(/^(contains|starts|exact|reading|file):(.+)$/);
    if (m) {
      filters.push({ kind: m[1], val: m[2].toLowerCase() });
    } else {
      const kind = (mode === 'auto') ? 'contains' : mode;
      filters.push({ kind: kind, val: tok.toLowerCase() });
    }
  }
  return filters;
}

function matches(entry, filters, dir) {
  if (!activeTypes.has(entry.t)) return false;
  if (redundancyFilter && !entry.red) return false;
  if (comboFilter && !entry.combo) return false;
  if (sweepFilter !== 'all') {
    const st = sweepState.get(entryKey(entry));
    const todoMatch = (!st && sweepFilter === 'todo');
    const statusMatch = (st === sweepFilter);
    if (!todoMatch && !statusMatch) return false;
  }
  if (dir && dirOf(entry.f) !== dir) return false;
  for (const f of filters) {
    const sL = (entry.s || '').toLowerCase();
    const rL = (entry.r || '').toLowerCase();
    const fL = (entry.f || '').toLowerCase();
    let ok = false;
    switch (f.kind) {
      case 'contains': ok = sL.includes(f.val); break;
      case 'starts':   ok = sL.startsWith(f.val); break;
      case 'exact':    ok = sL === f.val; break;
      case 'reading':  ok = rL.includes(f.val); break;
      case 'file':     ok = fL.includes(f.val); break;
    }
    if (!ok) return false;
  }
  return true;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function highlight(text, terms) {
  if (!terms.length) return escapeHtml(text);
  let out = escapeHtml(text);
  for (const t of terms) {
    if (!t) continue;
    const re = new RegExp('(' + t.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
    out = out.replace(re, '<mark>$1</mark>');
  }
  return out;
}

function renderMatch(m) {
  const reading = m.reading || '';
  const conds = [];
  for (const k of Object.keys(m)) {
    if (k === 'reading') continue;
    const v = m[k];
    const vStr = Array.isArray(v) ? '[' + v.map(x => '"' + escapeHtml(String(x)) + '"').join(', ') + ']' : '"' + escapeHtml(String(v)) + '"';
    conds.push('<span class="cond">' + escapeHtml(k) + '</span> = ' + vStr);
  }
  return '<div class="match">' + conds.join(' &amp; ') + '<span class="arr">→</span><span class="res">' + escapeHtml(reading) + '</span></div>';
}

const TYPE_LABEL = { e: 'entry', k: '[[kanji]]', c: 'compat', r: 'rule' };

function renderSurfaceWithClicks(s, terms) {
  const out = [];
  const chars = Array.from(s);
  for (const ch of chars) {
    const lowered = ch.toLowerCase();
    const matchesTerm = terms.some(t => t && lowered.includes(t));
    const idx = KANJI_IDX[ch];
    let cls = 'kc';
    if (idx) {
      const hasBlock = idx.some(r => r.src === 'k');
      cls += hasBlock ? ' has-kanji' : ' has-unihan';
    }
    const wrapped = matchesTerm ? '<mark>' + escapeHtml(ch) + '</mark>' : escapeHtml(ch);
    out.push('<span class="' + cls + '" data-kc="' + escapeHtml(ch) + '" title="' + escapeHtml(ch) + ' を含む entry を検索">' + wrapped + '</span>');
  }
  return out.join('');
}

function renderBreakdown(surface, entry) {
  const kanjiChars = Array.from(surface).filter(isKanji);
  if (kanjiChars.length < 2) return '';

  let concatDefaults = '';
  let allHaveDefault = true;
  const chips = [];
  for (const ch of kanjiChars) {
    const idx = KANJI_IDX[ch];
    if (!idx || idx.length === 0) {
      chips.push('<span class="kchip k-none" data-kc="' + escapeHtml(ch) + '"><span class="kc-char">' + escapeHtml(ch) + '</span><span class="kc-none">(未登録)</span></span>');
      allHaveDefault = false;
      continue;
    }
    const blockRec = idx.find(r => r.src === 'k');
    const unihanRec = idx.find(r => r.src === 'u');
    const primary = blockRec || unihanRec;
    const srcCls = blockRec ? 'k-block' : 'k-unihan';
    const srcTag = blockRec ? '[[kanji]]' : 'unihan';
    const extras = [];
    if (blockRec && blockRec.m) extras.push(blockRec.m.length + ' match');
    if (idx.length > 1 && blockRec && unihanRec) extras.push('+unihan');
    chips.push(
      '<span class="kchip ' + srcCls + '" data-kc="' + escapeHtml(ch) + '">' +
      '<span class="kc-char">' + escapeHtml(ch) + '</span>' +
      '<span class="kc-read">' + escapeHtml(primary.r || '') + '</span>' +
      '<span class="kc-extra">' + srcTag + (extras.length ? ' / ' + extras.join(' / ') : '') + '</span>' +
      '</span>'
    );
    concatDefaults += (primary.r || '');
  }

  let redundantFlag = '';
  if (entry.t === 'e' && allHaveDefault && entry.r && !entry.m) {
    const normEntry = kataToHira(entry.r);
    const normConcat = kataToHira(concatDefaults);
    if (normEntry === normConcat) {
      redundantFlag = '<span class="redundant-flag" title="default reading の連結と一致 — [[kanji]] default のみで再現できる可能性">⚠ default 連結と一致</span>';
    }
  }

  return '<div class="breakdown">' +
    '<div class="bd-title">構成漢字 (click で逆引き)' + redundantFlag + '</div>' +
    chips.join('') +
    '</div>';
}

function renderCard(entry, surfaceTerms, readingTerms) {
  const parts = [];
  const key = entryKey(entry);
  const swStatus = sweepState.get(key);
  const swCls = swStatus ? ' sw-' + swStatus : '';
  parts.push('<div class="card t-' + entry.t + swCls + '">');
  parts.push('<div class="row1">');
  parts.push('<span class="surface">' + renderSurfaceWithClicks(entry.s, surfaceTerms) + '</span>');
  parts.push('<span class="reading">' + highlight(entry.r, readingTerms) + '</span>');
  parts.push('<span class="badge t-' + entry.t + '">' + TYPE_LABEL[entry.t] + '</span>');
  if (entry.role) parts.push('<span class="badge">role=' + escapeHtml(entry.role) + '</span>');
  parts.push(renderSweepBtns(key, swStatus));
  parts.push('</div>');
  parts.push('<div class="path">' + escapeHtml(entry.f) + editLink(entry.f) + '</div>');
  if (entry.combo) {
    parts.push('<div class="match-section">');
    parts.push('<div class="match-title">📦 既存組み合わせで再現可:</div>');
    const segs = entry.combo.map(s => '<code>' + escapeHtml(s) + '</code>').join(' + ');
    parts.push('<div class="match">' + segs + '<span class="arr">→</span><span class="res">' + escapeHtml(entry.r) + '</span></div>');
    parts.push('</div>');
  }
  if (entry.m && entry.m.length) {
    parts.push('<div class="match-section">');
    parts.push('<div class="match-title">match blocks (' + entry.m.length + '):</div>');
    for (const m of entry.m) parts.push(renderMatch(m));
    parts.push('</div>');
  }
  parts.push(renderBreakdown(entry.s, entry));
  parts.push('</div>');
  return parts.join('');
}

const qInput = document.getElementById('q');
const modeSel = document.getElementById('mode');
const resultsEl = document.getElementById('results');
const kresultsEl = document.getElementById('kresults');
const statEl = document.getElementById('stat');
const kstatEl = document.getElementById('kstat');
const ufileFilter = document.getElementById('ufile-filter');

let currentView = 'entry';
let renderTimer = null;
function scheduleRender() {
  clearTimeout(renderTimer);
  renderTimer = setTimeout(render, 80);
}

function render() {
  if (currentView === 'kanji') renderKanjiView();
  else renderEntryView();
}

function renderEntryView() {
  const q = qInput.value;
  const mode = modeSel.value;
  const dir = dirFilter.value;
  const filters = parseQuery(q, mode);

  const surfaceTerms = filters.filter(f => ['contains','starts','exact'].includes(f.kind)).map(f => f.val);
  const readingTerms = filters.filter(f => f.kind === 'reading').map(f => f.val);

  const matched = [];
  for (const e of DATA) {
    if (matches(e, filters, dir)) matched.push(e);
  }

  matched.sort((a, b) => (a.s.length - b.s.length) || a.s.localeCompare(b.s, 'ja'));

  const total = matched.length;
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  if (entryPage > totalPages) entryPage = totalPages;
  const start = (entryPage - 1) * PER_PAGE;
  const shown = matched.slice(start, start + PER_PAGE);

  // progress bar (filtered set 内の sweep 状況)
  updateProgressBar(matched);

  statEl.textContent = total === 0
    ? '0 hits'
    : (total + ' hits' + (totalPages > 1 ? ' (page ' + entryPage + '/' + totalPages + ')' : ''));

  if (total === 0) {
    resultsEl.innerHTML = '<div class="empty">' + (q || redundancyFilter || comboFilter ? '該当 entry なし' : '検索語を入力するか filter を選んで') + '</div>';
    renderPaginationUI(0, 0, () => {});
    return;
  }
  resultsEl.innerHTML = shown.map(e => renderCard(e, surfaceTerms, readingTerms)).join('');
  renderPaginationUI(entryPage, totalPages, (p) => { entryPage = p; render(); window.scrollTo({top: 0, behavior: 'smooth'}); });
}

// === kanji view ===

function getKanjiWarnings(idx) {
  // idx is array of {src, r, f, m?}
  const warns = [];
  const hasBlock = idx.some(r => r.src === 'k');
  const hasUnihan = idx.some(r => r.src === 'u');
  if (hasBlock && hasUnihan) {
    warns.push('⚠ [[kanji]] と unihan 両方に存在 — unihan 側削除推奨');
  }
  const hiraKeys = new Set();
  for (const rec of idx) {
    if (!rec.m) continue;
    for (const m of rec.m) {
      for (const k of Object.keys(m)) {
        if (k.endsWith('_char_type') && m[k] === 'ひらがな') hiraKeys.add(k);
      }
    }
  }
  if (hiraKeys.size) {
    warns.push('⚠ ' + [...hiraKeys].join(', ') + ' = "ひらがな" 雑指定 (literal 列挙推奨)');
  }
  return warns;
}

function renderKanjiCard(ch) {
  const idx = KANJI_IDX[ch];
  const blockRecs = idx.filter(r => r.src === 'k');
  const unihanRecs = idx.filter(r => r.src === 'u');
  const warns = getKanjiWarnings(idx);

  const sections = [];
  for (const rec of blockRecs) {
    let body = '';
    if (rec.m && rec.m.length) {
      body = '<div class="kmatch">' + rec.m.map(m => renderMatch(m)).join('') + '</div>';
    } else {
      body = '<div class="kbare">(match 無し、 default のみ)</div>';
    }
    sections.push(
      '<div class="ksec">' +
      '<span class="src-tag">[[kanji]]</span>' +
      '<span class="kreading">' + escapeHtml(rec.r) + '</span>' +
      '<span class="kpath">' + escapeHtml(rec.f) + '</span>' +
      editLink(rec.f) +
      body +
      '</div>'
    );
  }
  for (const rec of unihanRecs) {
    sections.push(
      '<div class="ksec usec">' +
      '<span class="src-tag unihan">unihan</span>' +
      '<span class="kreading">' + escapeHtml(rec.r) + '</span>' +
      '<span class="kpath">' + escapeHtml(rec.f) + '</span>' +
      editLink(rec.f) +
      '</div>'
    );
  }

  const key = kanjiKey(ch);
  const swStatus = sweepState.get(key);
  const swCls = swStatus ? ' sw-' + swStatus : '';
  const cls = (warns.length ? 'kanji-card has-warn' : 'kanji-card') + swCls;
  return '<div class="' + cls + '">' +
    '<div class="big-char" data-kc="' + escapeHtml(ch) + '" title="' + escapeHtml(ch) + ' を含む全 entry を逆引き">' + escapeHtml(ch) + '</div>' +
    '<div class="kinfo">' +
    '<div style="margin-bottom:.3em">' + renderSweepBtns(key, swStatus) + '</div>' +
    warns.map(w => '<div><span class="warn">' + escapeHtml(w) + '</span></div>').join('') +
    sections.join('') +
    '</div>' +
    '</div>';
}

function renderKanjiView() {
  const q = qInput.value.trim().toLowerCase();
  const activeKf = document.querySelector('.chip.kf.active');
  const kfilter = activeKf ? activeKf.dataset.kfilter : 'all';
  const ufile = ufileFilter.value;

  let chars = Object.keys(KANJI_IDX);

  // free text query: substring on char itself (1 字なので contains:X だけ意味あるが、 prefix 命令も認める)
  if (q) {
    // strip any "key:" prefix that the user may have left, use the bare value as substring
    const m = q.match(/^(?:contains|exact|starts|reading|file):(.+)$/);
    const needle = (m ? m[1] : q);
    chars = chars.filter(ch => ch.includes(needle));
  }

  if (ufile) {
    chars = chars.filter(ch =>
      KANJI_IDX[ch].some(r => r.src === 'u' && r.f.includes(ufile))
    );
  }

  chars = chars.filter(ch => {
    const idx = KANJI_IDX[ch];
    const hasBlock = idx.some(r => r.src === 'k');
    const hasUnihan = idx.some(r => r.src === 'u');
    switch (kfilter) {
      case 'all': return true;
      case 'block': return hasBlock;
      case 'dup': return hasBlock && hasUnihan;
      case 'hira': {
        for (const rec of idx) {
          if (!rec.m) continue;
          for (const m of rec.m) {
            for (const k of Object.keys(m)) {
              if (k.endsWith('_char_type') && m[k] === 'ひらがな') return true;
            }
          }
        }
        return false;
      }
      case 'bare': return hasBlock && idx.filter(r => r.src === 'k').every(r => !r.m);
      default: return true;
    }
  });

  // sweep filter (= kanji 1 字単位で 済/保留/skip/未着手)
  if (sweepFilter !== 'all') {
    chars = chars.filter(ch => {
      const st = sweepState.get(kanjiKey(ch));
      if (sweepFilter === 'todo') return !st;
      return st === sweepFilter;
    });
  }

  chars.sort();

  // progress bar (kanji view 用)
  updateProgressBarKanji(chars);

  const total = chars.length;
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  if (kanjiPage > totalPages) kanjiPage = totalPages;
  const start = (kanjiPage - 1) * PER_PAGE;
  const shown = chars.slice(start, start + PER_PAGE);

  kstatEl.textContent = total === 0 ? '0 kanji' :
    (total + ' kanji' + (totalPages > 1 ? ' (page ' + kanjiPage + '/' + totalPages + ')' : ''));

  if (total === 0) {
    kresultsEl.innerHTML = '<div class="empty">該当 kanji なし</div>';
    renderPaginationUI(0, 0, () => {});
    return;
  }
  kresultsEl.innerHTML = shown.map(ch => renderKanjiCard(ch)).join('');
  renderPaginationUI(kanjiPage, totalPages, (p) => { kanjiPage = p; render(); window.scrollTo({top: 0, behavior: 'smooth'}); });
}

// === progress bar (filtered set 内の sweep 進捗) ===

const progressRow = document.getElementById('progress-row');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

function renderProgressBarFromCounts(done, hold, skip, total) {
  const todo = total - done - hold - skip;
  if (!total || done + hold + skip === 0) { progressRow.style.display = 'none'; return; }
  progressRow.style.display = '';
  const pct = (n) => total ? (n / total * 100) : 0;
  progressBar.innerHTML =
    '<div class="fill done" style="width:' + pct(done) + '%"></div>' +
    '<div class="fill hold" style="width:' + pct(hold) + '%"></div>' +
    '<div class="fill skip" style="width:' + pct(skip) + '%"></div>';
  progressText.innerHTML =
    '<span class="legend"><span class="swatch done"></span>済 ' + done + '</span>' +
    '<span class="legend"><span class="swatch hold"></span>保留 ' + hold + '</span>' +
    '<span class="legend"><span class="swatch skip"></span>skip ' + skip + '</span>' +
    '<span>未着手 ' + todo + ' / ' + total + ' (' + Math.round(pct(done)) + '% 完了)</span>';
}

function updateProgressBar(matched) {
  let done = 0, hold = 0, skip = 0;
  for (const e of matched) {
    const s = sweepState.get(entryKey(e));
    if (s === 'done') done++;
    else if (s === 'hold') hold++;
    else if (s === 'skip') skip++;
  }
  renderProgressBarFromCounts(done, hold, skip, matched.length);
}

function updateProgressBarKanji(chars) {
  let done = 0, hold = 0, skip = 0;
  for (const ch of chars) {
    const s = sweepState.get(kanjiKey(ch));
    if (s === 'done') done++;
    else if (s === 'hold') hold++;
    else if (s === 'skip') skip++;
  }
  renderProgressBarFromCounts(done, hold, skip, chars.length);
}

// === pagination UI ===

const paginationEl = document.getElementById('pagination');

function renderPaginationUI(current, totalPages, onChange) {
  if (totalPages <= 1) { paginationEl.style.display = 'none'; paginationEl.innerHTML = ''; return; }
  paginationEl.style.display = '';
  const prevDis = current <= 1;
  const nextDis = current >= totalPages;
  paginationEl.innerHTML =
    '<button id="pg-first" ' + (prevDis ? 'disabled' : '') + ' title="先頭ページ">«</button>' +
    '<button id="pg-prev" ' + (prevDis ? 'disabled' : '') + ' title="前ページ">‹ prev</button>' +
    '<span class="page-info">' +
      'page <input class="page-input" id="pg-input" type="number" min="1" max="' + totalPages + '" value="' + current + '"> / ' + totalPages +
    '</span>' +
    '<button id="pg-next" ' + (nextDis ? 'disabled' : '') + ' title="次ページ">next ›</button>' +
    '<button id="pg-last" ' + (nextDis ? 'disabled' : '') + ' title="最終ページ">»</button>';
  document.getElementById('pg-first').onclick = () => onChange(1);
  document.getElementById('pg-prev').onclick  = () => onChange(Math.max(1, current - 1));
  document.getElementById('pg-next').onclick  = () => onChange(Math.min(totalPages, current + 1));
  document.getElementById('pg-last').onclick  = () => onChange(totalPages);
  document.getElementById('pg-input').onchange = (ev) => {
    let p = parseInt(ev.target.value, 10);
    if (isNaN(p)) return;
    p = Math.max(1, Math.min(totalPages, p));
    onChange(p);
  };
}

// === dashboard (header 上部の audit カウンター) ===

const STATS = (function() {
  let red = 0, combo = 0, dup = 0, hira = 0, bare = 0;
  for (const e of DATA) {
    if (e.red) red++;
    if (e.combo) combo++;
  }
  for (const ch of Object.keys(KANJI_IDX)) {
    const idx = KANJI_IDX[ch];
    const hasBlock = idx.some(r => r.src === 'k');
    const hasUnihan = idx.some(r => r.src === 'u');
    if (hasBlock && hasUnihan) dup++;
    let hasHira = false;
    for (const rec of idx) {
      if (!rec.m) continue;
      for (const m of rec.m) {
        for (const k of Object.keys(m)) {
          if (k.endsWith('_char_type') && m[k] === 'ひらがな') { hasHira = true; break; }
        }
        if (hasHira) break;
      }
      if (hasHira) break;
    }
    if (hasHira) hira++;
    if (hasBlock && idx.filter(r => r.src === 'k').every(r => !r.m)) bare++;
  }
  return { red, combo, dup, hira, bare };
})();

function renderDashboard() {
  const dash = document.getElementById('dashboard');
  const fmt = n => n.toLocaleString();
  dash.innerHTML =
    '<div class="stat-card warn" data-jump="red" title="default 連結と一致 (= 構成漢字 default だけで再現できる冗長 entry) の絞込"><div class="stat-num">' + fmt(STATS.red) + '</div><div class="stat-label">⚠ default 連結と一致</div></div>' +
    '<div class="stat-card warn" data-jump="combo" title="既存 entry の連結で再現可能 entry の絞込"><div class="stat-num">' + fmt(STATS.combo) + '</div><div class="stat-label">📦 既存組み合わせ</div></div>' +
    '<div class="stat-card warn" data-jump="dup" title="[[kanji]] block と unihan に両方ある重複 kanji"><div class="stat-num">' + fmt(STATS.dup) + '</div><div class="stat-label">⚠ [[kanji]]×unihan 重複</div></div>' +
    '<div class="stat-card warn" data-jump="hira" title="*_char_type=ひらがな 雑指定の kanji"><div class="stat-num">' + fmt(STATS.hira) + '</div><div class="stat-label">⚠ char_type=ひらがな</div></div>' +
    '<div class="stat-card" data-jump="bare" title="match 無し default のみの kanji"><div class="stat-num">' + fmt(STATS.bare) + '</div><div class="stat-label">[[kanji]] default のみ</div></div>';
}

// === URL state ===

function readUrl() {
  urlSyncEnabled = false;
  try {
    const p = new URL(location.href).searchParams;
    if (p.has('q')) qInput.value = p.get('q');
    if (p.has('mode')) modeSel.value = p.get('mode');
    if (p.has('dir')) dirFilter.value = p.get('dir');
    if (p.has('ufile')) ufileFilter.value = p.get('ufile');
    if (p.has('view')) {
      currentView = p.get('view') === 'kanji' ? 'kanji' : 'entry';
      document.querySelectorAll('.vtab').forEach(t => t.classList.toggle('active', t.dataset.view === currentView));
      document.querySelectorAll('.filters[data-for]').forEach(f => f.style.display = (f.dataset.for === currentView) ? '' : 'none');
      resultsEl.style.display = (currentView === 'entry') ? '' : 'none';
      kresultsEl.style.display = (currentView === 'kanji') ? '' : 'none';
    }
    if (p.has('kfilter')) {
      const kf = p.get('kfilter');
      document.querySelectorAll('.chip.kf').forEach(c => c.classList.toggle('active', c.dataset.kfilter === kf));
    }
    if (p.has('rf')) {
      redundancyFilter = (p.get('rf') === '1');
      document.getElementById('rf-chip').classList.toggle('active', redundancyFilter);
    }
    if (p.has('cf')) {
      comboFilter = (p.get('cf') === '1');
      document.getElementById('cf-chip').classList.toggle('active', comboFilter);
    }
    if (p.has('types')) {
      const ts = new Set(p.get('types').split(','));
      activeTypes.clear();
      for (const t of ts) activeTypes.add(t);
      document.querySelectorAll('.chip[data-type]').forEach(c => c.classList.toggle('active', activeTypes.has(c.dataset.type)));
    }
    if (p.has('p')) {
      const pg = parseInt(p.get('p'), 10);
      if (!isNaN(pg) && pg >= 1) {
        if (currentView === 'kanji') kanjiPage = pg; else entryPage = pg;
      }
    }
  } finally {
    urlSyncEnabled = true;
  }
}

function writeUrl() {
  if (!urlSyncEnabled) return;
  const params = new URLSearchParams();
  if (qInput.value) params.set('q', qInput.value);
  if (currentView !== 'entry') params.set('view', currentView);
  if (modeSel.value !== 'auto') params.set('mode', modeSel.value);
  if (dirFilter.value) params.set('dir', dirFilter.value);
  if (ufileFilter.value) params.set('ufile', ufileFilter.value);
  const activeKf = document.querySelector('.chip.kf.active');
  if (activeKf && activeKf.dataset.kfilter !== 'all') params.set('kfilter', activeKf.dataset.kfilter);
  if (redundancyFilter) params.set('rf', '1');
  if (comboFilter) params.set('cf', '1');
  if (activeTypes.size < 4) params.set('types', [...activeTypes].join(','));
  const page = currentView === 'kanji' ? kanjiPage : entryPage;
  if (page > 1) params.set('p', String(page));
  const q = params.toString();
  history.replaceState(null, '', q ? location.pathname + '?' + q : location.pathname);
}

// === view tab switching ===

function setView(view, opts) {
  opts = opts || {};
  currentView = view;
  document.querySelectorAll('.vtab').forEach(t => t.classList.toggle('active', t.dataset.view === view));
  document.querySelectorAll('.filters[data-for]').forEach(f => {
    f.style.display = (f.dataset.for === view) ? '' : 'none';
  });
  resultsEl.style.display = (view === 'entry') ? '' : 'none';
  kresultsEl.style.display = (view === 'kanji') ? '' : 'none';
  if (!opts.keepPage) {
    if (view === 'entry') entryPage = 1; else kanjiPage = 1;
  }
  render();
}

// override render to write URL after each render
const originalRender = render;
render = function() {
  if (currentView === 'kanji') renderKanjiView();
  else renderEntryView();
  writeUrl();
};

// === handlers ===

// type chip handler with page reset
document.querySelectorAll('.chip[data-type]').forEach(chip => {
  chip.addEventListener('click', () => {
    const t = chip.dataset.type;
    if (activeTypes.has(t)) { activeTypes.delete(t); chip.classList.remove('active'); }
    else { activeTypes.add(t); chip.classList.add('active'); }
    entryPage = 1;
    render();
  });
});

// redundancy chip
document.getElementById('rf-chip').addEventListener('click', () => {
  redundancyFilter = !redundancyFilter;
  document.getElementById('rf-chip').classList.toggle('active', redundancyFilter);
  entryPage = 1;
  render();
});

// combo chip
document.getElementById('cf-chip').addEventListener('click', () => {
  comboFilter = !comboFilter;
  document.getElementById('cf-chip').classList.toggle('active', comboFilter);
  entryPage = 1;
  render();
});

// vtab click
document.querySelectorAll('.vtab').forEach(t => {
  t.addEventListener('click', () => setView(t.dataset.view));
});

// kanji filter chip
document.querySelectorAll('.chip.kf').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.chip.kf').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    kanjiPage = 1;
    render();
  });
});

ufileFilter.addEventListener('change', () => { kanjiPage = 1; render(); });
qInput.addEventListener('input', () => { entryPage = 1; kanjiPage = 1; scheduleRender(); });
modeSel.addEventListener('change', () => { entryPage = 1; render(); });
dirFilter.addEventListener('change', () => { entryPage = 1; render(); });

// dashboard click → jump to corresponding filter
document.getElementById('dashboard').addEventListener('click', ev => {
  const card = ev.target.closest('[data-jump]');
  if (!card) return;
  const jump = card.dataset.jump;
  // reset other filters
  redundancyFilter = false; comboFilter = false;
  document.getElementById('rf-chip').classList.remove('active');
  document.getElementById('cf-chip').classList.remove('active');
  document.querySelectorAll('.chip.kf').forEach(c => c.classList.toggle('active', c.dataset.kfilter === 'all'));
  if (jump === 'red') {
    redundancyFilter = true;
    document.getElementById('rf-chip').classList.add('active');
    setView('entry');
  } else if (jump === 'combo') {
    comboFilter = true;
    document.getElementById('cf-chip').classList.add('active');
    setView('entry');
  } else {
    // kanji filters
    document.querySelectorAll('.chip.kf').forEach(c => c.classList.toggle('active', c.dataset.kfilter === jump));
    setView('kanji');
  }
});

// entries view: sw button click (toggle) > kanji char click (reverse lookup)
resultsEl.addEventListener('click', ev => {
  // sw button (toggle sweep status)
  const swBtn = ev.target.closest('[data-sw][data-sw-key]');
  if (swBtn) {
    ev.stopPropagation();
    const key = swBtn.dataset.swKey;
    const newStatus = swBtn.dataset.sw;
    const cur = sweepState.get(key);
    if (cur === newStatus) sweepState.delete(key);
    else sweepState.set(key, newStatus);
    saveSweep();
    render();
    return;
  }
  // kanji char click (reverse lookup)
  const target = ev.target.closest('[data-kc]');
  if (!target) return;
  const ch = target.dataset.kc;
  if (!ch) return;
  qInput.value = 'contains:' + ch;
  modeSel.value = 'auto';
  entryPage = 1;
  window.scrollTo({ top: 0, behavior: 'smooth' });
  render();
});

// sweep filter chip (entries / kanji 両 view 共通)
document.querySelectorAll('.chip.sf').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.chip.sf').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    sweepFilter = chip.dataset.sfilter;
    entryPage = 1; kanjiPage = 1;
    render();
  });
});

// sweep toolbar
document.getElementById('sw-export').addEventListener('click', async () => {
  const obj = {};
  for (const [k, v] of sweepState) obj[k] = v;
  const json = JSON.stringify(obj, null, 2);
  try {
    await navigator.clipboard.writeText(json);
    alert('進捗 JSON を clipboard に copy しました (' + sweepState.size + ' entries)');
  } catch (e) {
    // fallback: open in new window
    const w = window.open('', '_blank');
    w.document.body.innerText = json;
  }
});
document.getElementById('sw-import').addEventListener('click', () => {
  const json = prompt('進捗 JSON を貼り付け:');
  if (!json) return;
  try {
    const obj = JSON.parse(json);
    for (const [k, v] of Object.entries(obj)) {
      if (['done', 'hold', 'skip'].includes(v)) sweepState.set(k, v);
    }
    saveSweep();
    render();
    alert('進捗復元完了 (現在 ' + sweepState.size + ' entries マーク済)');
  } catch (e) { alert('JSON parse failed: ' + e.message); }
});
document.getElementById('sw-clear').addEventListener('click', () => {
  // 現 view + 現 filter にマッチする sweep 状態だけクリア
  let cleared = 0;
  if (currentView === 'kanji') {
    // kanji 側 (= kanjiKey)
    const activeKf = document.querySelector('.chip.kf.active');
    const kfilter = activeKf ? activeKf.dataset.kfilter : 'all';
    const ufile = ufileFilter.value;
    const q = qInput.value.trim().toLowerCase();
    const m = q.match(/^(?:contains|exact|starts|reading|file):(.+)$/);
    const needle = m ? m[1] : q;
    for (const ch of Object.keys(KANJI_IDX)) {
      if (needle && !ch.includes(needle)) continue;
      if (ufile && !KANJI_IDX[ch].some(r => r.src === 'u' && r.f.includes(ufile))) continue;
      const idx = KANJI_IDX[ch];
      const hasBlock = idx.some(r => r.src === 'k');
      const hasUnihan = idx.some(r => r.src === 'u');
      let pass = true;
      if (kfilter === 'block') pass = hasBlock;
      else if (kfilter === 'dup') pass = hasBlock && hasUnihan;
      else if (kfilter === 'hira') {
        pass = idx.some(r => r.m && r.m.some(mm =>
          Object.keys(mm).some(k => k.endsWith('_char_type') && mm[k] === 'ひらがな')));
      } else if (kfilter === 'bare') {
        pass = hasBlock && idx.filter(r => r.src === 'k').every(r => !r.m);
      }
      if (!pass) continue;
      const k = kanjiKey(ch);
      if (sweepState.has(k)) { sweepState.delete(k); cleared++; }
    }
  } else {
    const filters = parseQuery(qInput.value, modeSel.value);
    const dir = dirFilter.value;
    for (const e of DATA) {
      if (!matches(e, filters, dir)) continue;
      const k = entryKey(e);
      if (sweepState.has(k)) { sweepState.delete(k); cleared++; }
    }
  }
  if (cleared === 0) { alert('クリア対象なし'); return; }
  if (!confirm(cleared + ' 件の sweep 状態をクリアしますか?')) return;
  saveSweep();
  render();
});

// kanji view: sw button click (toggle) > big-char click (reverse lookup)
kresultsEl.addEventListener('click', ev => {
  // sw button (kanji sweep)
  const swBtn = ev.target.closest('[data-sw][data-sw-key]');
  if (swBtn) {
    ev.stopPropagation();
    const key = swBtn.dataset.swKey;
    const newStatus = swBtn.dataset.sw;
    const cur = sweepState.get(key);
    if (cur === newStatus) sweepState.delete(key);
    else sweepState.set(key, newStatus);
    saveSweep();
    render();
    return;
  }
  // big-char click → entries view + contains:<ch>
  const target = ev.target.closest('[data-kc]');
  if (!target) return;
  const ch = target.dataset.kc;
  if (!ch) return;
  qInput.value = 'contains:' + ch;
  modeSel.value = 'auto';
  entryPage = 1;
  setView('entry');
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// === theme toggle (auto → light → dark → auto cycle、 localStorage で persist) ===
const THEME_LABEL = { auto: '🖥 auto', light: '☀ light', dark: '🌙 dark' };
const THEME_NEXT = { auto: 'light', light: 'dark', dark: 'auto' };
function currentTheme() {
  const t = localStorage.getItem('theme');
  return (t === 'light' || t === 'dark') ? t : 'auto';
}
function applyTheme(t) {
  if (t === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', t);
  document.getElementById('theme-toggle').textContent = THEME_LABEL[t];
}
applyTheme(currentTheme());
document.getElementById('theme-toggle').addEventListener('click', () => {
  const next = THEME_NEXT[currentTheme()];
  if (next === 'auto') localStorage.removeItem('theme');
  else localStorage.setItem('theme', next);
  applyTheme(next);
});

// === init ===
loadSweep();
renderDashboard();
readUrl();
render();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Build dict_browser.html for GitHub Pages")
    parser.add_argument("--dict-dir", type=Path, default=REPO_ROOT / "core",
                        help="Path to dict core/ dir (default: <repo>/core)")
    parser.add_argument("--rules-dir", type=Path, default=REPO_ROOT / "rules",
                        help="Path to rules/ dir (default: <repo>/rules)")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "build" / "dict_browser.html",
                        help="Output HTML path (default: <repo>/build/dict_browser.html)")
    args = parser.parse_args()

    if not args.dict_dir.is_dir():
        print(f"ERROR: --dict-dir not found: {args.dict_dir}", file=sys.stderr)
        return 1

    rules_dir = args.rules_dir if args.rules_dir.is_dir() else None
    entries, kanji_idx, files = collect(args.dict_dir, rules_dir)
    print(f"Collected {len(entries)} entries from {len(files)} files")
    print(f"Kanji index: {len(kanji_idx)} unique chars")

    json_data = json.dumps(entries, ensure_ascii=False, separators=(',', ':'))
    json_kanji = json.dumps(kanji_idx, ensure_ascii=False, separators=(',', ':'))
    print(f"JSON size: data={len(json_data.encode('utf-8'))/1024/1024:.2f} MB, "
          f"kanji_idx={len(json_kanji.encode('utf-8'))/1024/1024:.2f} MB")

    html = (HTML_TEMPLATE
            .replace("__COUNT__", f"{len(entries):,}")
            .replace("__FILES__", str(len(files)))
            .replace("__KANJI_COUNT__", f"{len(kanji_idx):,}")
            .replace("__DATA__", json_data)
            .replace("__KANJI_IDX__", json_kanji))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"Wrote: {args.out}")
    print(f"HTML size: {args.out.stat().st_size / 1024 / 1024:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
