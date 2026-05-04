#!/usr/bin/env python3
"""
furigana-dict 配下の TOML ファイルを検証する。

検出する問題:
- TOML 構文エラー
- 読み (value) が全角カタカナ以外を含む
- 必須セクション / フィールド欠落
- jukugo / unihan の cross-file 重複

CI から呼び出し想定: `python3 tools/validate.py`
exit code 0 = OK, 1 = 検証エラーあり

要 Python 3.11+ (tomllib)。
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

# 全角カタカナ + 長音 (ー) + 中点 (・) のみ許可
KATAKANA_RE = re.compile(r'^[゠-ヿー・]+$')


class Errors(list):
    def add_for(self, file: Path, msg: str) -> None:
        self.append(f"{file.name}: {msg}")

    def add(self, msg: str) -> None:
        self.append(msg)


def is_katakana(s: str) -> bool:
    """`s` が全角カタカナ (+ ー / ・) のみで構成されているか"""
    return bool(s) and bool(KATAKANA_RE.fullmatch(s))


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
    """[entries] section: surface (str) → カタカナ読み (str)"""
    data = load_toml(path, errors)
    if data is None:
        return {}
    entries = data.get('entries')
    if not isinstance(entries, dict):
        errors.add_for(path, "[entries] section が無い、または table ではない")
        return {}
    for surface, reading in entries.items():
        if not isinstance(reading, str):
            errors.add_for(path, f"'{surface}': value が string ではない")
            continue
        if not is_katakana(reading):
            errors.add_for(path, f"'{surface}' → '{reading}' (全角カタカナのみで書いてください)")
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
        if not is_katakana(value):
            errors.add_for(path, f"'{key}' → '{value}' (全角カタカナのみで書いてください)")


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
        if not isinstance(kana, str) or not is_katakana(kana):
            errors.add_for(
                path, f"'{symbol}'.kana = '{kana}' (全角カタカナのみで書いてください)"
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
        if not isinstance(kana, str) or not is_katakana(kana):
            errors.add_for(
                path, f"entry[{i}]: '{kanji}' → kana = '{kana}' (全角カタカナのみで書いてください)"
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
        if not isinstance(value, str) or not is_katakana(value):
            errors.add_for(path, f"'{key}' → '{value}' (全角カタカナのみで書いてください)")


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
            if not isinstance(suffix, str) or not is_katakana(suffix):
                errors.add_for(
                    path, f"simple.'{c}' = '{suffix}' (全角カタカナのみで書いてください)"
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
        if d is not None and (not isinstance(d, str) or not is_katakana(d)):
            errors.add_for(
                path, f"counter.'{c}'.default = '{d}' (全角カタカナのみで書いてください)"
            )
        # rules / replacements / specials の suffix も軽く確認
        for r in rule.get('rules', []):
            if isinstance(r, dict):
                s = r.get('suffix')
                if s is not None and (not isinstance(s, str) or not is_katakana(s)):
                    errors.add_for(
                        path, f"counter.'{c}'.rules: suffix = '{s}' (全角カタカナのみ)"
                    )
        for r in rule.get('replacements', []):
            if isinstance(r, dict):
                t = r.get('to')
                if t is not None and (not isinstance(t, str) or not is_katakana(t)):
                    errors.add_for(
                        path, f"counter.'{c}'.replacements: to = '{t}' (全角カタカナのみ)"
                    )
        specials = rule.get('specials', {})
        if isinstance(specials, dict):
            for k, v in specials.items():
                if not isinstance(v, str) or not is_katakana(v):
                    errors.add_for(
                        path, f"counter.'{c}'.specials.'{k}' = '{v}' (全角カタカナのみ)"
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
        if default is not None and (not isinstance(default, str) or not is_katakana(default)):
            errors.add_for(
                path, f"rule[{i}] '{surface}': default = '{default}' (全角カタカナのみ)"
            )
        for j, m in enumerate(r.get('match', [])):
            if not isinstance(m, dict):
                continue
            reading = m.get('reading')
            if reading is not None and (
                not isinstance(reading, str) or not is_katakana(reading)
            ):
                errors.add_for(
                    path,
                    f"rule[{i}] '{surface}'.match[{j}]: reading = '{reading}' (全角カタカナのみ)",
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


# ─── main ──────────────────────────────────────────────────────────────────
def main() -> int:
    root = Path(__file__).resolve().parent.parent  # tools/.. = repo root
    errors = Errors()

    jukugo: dict = {}
    unihan: dict = {}

    targets = [
        # path, validator
        (root / 'core' / 'jukugo.toml',           lambda p: jukugo.update(validate_lookup(p, errors))),
        (root / 'core' / 'unihan.toml',           lambda p: unihan.update(validate_lookup(p, errors))),
        (root / 'core' / 'compat.toml',           lambda p: validate_compat(p, errors)),
        (root / 'rules' / 'numeric_phrases.toml', lambda p: validate_simple_entries(p, errors)),
        (root / 'rules' / 'symbols.toml',         lambda p: validate_simple_entries(p, errors)),
        (root / 'rules' / 'latin.toml',           lambda p: validate_simple_entries(p, errors)),
        (root / 'rules' / 'units.toml',           lambda p: validate_units(p, errors)),
        (root / 'rules' / 'scales.toml',          lambda p: validate_scales(p, errors)),
        (root / 'rules' / 'days.toml',            lambda p: validate_days(p, errors)),
        (root / 'rules' / 'counters.toml',        lambda p: validate_counters(p, errors)),
        (root / 'rules' / 'context.toml',         lambda p: validate_context(p, errors)),
    ]

    found = 0
    for path, validator in targets:
        if path.exists():
            validator(path)
            found += 1

    check_cross_file_duplicates(jukugo, unihan, errors)

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
