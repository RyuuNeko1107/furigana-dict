#!/usr/bin/env python3
"""
furigana-dict 配下の TOML ファイルを検証する。

検出する問題:
- TOML 構文エラー
- 読み (value) が ひらがな / 全角カタカナ / ー / ・ 以外を含む
- 必須セクション / フィールド欠落
- jukugo / unihan の cross-file 重複

ファイル配置:
- 単一ファイル形式 (core/jukugo.toml, rules/counters.toml, rules/context.toml)
- 細分化形式      (core/jukugo/*.toml, rules/counters/*.toml, rules/context/*.toml)
  ─ いずれにも対応する。両方ある場合は単一ファイル形式を優先する
   (エンジン側 load_rules_dir と挙動を揃えるため)。

CI から呼び出し想定: `python3 tools/validate.py`
exit code 0 = OK, 1 = 検証エラーあり

要 Python 3.11+ (tomllib)。
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

# ひらがな + 全角カタカナ + 長音 (ー) + 中点 (・) を許可。
# 加えて intonation bracket marker (`[` `]` `/`) も許容 (= 0.1.0 forward compat、
# lib alpha.10 〜 0.1.0 stable で reading から strip して使う、 0.2.0 で activate)。
#
# 訓読みはひらがな、音読みはカタカナで書くのが慣習なので、両方受け入れる。
# エンジン側 (`furigana::kana::kata_to_hira`) で出力時に正規化されるため、
# 内部表現上はどちらで書いても等価。
KANA_RE = re.compile(r'^[ぁ-ゖァ-ヿー・\[\]/]+$')

# lib alpha.10 (★A1b) で必須化された dict schema version。
# 各 dict / rule TOML の `[meta] schema_version = "2"` が必須、 違反は CI fail。
SUPPORTED_SCHEMA_VERSION = "2"


class Errors(list):
    def add_for(self, file: Path, msg: str) -> None:
        self.append(f"{file.name}: {msg}")

    def add(self, msg: str) -> None:
        self.append(msg)


def is_kana(s: str) -> bool:
    """`s` が ひらがな または 全角カタカナ (+ ー / ・ / intonation bracket [ ] /) のみで構成されているか"""
    return bool(s) and bool(KANA_RE.fullmatch(s))


def validate_bracket_syntax(reading: str) -> list[str]:
    """intonation bracket notation (`[` `]` `/`) の構文検証 (0.2.0 forward compat)。

    constraint:
    - phrase 区切り `/` で分割した各 phrase 内で `[` は最大 1 個、 `]` は最大 1 個
    - 同 phrase 内で `[` と `]` 両方ある場合は `[` が `]` より前 (= 開始 → 終了)
    - 空 phrase 禁止 (連続 `//` / 先頭・末尾 `/`)

    error message の list を返す (= 空 list なら OK)。
    """
    errors: list[str] = []
    if '//' in reading:
        errors.append("空 phrase (連続 '//')")
    if reading.startswith('/'):
        errors.append("先頭 '/' (= 空 leading phrase)")
    if reading.endswith('/'):
        errors.append("末尾 '/' (= 空 trailing phrase)")
    for i, phrase in enumerate(reading.split('/')):
        if not phrase:
            continue
        n_open = phrase.count('[')
        n_close = phrase.count(']')
        if n_open > 1:
            errors.append(f"phrase[{i}] '{phrase}': '[' が {n_open} 個 (最大 1)")
        if n_close > 1:
            errors.append(f"phrase[{i}] '{phrase}': ']' が {n_close} 個 (最大 1)")
        if n_open == 1 and n_close == 1:
            i_open = phrase.index('[')
            i_close = phrase.index(']')
            if i_close < i_open:
                errors.append(f"phrase[{i}] '{phrase}': ']' が '[' より前 (= 順序不正)")
    return errors


def check_reading(path: Path, errors: Errors, label: str, reading: str) -> None:
    """reading の kana check + bracket 構文 check を統合的に呼ぶヘルパ。

    label は error message の prefix (例: `"'X'"` / `"single_override 'X'"`)。"""
    if not is_kana(reading):
        errors.add_for(path, f"{label} → '{reading}' (ひらがな または 全角カタカナで書いてください)")
        return
    for be in validate_bracket_syntax(reading):
        errors.add_for(path, f"{label} bracket 構文: {be}")


def load_toml(path: Path, errors: Errors):
    try:
        with open(path, 'rb') as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        errors.add_for(path, f"TOML パース失敗: {e}")
        return None
    except OSError as e:
        errors.add_for(path, f"読み込み失敗: {e}")
        return None


# ─── core/jukugo.toml, core/unihan.toml ────────────────────────────────────
def validate_lookup(path: Path, errors: Errors) -> dict:
    """[entries] section: surface → reading の検証。

    新 format (★A2、 alpha.11) で entry 値は以下 3 形式が併存:

    1. **Simple** (= 旧 format) — string 値: `"X" = "ヨミ"`
    2. **inline Detailed** — inline table: `"X" = { reading = "ヨミ", match = [...] }`
    3. **expanded Detailed** — sub-table: `[entries."X"]` + `reading = "..."` + `[[entries."X".match]]`

    本関数は default reading だけ flat な dict として返し (= cross-file
    duplicate check 用)、 reading は検証する。 match block 内の reading は
    `validate_match_blocks` で別途検証 (= 後から呼ぶ)。
    """
    data = load_toml(path, errors)
    if data is None:
        return {}
    entries = data.get('entries')
    if not isinstance(entries, dict):
        errors.add_for(path, "[entries] section が無い、または table ではない")
        return {}
    flat: dict[str, str] = {}
    for surface, value in entries.items():
        # Simple form: string value
        if isinstance(value, str):
            reading = value
            check_reading(path, errors, f"'{surface}'", reading)
            flat[surface] = reading
            continue
        # Detailed form: dict value with required `reading` field
        if isinstance(value, dict):
            reading = value.get('reading')
            if not isinstance(reading, str):
                errors.add_for(
                    path,
                    f"'{surface}': detailed entry に reading field 不在 (= 必須、 string)",
                )
                continue
            check_reading(path, errors, f"'{surface}'", reading)
            # match block 配列 (optional) を検証
            matches = value.get('match', [])
            if matches and not isinstance(matches, list):
                errors.add_for(
                    path,
                    f"'{surface}': match field は array of table (現在 {type(matches).__name__})",
                )
                matches = []
            for i, m in enumerate(matches):
                if not isinstance(m, dict):
                    errors.add_for(
                        path,
                        f"'{surface}': match[{i}] が table ではない",
                    )
                    continue
                m_reading = m.get('reading')
                if not isinstance(m_reading, str):
                    errors.add_for(
                        path,
                        f"'{surface}': match[{i}] に reading field 不在 (= 必須、 string)",
                    )
                    continue
                check_reading(path, errors, f"'{surface}' match[{i}]", m_reading)
            flat[surface] = reading
            continue
        # その他 (= bool / array / etc) は型不一致として error
        errors.add_for(path, f"'{surface}': value が string でも detailed entry でもない (型: {type(value).__name__})")
    return flat


# ─── core/single_overrides.toml ───────────────────────────────────────────
# 単漢字 surface (≥1 文字) の default reading override 専用ファイル。
def validate_single_overrides(path: Path, errors: Errors) -> dict:
    """[entries] section: 単漢字 surface (1 字) → カタカナ読み"""
    data = load_toml(path, errors)
    if data is None:
        return {}
    entries = data.get('entries')
    if not isinstance(entries, dict):
        errors.add_for(path, "[entries] section が無い、または table ではない")
        return {}
    for surface, reading in entries.items():
        if not isinstance(reading, str):
            errors.add_for(path, f"single_overrides '{surface}': value が string ではない")
            continue
        if len(surface) == 0 or len(list(surface)) != 1:
            # NOTE: chars().count() を len() で代用 (Python str は文字数 = len)
            char_count = sum(1 for _ in surface)
            if char_count != 1:
                errors.add_for(path, f"single_overrides '{surface}': surface は **必ず 1 字** (現在 {char_count} 字)、 ≥2 字 surface は jukugo に置く")
                continue
        if not is_kana(reading):
            errors.add_for(path, f"single_overrides '{surface}' → '{reading}' (ひらがな または 全角カタカナで書いてください)")
    return entries


# ─── core/loanwords/*.toml ────────────────────────────────────────────────
# ASCII / 全角英字 始まりの surface 専用 (IT 用語等)。 reading はカタカナ。
LOANWORD_SURFACE_RE = re.compile(r'^[A-Za-zＡ-Ｚａ-ｚ][A-Za-z0-9Ａ-Ｚａ-ｚ０-９+#._\-＋＃．＿－]*$')


def validate_loanwords(path: Path, errors: Errors) -> dict:
    """[entries] section: 英字 surface (≥1 文字) → カタカナ読み"""
    data = load_toml(path, errors)
    if data is None:
        return {}
    entries = data.get('entries')
    if not isinstance(entries, dict):
        errors.add_for(path, "[entries] section が無い、または table ではない")
        return {}
    for surface, reading in entries.items():
        if not isinstance(reading, str):
            errors.add_for(path, f"loanword '{surface}': value が string ではない")
            continue
        if not LOANWORD_SURFACE_RE.fullmatch(surface):
            errors.add_for(path, f"loanword '{surface}': surface は ASCII / 全角英字始まりの英数+記号 (+#._-) のみ可")
            continue
        if not is_kana(reading):
            errors.add_for(path, f"loanword '{surface}' → '{reading}' (ひらがな または 全角カタカナで書いてください)")
    return entries


# ─── core/compat.toml ──────────────────────────────────────────────────────
def validate_compat(path: Path, errors: Errors) -> None:
    """[map] section: variant → canonical (どちらも漢字 1〜数文字想定)"""
    data = load_toml(path, errors)
    if data is None:
        return
    mapping = data.get('map')
    if not isinstance(mapping, dict):
        errors.add_for(path, "[map] section が無い")
        return
    for variant, canonical in mapping.items():
        if not isinstance(canonical, str) or not canonical:
            errors.add_for(path, f"'{variant}': canonical が空 or 非 string")
            continue
        # variant も canonical も基本 1 文字 (multi-codepoint 文字含む)。
        # 異常に長い値は警告対象。
        if len(canonical) > 4:
            errors.add_for(path, f"'{variant}' → '{canonical}' (canonical が長すぎる印象)")


# ─── rules/numeric_phrases.toml, rules/symbols.toml, rules/latin.toml ──────
def validate_simple_entries(path: Path, errors: Errors) -> None:
    """[entries] section: key → カタカナ値"""
    data = load_toml(path, errors)
    if data is None:
        return
    entries = data.get('entries')
    if not isinstance(entries, dict):
        errors.add_for(path, "[entries] section が無い")
        return
    for key, value in entries.items():
        if not isinstance(value, str):
            errors.add_for(path, f"'{key}': value が string ではない")
            continue
        if not is_kana(value):
            errors.add_for(path, f"'{key}' → '{value}' (ひらがな または 全角カタカナで書いてください)")


# ─── rules/units.toml ──────────────────────────────────────────────────────
def validate_units(path: Path, errors: Errors) -> None:
    """[entries] symbol → { kana, ci? }"""
    data = load_toml(path, errors)
    if data is None:
        return
    entries = data.get('entries')
    if not isinstance(entries, dict):
        errors.add_for(path, "[entries] section が無い")
        return
    for symbol, info in entries.items():
        if not isinstance(info, dict):
            errors.add_for(path, f"'{symbol}': inline table ({{ kana = ... }}) ではない")
            continue
        kana = info.get('kana')
        if not isinstance(kana, str) or not is_kana(kana):
            errors.add_for(
                path, f"'{symbol}'.kana = '{kana}' (ひらがな または 全角カタカナで書いてください)"
            )


# ─── rules/scales.toml ─────────────────────────────────────────────────────
def validate_scales(path: Path, errors: Errors) -> None:
    """[[entry]] kanji + kana"""
    data = load_toml(path, errors)
    if data is None:
        return
    entries = data.get('entry')
    if not isinstance(entries, list):
        errors.add_for(path, "[[entry]] array が無い")
        return
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            errors.add_for(path, f"entry[{i}] が table ではない")
            continue
        kanji = e.get('kanji')
        kana = e.get('kana')
        if not isinstance(kanji, str) or not kanji:
            errors.add_for(path, f"entry[{i}]: kanji 欠落")
        if not isinstance(kana, str) or not is_kana(kana):
            errors.add_for(
                path, f"entry[{i}]: '{kanji}' → kana = '{kana}' (ひらがな または 全角カタカナで書いてください)"
            )


# ─── rules/days.toml ───────────────────────────────────────────────────────
def validate_days(path: Path, errors: Errors) -> None:
    """key (1〜31 の str) → カタカナ"""
    data = load_toml(path, errors)
    if data is None:
        return
    for key, value in data.items():
        if not key.isdigit():
            errors.add_for(path, f"key '{key}' は数値文字列であるべき (例: \"1\")")
            continue
        n = int(key)
        if not (1 <= n <= 31):
            errors.add_for(path, f"key '{key}' は 1〜31 の範囲外")
        if not isinstance(value, str) or not is_kana(value):
            errors.add_for(path, f"'{key}' → '{value}' (ひらがな または 全角カタカナで書いてください)")


# ─── rules/counters.toml ───────────────────────────────────────────────────
def validate_counters(path: Path, errors: Errors) -> None:
    """[simple] と [counter."X"] を軽く検証"""
    data = load_toml(path, errors)
    if data is None:
        return

    simple = data.get('simple', {})
    if not isinstance(simple, dict):
        errors.add_for(path, "[simple] が table ではない")
    else:
        for c, suffix in simple.items():
            if not isinstance(suffix, str) or not is_kana(suffix):
                errors.add_for(
                    path, f"simple.'{c}' = '{suffix}' (ひらがな または 全角カタカナで書いてください)"
                )

    counters = data.get('counter', {})
    if not isinstance(counters, dict):
        errors.add_for(path, "[counter] table が無い")
        return

    for c, rule in counters.items():
        if not isinstance(rule, dict):
            errors.add_for(path, f"counter.'{c}' が table ではない")
            continue
        d = rule.get('default')
        if d is not None and (not isinstance(d, str) or not is_kana(d)):
            errors.add_for(
                path, f"counter.'{c}'.default = '{d}' (ひらがな または 全角カタカナで書いてください)"
            )
        # rules / replacements / specials の suffix も軽く確認
        for r in rule.get('rules', []):
            if isinstance(r, dict):
                s = r.get('suffix')
                if s is not None and (not isinstance(s, str) or not is_kana(s)):
                    errors.add_for(
                        path, f"counter.'{c}'.rules: suffix = '{s}' (ひらがな または 全角カタカナ)"
                    )
        for r in rule.get('replacements', []):
            if isinstance(r, dict):
                t = r.get('to')
                if t is not None and (not isinstance(t, str) or not is_kana(t)):
                    errors.add_for(
                        path, f"counter.'{c}'.replacements: to = '{t}' (ひらがな または 全角カタカナ)"
                    )
        specials = rule.get('specials', {})
        if isinstance(specials, dict):
            for k, v in specials.items():
                if not isinstance(v, str) or not is_kana(v):
                    errors.add_for(
                        path, f"counter.'{c}'.specials.'{k}' = '{v}' (ひらがな または 全角カタカナ)"
                    )


# ─── rules/context.toml ────────────────────────────────────────────────────
def validate_context(path: Path, errors: Errors) -> None:
    """[[rule]] surface + default? + [[rule.match]] reading"""
    data = load_toml(path, errors)
    if data is None:
        return
    rules = data.get('rule', [])
    if not isinstance(rules, list):
        errors.add_for(path, "[[rule]] array が無い")
        return
    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            errors.add_for(path, f"rule[{i}] が table ではない")
            continue
        surface = r.get('surface')
        if not isinstance(surface, str) or not surface:
            errors.add_for(path, f"rule[{i}]: surface 欠落")
            surface = '<unknown>'
        default = r.get('default')
        if default is not None and (not isinstance(default, str) or not is_kana(default)):
            errors.add_for(
                path, f"rule[{i}] '{surface}': default = '{default}' (ひらがな または 全角カタカナ)"
            )
        for j, m in enumerate(r.get('match', [])):
            if not isinstance(m, dict):
                continue
            reading = m.get('reading')
            if reading is not None and (
                not isinstance(reading, str) or not is_kana(reading)
            ):
                errors.add_for(
                    path,
                    f"rule[{i}] '{surface}'.match[{j}]: reading = '{reading}' (ひらがな または 全角カタカナ)",
                )


# ─── cross-file 重複検出 ──────────────────────────────────────────────────
def check_cross_file_duplicates(
    jukugo: dict, unihan: dict, errors: Errors
) -> None:
    overlap = set(jukugo.keys()) & set(unihan.keys())
    for surface in sorted(overlap):
        errors.add(
            f"cross-file 重複: '{surface}' が core/jukugo.toml と core/unihan.toml の両方に登場"
        )


def _normalize_kata(s: str) -> str:
    """ひらがな → 全角カタカナ正規化 (jukugo merge と同じ等価判定)。"""
    return ''.join(chr(ord(c) + 0x60) if 'ぁ' <= c <= 'ゖ' else c for c in s)


def check_jukugo_divergent_reading(
    per_file_jukugo: dict, errors: Errors
) -> None:
    """jukugo 同士で同 surface だが異なる reading の cross-file 重複を ERROR にする。

    `Dict::from_toml_dir` は後勝ち merge なので、 異 reading 重複が放置されると
    file 名 alphabetical で末尾のファイルが prevail し、 動作が予測不能になる
    (例: abstracts.toml の 一蓮托生=イチレントクショウ vs four_char.toml の
    一蓮托生=イチレンタクショウ が放置されると four_char 側が後勝ちで反映される)。
    同一 reading の重複は実害がないので silent (tools/list_dups.py で別途 list 化)。
    """
    seen: dict[str, list[tuple[str, str]]] = {}
    for filename, entries in per_file_jukugo.items():
        for surface, reading in entries.items():
            if not isinstance(reading, str):
                continue
            seen.setdefault(surface, []).append((filename, reading))
    for surface, lst in sorted(seen.items()):
        if len(lst) <= 1:
            continue
        normalized = {_normalize_kata(r) for _, r in lst}
        if len(normalized) > 1:
            details = ', '.join(f"{f}={r!r}" for f, r in lst)
            errors.add(
                f"cross-file divergent reading: '{surface}' の読みがファイル間でズレている: {details}"
            )


# ─── 単一ファイル / 細分化サブディレクトリ どちらにも対応 ─────────────────
def discover(base_dir: Path, name: str, *, recursive: bool = False) -> list[Path]:
    """`base_dir/name.toml` 単一ファイル → 無ければ `base_dir/name/*.toml` を返す。

    `recursive=True` の場合は `base_dir/name/**/*.toml` で全階層スキャン
    (ja-furigana 0.1.0-alpha.6 以降の loader と挙動を揃える)。

    どちらも存在しない場合は空リスト。両方ある場合は単一ファイルを優先
    (エンジン側 load_rules_dir / Dict::from_toml_dir と同じ挙動)。
    """
    single = base_dir / f"{name}.toml"
    if single.is_file():
        return [single]
    subdir = base_dir / name
    if not subdir.is_dir():
        return []
    pattern = '**/*.toml' if recursive else '*.toml'
    # _genre.toml (STATS sub-section description) と *.test.toml (CI 専用 inline test)
    # は dict entries を持たないので validate 対象外。
    return sorted(
        p for p in subdir.glob(pattern)
        if p.is_file() and p.name != '_genre.toml' and not p.name.endswith('.test.toml')
    )


def validate_kanji_blocks(path: Path, errors: Errors) -> dict[str, str]:
    """`[[kanji]]` array of tables の検証 (★A2、 alpha.11、 `core/kanji/`)。

    各 block は `char` (1 字 surface 必須) + `default` reading + optional
    `[[kanji.match]]` 配列 (= entry inline match と同 vocabulary)。

    返り値: `{ char: default_reading }` (= cross-file 重複 check 用 flat dict)。
    """
    data = load_toml(path, errors)
    if data is None:
        return {}
    blocks = data.get("kanji")
    if blocks is None:
        # [[kanji]] が無くても OK (= 純 [entries] 形式 file の場合)
        return {}
    if not isinstance(blocks, list):
        errors.add_for(path, "[[kanji]] は array of tables (現在 不正型)")
        return {}
    flat: dict[str, str] = {}
    for i, b in enumerate(blocks):
        if not isinstance(b, dict):
            errors.add_for(path, f"[[kanji]][{i}] が table ではない")
            continue
        char = b.get("char")
        if not isinstance(char, str) or len(char) != 1:
            errors.add_for(
                path,
                f"[[kanji]][{i}]: char field が 1 字 string ではない (現在 {char!r})",
            )
            continue
        default = b.get("default")
        if not isinstance(default, str):
            errors.add_for(
                path,
                f"[[kanji]][{i}] (char={char!r}): default field が string ではない",
            )
            continue
        check_reading(path, errors, f"[[kanji]] char={char!r}", default)
        # match 配列 (optional) を検証
        matches = b.get("match", [])
        if matches and not isinstance(matches, list):
            errors.add_for(
                path,
                f"[[kanji]][{i}] (char={char!r}): match field は array of table (現在 {type(matches).__name__})",
            )
            matches = []
        for j, m in enumerate(matches):
            if not isinstance(m, dict):
                errors.add_for(
                    path,
                    f"[[kanji]][{i}] (char={char!r}): match[{j}] が table ではない",
                )
                continue
            m_reading = m.get("reading")
            if not isinstance(m_reading, str):
                errors.add_for(
                    path,
                    f"[[kanji]][{i}] (char={char!r}): match[{j}] に reading 不在",
                )
                continue
            check_reading(path, errors, f"[[kanji]] char={char!r} match[{j}]", m_reading)
        flat[char] = default
    return flat


def validate_schema_version(path: Path, errors: Errors) -> None:
    """`[meta] schema_version = "2"` が宣言されているかを check (★A1b、 alpha.10〜)。

    lib alpha.10 以降は schema_version "2" のみ accept、 不在 / 別値はエラー。
    `_genre.toml` / `*.test.toml` / `tests/corpus/` 配下は対象外 (= 呼び出し側の
    discover が既に弾いている前提)、 本関数は呼ばれた file 全部を check する。
    """
    data = load_toml(path, errors)
    if data is None:
        return  # parse error は load_toml 側で記録済み
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.add_for(path, "[meta] block が無い (= alpha.10〜 必須、 ★A1b)")
        return
    sv = meta.get("schema_version")
    if sv is None:
        errors.add_for(
            path,
            f'[meta] schema_version = "{SUPPORTED_SCHEMA_VERSION}" が必須 (alpha.10〜、 ★A1b)',
        )
        return
    if sv != SUPPORTED_SCHEMA_VERSION:
        errors.add_for(
            path,
            f'[meta] schema_version = {sv!r} は未対応 (期待: "{SUPPORTED_SCHEMA_VERSION}")',
        )


def discover_works(core_dir: Path) -> list[Path]:
    """`core/works/**/*.toml` を全階層再帰でスキャン。

    works/ は作品単位 1 ファイル (例: `works/game/touhou.toml`) の
    細分化構造を許容する。jukugo と同様に ≥2 字 surface の固定読み辞書として
    扱う (load_jukugo に流す)。
    """
    works = core_dir / 'works'
    if not works.is_dir():
        return []
    return sorted(
        p for p in works.glob('**/*.toml')
        if p.is_file() and p.name != '_genre.toml' and not p.name.endswith('.test.toml')
    )


# ─── main ──────────────────────────────────────────────────────────────────
def main() -> int:
    root = Path(__file__).resolve().parent.parent  # tools/.. = repo root
    errors = Errors()
    core = root / 'core'
    rules = root / 'rules'

    jukugo: dict = {}
    unihan: dict = {}
    # check_jukugo_divergent_reading 用に per-file の entries を保持
    per_file_jukugo: dict[str, dict] = {}

    def load_jukugo(p: Path) -> None:
        entries = validate_lookup(p, errors)
        jukugo.update(entries)
        per_file_jukugo[p.name] = entries

    def load_unihan(p: Path) -> None:
        unihan.update(validate_lookup(p, errors))

    # 各 (paths, validator) ペア。paths は単一ファイル or 細分化サブディレクトリ配下。
    # jukugo / works はどちらも ≥2 字 surface の固定読み辞書として load_jukugo に流す
    # (works は作品単位 1 ファイル、ja-furigana 0.1.0-alpha.6 以降の loader 全階層対応)。
    # ★A2 alpha.11: `core/kanji/` の [[kanji]] block (= 旧 single_overrides の後継)
    # を unihan map にマージ (= cross-file 重複 check の対象)
    def load_kanji(p: Path) -> None:
        unihan.update(validate_kanji_blocks(p, errors))

    # ★A2 alpha.11: 旧 format file (= core/single_overrides.toml + rules/context/)
    # は削除済 (= entry inline match + [[kanji]] block format に migration 完了)、
    # validate.py の target からも除外。 validate_single_overrides() / validate_context()
    # 関数自体は将来 reference 用に残置するが、 main() の target list には載せない。
    targets: list[tuple[list[Path], callable]] = [
        (discover(core, 'jukugo', recursive=True), load_jukugo),
        (discover_works(core),                     load_jukugo),
        ([core / '_inbox.toml'],                   load_jukugo),
        (discover(core, 'loanwords', recursive=True), lambda p: validate_loanwords(p, errors)),
        (discover(core, 'unihan'),                 load_unihan),
        (discover(core, 'kanji', recursive=True),  load_kanji),
        ([core / 'compat.toml'],             lambda p: validate_compat(p, errors)),
        ([rules / 'numeric_phrases.toml'],   lambda p: validate_simple_entries(p, errors)),
        ([rules / 'symbols.toml'],           lambda p: validate_simple_entries(p, errors)),
        ([rules / 'units.toml'],             lambda p: validate_units(p, errors)),
        ([rules / 'scales.toml'],            lambda p: validate_scales(p, errors)),
        ([rules / 'days.toml'],              lambda p: validate_days(p, errors)),
        (discover(rules, 'counters'),        lambda p: validate_counters(p, errors)),
    ]

    found = 0
    for paths, validator in targets:
        for path in paths:
            if path.exists():
                validator(path)
                found += 1

    # ★A1b: 全 dict / rule TOML が `[meta] schema_version = "2"` を持つことを check。
    # 既に走った各 validator の結果と独立した別 pass、 全 targets の path を再 walk。
    schema_checked = 0
    for paths, _validator in targets:
        for path in paths:
            if path.exists():
                validate_schema_version(path, errors)
                schema_checked += 1

    check_cross_file_duplicates(jukugo, unihan, errors)
    check_jukugo_divergent_reading(per_file_jukugo, errors)

    if errors:
        print(f"[FAIL] {len(errors)} 件の検証エラー", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(
        f"[OK] {found} ファイル検査済 (jukugo {len(jukugo)} / unihan {len(unihan)} entries)"
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
