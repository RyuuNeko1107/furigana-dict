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


def collect(dict_dir: Path):
    """全 TOML を走査して entry list + kanji index を返す。"""
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
}
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
.badge.t-k { background: #fbefff; color: var(--purple); border-color: transparent; }
.badge.t-c { background: #fff8c5; color: var(--yellow); border-color: transparent; }
.path { font-family: Consolas, "Cascadia Mono", monospace; font-size: .78em; color: #8b949e; margin-top: .25em; }
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
mark { background: #fff8c5; color: inherit; padding: 0 1px; }

.surface .kc {
  cursor: pointer; padding: 0 2px; border-radius: 3px;
  border-bottom: 2px dotted transparent; transition: background .1s, border-color .1s;
}
.surface .kc.has-kanji { border-bottom-color: var(--purple); }
.surface .kc.has-unihan { border-bottom-color: #8b949e; }
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
.kchip.k-unihan { border-left-color: #8b949e; }
.kchip.k-none { border-left-color: var(--line); color: var(--muted); }
.kchip .kc-char { font-weight: 600; font-size: 1.05em; }
.kchip .kc-read { color: var(--green); font-family: "Yu Gothic UI", sans-serif; }
.kchip .kc-extra { font-size: .75em; color: var(--muted); }
.kchip .kc-none { color: var(--muted); font-style: italic; }
.redundant-flag {
  display: inline-block; padding: .1em .55em; font-size: .75em;
  background: #fff8c5; color: var(--yellow); border-radius: 10px;
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
</style>
</head>
<body>

<header>
  <div class="nav">
    <span class="repo-link">repo: <a href="https://github.com/RyuuNeko1107/ja-furigana-dict">github.com/RyuuNeko1107/ja-furigana-dict</a></span>
  </div>
  <h1>furigana-dict 検索 <span class="count">__COUNT__ entries / __FILES__ files / __KANJI_COUNT__ kanji</span></h1>
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
    </ul>
  </div>
  <div class="filters">
    <span class="chip t-e active" data-type="e">📘 entry (<span id="cnt-e">0</span>)</span>
    <span class="chip t-k active" data-type="k">🈳 [[kanji]] (<span id="cnt-k">0</span>)</span>
    <span class="chip t-c active" data-type="c">🔄 compat (<span id="cnt-c">0</span>)</span>
    <select id="dir-filter">
      <option value="">全 dir</option>
    </select>
    <span id="stat"></span>
  </div>
</header>

<main>
  <div id="results"></div>
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

const dirOf = f => {
  const parts = f.split('/');
  return parts.length >= 3 ? parts[1] : '';
};

const typeCounts = { e: 0, k: 0, c: 0 };
const dirsSet = new Set();
for (const e of DATA) {
  typeCounts[e.t] = (typeCounts[e.t] || 0) + 1;
  dirsSet.add(dirOf(e.f));
}
document.getElementById('cnt-e').textContent = typeCounts.e || 0;
document.getElementById('cnt-k').textContent = typeCounts.k || 0;
document.getElementById('cnt-c').textContent = typeCounts.c || 0;

const dirFilter = document.getElementById('dir-filter');
[...dirsSet].sort().forEach(d => {
  if (!d) return;
  const opt = document.createElement('option');
  opt.value = d; opt.textContent = d;
  dirFilter.appendChild(opt);
});

const activeTypes = new Set(['e', 'k', 'c']);
document.querySelectorAll('.chip[data-type]').forEach(chip => {
  chip.addEventListener('click', () => {
    const t = chip.dataset.type;
    if (activeTypes.has(t)) { activeTypes.delete(t); chip.classList.remove('active'); }
    else { activeTypes.add(t); chip.classList.add('active'); }
    render();
  });
});

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

const TYPE_LABEL = { e: 'entry', k: '[[kanji]]', c: 'compat' };

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
  parts.push('<div class="card t-' + entry.t + '">');
  parts.push('<div class="row1">');
  parts.push('<span class="surface">' + renderSurfaceWithClicks(entry.s, surfaceTerms) + '</span>');
  parts.push('<span class="reading">' + highlight(entry.r, readingTerms) + '</span>');
  parts.push('<span class="badge t-' + entry.t + '">' + TYPE_LABEL[entry.t] + '</span>');
  if (entry.role) parts.push('<span class="badge">role=' + escapeHtml(entry.role) + '</span>');
  parts.push('</div>');
  parts.push('<div class="path">' + escapeHtml(entry.f) + '</div>');
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
const statEl = document.getElementById('stat');

let renderTimer = null;
function scheduleRender() {
  clearTimeout(renderTimer);
  renderTimer = setTimeout(render, 80);
}

function render() {
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

  const shown = matched.slice(0, RESULT_CAP);
  statEl.textContent = matched.length === 0
    ? '0 hits'
    : (matched.length > RESULT_CAP ? shown.length + ' / ' + matched.length + ' hits (上位のみ)' : matched.length + ' hits');

  if (matched.length === 0) {
    resultsEl.innerHTML = '<div class="empty">' + (q ? '該当 entry なし' : '検索語を入力してね') + '</div>';
    return;
  }
  resultsEl.innerHTML = shown.map(e => renderCard(e, surfaceTerms, readingTerms)).join('');
}

qInput.addEventListener('input', scheduleRender);
modeSel.addEventListener('change', render);
dirFilter.addEventListener('change', render);

resultsEl.addEventListener('click', ev => {
  const target = ev.target.closest('[data-kc]');
  if (!target) return;
  const ch = target.dataset.kc;
  if (!ch) return;
  qInput.value = 'contains:' + ch;
  modeSel.value = 'auto';
  window.scrollTo({ top: 0, behavior: 'smooth' });
  render();
});

render();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Build dict_browser.html for GitHub Pages")
    parser.add_argument("--dict-dir", type=Path, default=REPO_ROOT / "core",
                        help="Path to dict core/ dir (default: <repo>/core)")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "build" / "dict_browser.html",
                        help="Output HTML path (default: <repo>/build/dict_browser.html)")
    args = parser.parse_args()

    if not args.dict_dir.is_dir():
        print(f"ERROR: --dict-dir not found: {args.dict_dir}", file=sys.stderr)
        return 1

    entries, kanji_idx, files = collect(args.dict_dir)
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
