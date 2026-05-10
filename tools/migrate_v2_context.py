#!/usr/bin/env python3
"""
rules/context/*.toml の [[rule]] / [[rule.match]] を新 format の
`[entries."x"]` / `[[entries."x".match]]` 形式に機械変換する。

alpha.11 lib (★A2 wire-up) で `scoring/format::Entry` / `EntryDetail` /
`MatchBlock` を実際の dict load 経路で parse するようになり、 さらに
matcher vocabulary が prev_ends_any / next_starts / next_starts_any /
next2_starts_any / prev_month / next_digit を含む形に拡張された。 これにより
旧 rules/context/ の 46 match block 中 41 件 (89%) が機械変換可能。

## 出力先

`docs/migration/v2_context/` (= 変換結果と report、 review 用 staging area)。
core/ への merge は人手 PR series で実施 (= 各 surface をどの jukugo file に
配置するか triage 要、 alpha.11 期 dict 完全再編成 task の一部)。

## 変換 rule

| 旧 format | 新 format |
|---|---|
| `[[rule]]` + `surface = "X"` | `[entries."X"]` |
| `default = "..."` | `reading = "..."` |
| `[[rule.match]]` | `[[entries."X".match]]` |
| `prev_ends = [...]` | `prev_ends_any = [...]` (rename) |
| `next2_starts = [...]` | `next2_starts_any = [...]` (rename) |
| `pos = "..."` | **DROP** + TODO comment (= POS は新 format 不採用、 literal 列挙で代用要) |
| `prev_eq` / `next_eq` / `prev_eq_any` / `next_eq_any` | そのまま (同名) |
| `next_starts` / `next_starts_any` / `next_digit` / `prev_month` | そのまま (同名) |
| `prev_char_type` / `next_char_type` | そのまま (同名) |

## TODO 出力

- POS-only match (= 全 condition が pos のみ) は drop されるので、 その entry の
  match block 配列が空になる場合 (= 元 rule 全 match が POS-only) → TODO note
- POS を含む rule (= 5 件、 alpha.11 拡張で 0 件まで減少した hybrid 含む)
- default 不在 rule (= match miss 時の fallback がない) → TODO で human が default 決定
- core/ にも entry 不在 surface (= 21 件) → TODO で human がどの jukugo file に
  配置するか triage

走らせ方:
    python tools/migrate_v2_context.py             # default output dir に出力
    python tools/migrate_v2_context.py --output-dir <path>
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# field rename mapping (旧 → 新)
RENAME = {
    "prev_ends": "prev_ends_any",
    "next2_starts": "next2_starts_any",
}

# 新 format でサポートされる match field (= 出力時 emit する field)
SUPPORTED_MATCH_FIELDS = [
    # (field name, value type)
    "prev_eq",
    "prev_eq_any",
    "next_eq",
    "next_eq_any",
    "prev_ends_any",
    "next_starts",
    "next_starts_any",
    "next2_starts_any",
    "prev_char_type",
    "next_char_type",
    "prev_month",
    "next_digit",
]

# 新 format で **採用しない** field (= drop + TODO 出力)
UNSUPPORTED_FIELDS = {"pos"}

# 旧 format で 「triple-quoted string を newline split で string list として扱う」
# 形式の field 群 (= lib 旧 deserialize_with = "string_list" 経路)。
# 機械変換時に string なら newline split → array に正規化する。
LIST_FIELDS_OLD_NAMES = {
    "prev_ends",  # → prev_ends_any
    "next_starts_any",
    "next2_starts",  # → next2_starts_any
    "prev_eq_any",
    "next_eq_any",
}


def coerce_list(v):
    """value が triple-quoted string なら newline split で list 化、 既に list ならそのまま。"""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        # newline split + trim + 空 entry 除去
        items = [line.strip() for line in v.splitlines()]
        return [s for s in items if s]
    return v


def normalize_match(match: dict) -> tuple[dict, list[str]]:
    """match block dict を正規化 (rename + drop POS + list coerce) して (新 dict, dropped fields) を返す。

    旧 format の triple-quoted string (= newline-split list) は array に正規化、
    旧 field 名は新 field 名に rename、 POS は drop して reason を返す。
    """
    out = {}
    dropped = []
    for k, v in match.items():
        if k == "reading":
            out["reading"] = v
            continue
        if k in UNSUPPORTED_FIELDS:
            dropped.append(f"{k}={v!r}")
            continue
        # triple-quoted string → list 正規化 (= 旧 deserialize_with 互換)
        if k in LIST_FIELDS_OLD_NAMES:
            v = coerce_list(v)
        new_key = RENAME.get(k, k)
        out[new_key] = v
    return out, dropped


def find_existing_surface_file(surface: str, core_dir: Path) -> Path | None:
    """surface が既存 core/ のどの file に entry として存在するか探す。"""
    for p in core_dir.rglob("*.toml"):
        if p.name == "_genre.toml" or p.name.endswith(".test.toml"):
            continue
        try:
            data = tomllib.loads(p.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            continue
        if surface in data.get("entries", {}):
            return p
    return None


def emit_toml_string(s: str) -> str:
    """TOML string literal として escape (= ダブルクォート + \\ / " escape)。"""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit_toml_value(v) -> str:
    """TOML value として整形 (= string / array of string / bool 対応)。"""
    if isinstance(v, str):
        return emit_toml_string(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        # 1 行 1 要素 (project 全体方針)
        if not v:
            return "[]"
        items = ",\n".join(f"  {emit_toml_value(x)}" for x in v)
        return f"[\n{items},\n]"
    raise ValueError(f"unsupported value type: {type(v)} = {v!r}")


def emit_match_block(match: dict, surface: str) -> str:
    """[[entries."X".match]] block を TOML 文字列として整形。"""
    lines = [f'[[entries.{emit_toml_string(surface)}.match]]']
    # 保証: reading は最初に
    if "reading" in match:
        lines.append(f"reading = {emit_toml_value(match['reading'])}")
    # 残り field を SUPPORTED_MATCH_FIELDS の順番で出力
    for field in SUPPORTED_MATCH_FIELDS:
        if field == "reading":
            continue
        if field in match:
            lines.append(f"{field} = {emit_toml_value(match[field])}")
    # 認識外 field がもし残ってたら警告 comment
    extra = set(match.keys()) - set(SUPPORTED_MATCH_FIELDS) - {"reading"}
    for k in sorted(extra):
        lines.append(f"# WARNING: 認識外 field {k} = {match[k]!r}")
    return "\n".join(lines)


def emit_entry(rule: dict, surface: str, default_reading: str | None, todo_notes: list[str]) -> str:
    """[entries."X"] block + match block 配列を整形。"""
    lines = []
    if todo_notes:
        for note in todo_notes:
            lines.append(f"# TODO: {note}")
    lines.append(f"[entries.{emit_toml_string(surface)}]")
    if default_reading is not None:
        lines.append(f"reading = {emit_toml_value(default_reading)}")
    else:
        lines.append('# TODO: default reading 不在、 人手で reading = "..." を追加要')
        lines.append('reading = "???"  # PLACEHOLDER')
    matches = rule.get("match", [])
    out_matches = []
    for m in matches:
        normalized, dropped = normalize_match(m)
        if dropped:
            # 全 condition が POS で drop された場合 (= reading 以外何も残らない) は match block 出力 skip
            if set(normalized.keys()) == {"reading"}:
                lines.append(
                    f"# TODO: POS-only match dropped (reading={normalized['reading']!r}, "
                    f"原条件 {', '.join(dropped)})、 literal 列挙で代用要"
                )
                continue
            # 部分 drop は WARN 残す
            lines.append(
                f"# WARNING: POS condition dropped: {', '.join(dropped)} (literal 列挙で再現要)"
            )
        if "reading" not in normalized:
            lines.append(f"# WARNING: match block に reading 不在、 skip")
            continue
        out_matches.append(normalized)
    if out_matches:
        lines.append("")
        for nm in out_matches:
            lines.append(emit_match_block(nm, surface))
            lines.append("")
        # 末尾の空行 trim
        if lines and lines[-1] == "":
            lines.pop()
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs" / "migration" / "v2_context",
        help="変換結果の出力先 dir (default: docs/migration/v2_context/)",
    )
    args = parser.parse_args()

    rules_context = ROOT / "rules" / "context"
    if not rules_context.is_dir():
        print(f"error: rules/context/ not found at {rules_context}", file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # --- 各 source file 処理 ---
    report_lines: list[str] = [
        "# rules/context migration report (v2 context → entry inline match)",
        "",
        "alpha.11 期の dict 完全再編成の一部、 `tools/migrate_v2_context.py --apply` 結果。",
        "",
        "## 集計",
        "",
    ]

    total_rules = 0
    total_matches = 0
    pos_only_matches = 0
    pos_partial_matches = 0
    matched_surfaces = []
    missing_surfaces = []
    no_default_rules = []

    core_dir = ROOT / "core"

    for src_path in sorted(rules_context.glob("*.toml")):
        if src_path.name == "_genre.toml":
            continue
        src_data = tomllib.loads(src_path.read_text(encoding="utf-8"))
        rules = src_data.get("rule", [])
        if not rules:
            continue

        out_lines: list[str] = [
            f'# 機械変換: {src_path.relative_to(ROOT).as_posix()} → entry inline match',
            "#",
            "# 各 [entries.\"X\"] block を **既存 core/jukugo/ の対応 surface entry に",
            "# merge** するか、 surface 不在なら新規 entry として配置する。",
            "# 本 file は staging area、 lib は load しない (= role 不明)。",
            "",
            '[meta]',
            'schema_version = "2"',
            'role = "migrated_context"  # 仮 role、 実 merge 時に削除',
            'description = "rules/context migration の staging output (review 用、 lib loader 対象外)"',
            "",
        ]

        for rule in rules:
            total_rules += 1
            surface = rule.get("surface")
            if not surface:
                continue

            # 既存 core/ の entry を探す
            existing_file = find_existing_surface_file(surface, core_dir)
            if existing_file:
                matched_surfaces.append((surface, existing_file.relative_to(ROOT).as_posix()))
            else:
                missing_surfaces.append(surface)

            # default 取得:
            #   1. 旧 rule.default
            #   2. POS-only match の reading (= 「名詞 / 形容詞 のとき」 を表現していた、
            #      POS drop 後は default で代用する自然な意味)
            #   3. 1 つ目の non-POS match.reading
            default_reading = rule.get("default")
            todo_notes: list[str] = []
            if default_reading is None:
                no_default_rules.append(surface)
                # POS-only match の reading を優先採用 (= 同 reading が複数あれば 1 つ採用)
                pos_only_readings: list[str] = []
                for m in rule.get("match", []):
                    keys = set(m.keys())
                    if (keys - {"reading"}) == {"pos"}:
                        if isinstance(m.get("reading"), str):
                            pos_only_readings.append(m["reading"])
                if pos_only_readings:
                    # 同 reading が支配的な場合のみ自動採用、 異なれば人手判断
                    unique = set(pos_only_readings)
                    if len(unique) == 1:
                        default_reading = pos_only_readings[0]
                        todo_notes.append(
                            f"default 不在 (旧 rule)、 POS-only match の reading={default_reading!r} を default 採用 (POS={'/'.join(repr(rule['match'][i].get('pos','?')) for i in range(len(rule.get('match',[]))) if (set(rule['match'][i].keys()) - {'reading'}) == {'pos'})})"
                        )
                    else:
                        # 複数異なる POS-only reading は人手判断
                        first = pos_only_readings[0]
                        default_reading = first
                        todo_notes.append(
                            f"default 不在 (旧 rule)、 複数 POS-only reading が分岐 ({sorted(unique)})、 暫定 default={first!r}。 人手で確認要"
                        )
                if default_reading is None and rule.get("match"):
                    first_normalized, _ = normalize_match(rule["match"][0])
                    if "reading" in first_normalized:
                        default_reading = first_normalized["reading"]
                        todo_notes.append(
                            f"default 不在 + POS-only も無し、 第 1 match の reading={default_reading!r} を暫定 default に。 人手で確認要"
                        )
            if existing_file:
                todo_notes.append(
                    f"既存 entry: {existing_file.relative_to(ROOT).as_posix()} に merge 要"
                )
            else:
                # missing surface — 配置先示唆
                if len(surface) >= 2:
                    todo_notes.append(
                        "core/ に entry 不在、 適切な core/jukugo/<sub-dir>/<file>.toml に配置要"
                    )
                else:
                    todo_notes.append(
                        "core/ に entry 不在 (1 字 surface)、 core/unihan/ への配置 or [[kanji]] block 化要"
                    )

            # POS 計上
            for m in rule.get("match", []):
                total_matches += 1
                _, dropped = normalize_match(m)
                if dropped:
                    other_supported = (set(m.keys()) - UNSUPPORTED_FIELDS - {"reading"})
                    if not other_supported:
                        pos_only_matches += 1
                    else:
                        pos_partial_matches += 1

            entry_block = emit_entry(rule, surface, default_reading, todo_notes)
            out_lines.append(entry_block)
            out_lines.append("")

        # write per-source output
        out_path = args.output_dir / f"from_{src_path.stem}.toml"
        out_path.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {out_path.relative_to(ROOT).as_posix()}")

    # --- report 構築 ---
    report_lines += [
        f"- 総 rule 数: {total_rules}",
        f"- 総 match block 数: {total_matches}",
        f"- POS-only match block (= drop されて空 match): {pos_only_matches}",
        f"- POS + 他条件 mix match block (= POS だけ drop、 他は保持): {pos_partial_matches}",
        f"- core/ に既存 entry がある surface: {len(matched_surfaces)}",
        f"- core/ に entry 不在 surface (= 新規追加要): {len(missing_surfaces)}",
        f"- default 不在 rule (= 暫定 default 推定要): {len(no_default_rules)}",
        "",
        "## TODO",
        "",
        "### POS-only match (= literal 列挙で代用要)",
        "",
        "本 5 件は `pos = \"名詞\"` 等の汎用条件で reading 切替を表現していたが、",
        "新 format は POS 不採用 (Lindera 撤廃路線)。 各 surface で 「名詞のとき」 と",
        "「形容詞のとき」 が同じ reading なら **default reading で十分** (= match",
        "block 不要)。 異なる reading を要求するケースは `prev_eq_any` などで",
        "literal 列挙する。",
        "",
        "### core/ に entry 不在 (= 新規追加要)",
        "",
    ]
    for s in sorted(set(missing_surfaces)):
        report_lines.append(f"- `{s}` ({len(s)} 字)")
    report_lines += [
        "",
        "### default 不在 rule",
        "",
    ]
    for s in sorted(set(no_default_rules)):
        report_lines.append(f"- `{s}` (= 暫定 default は第 1 match から推定済、 人手確認要)")

    report_lines += [
        "",
        "### core/ 既存 entry への merge (= file 分散)",
        "",
        "本 30 surface は対応 core/ entry が既に存在、 inline match を **既存 entry",
        "に merge** すべき。 新規 detailed entry として置くと load 時に簡単 entry が",
        "上書きしてしまう (file 名 sort 順依存) リスクあり。",
        "",
    ]
    file_groups: dict[str, list[str]] = {}
    for s, f in matched_surfaces:
        file_groups.setdefault(f, []).append(s)
    for f in sorted(file_groups):
        surfaces = sorted(set(file_groups[f]))
        report_lines.append(f"- `{f}` (= {len(surfaces)} surface): {', '.join(f'`{s}`' for s in surfaces)}")

    report_path = args.output_dir / "MIGRATION_REPORT.md"
    report_path.write_text("\n".join(report_lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {report_path.relative_to(ROOT).as_posix()}")
    print()
    print(f"summary: {total_rules} rules / {total_matches} match blocks → "
          f"{len(matched_surfaces)} matched, {len(missing_surfaces)} missing, "
          f"{pos_only_matches} POS-only dropped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
