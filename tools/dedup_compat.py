#!/usr/bin/env python3
"""
core/unihan/*.toml + core/jukugo/*.toml + core/works/**/*.toml から、
core/compat.toml の異体字 mapping 経由で dead 経路になる entry を整理する。
**冪等 / CI 自動実行** (.github/workflows/regen-stats.yml で master push 時)。

ja-furigana lib の処理順:
  1. 異体字正規化 (kana::normalize_text — compat 適用)
  2. 慣用語句先行確定
  3. token 化 + lookup (jukugo / unihan / 等)

入力に含まれる異体字 (例「髙」「乘」) は Step 1 で標準字 (「高」「乗」) に
置換され、 lookup は標準字でしか走らない。 unihan / jukugo に異体字 surface
を持っても **lib からは到達不可 (dead code)** で辞書サイズの無駄になる。

contributor が PR で誤って異体字 surface を追加しても、 master push 時に CI が
自動で本 script を走らせて 標準形に置換 / 削除する。 手動実行は通常不要。

レイヤ別の処理:

- **unihan (1 char surface)**: surface が compat key と完全一致なら drop
  (lib は normalize 後の標準字を別 file から lookup する)。
  self-map (key == value) の compat entry は対象外 (= 削除しない)。

- **jukugo / works (≥2 char surface)**: surface 内に compat key を含むなら
  全 char を normalize した標準形 surface を計算し、 以下のいずれか:
  - 標準形が **同 reading** で他に居る → 旧 entry を drop only
  - 標準形が **居ない** → 旧 entry を drop + 標準形を元 file の末尾に append
    (= rename、 reading は移植)
  - 標準形が **違う reading** で居る → collision、 manual review 警告 (stderr)

走らせ方 (手動):
    python tools/dedup_compat.py

冪等性: 既に重複なしなら no-op (file 書き戻し自体スキップ)。
"""
from __future__ import annotations

import glob
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPAT_TOML = ROOT / "core/compat.toml"
UNIHAN_DIR = ROOT / "core/unihan"

# unihan/ の各 file は header + [meta] + [entries] の決まった構造で書かれているので、
# rewrite 時に header 込みで再生成する。
META_DESCRIPTIONS_UNIHAN = {
    "joyo.toml":
        "常用漢字 2,136 字 (文化庁 2010-11-30 改訂、 内閣告示) — 利用頻度高、 default reading review 対象",
    "jinmeiyou.toml":
        "人名用漢字 (法務省、 子の名に使用可、 常用と重複する 128 字を除外した残り 855 字)",
    "jis_basic.toml":
        "JIS 基本 (CJK Basic Block U+4E00-U+9FFF のうち常用 / 人名用以外、 概ね JIS X 0208 第1+第2水準カバー)",
    "jis_supplement.toml":
        "JIS 補助 (CJK Extension A + Compatibility Ideographs、 概ね JIS X 0213 第3+第4水準カバー)",
    "extension.toml":
        "拡張漢字 (CJK Extension B 以降、 表外字 / 中国専用字 / 異体字、 機械的扱い、 ほぼ lib lookup されない)",
}


def normalize(s: str, compat: dict[str, str]) -> str:
    """surface 内の各 char に compat[c] を適用した形を返す。"""
    return "".join(compat.get(c, c) for c in s)


def write_unihan_bucket(path: Path, fname: str, entries: dict[str, str]) -> None:
    desc = META_DESCRIPTIONS_UNIHAN[fname]
    lines = [
        f"# {desc}",
        "#",
        "# このファイルは tools/classify_unihan.py で水準別自動分類された後、",
        "# tools/fill_missing_unihan.py で seed list の欠落分が KANJIDIC reading で補完され、",
        "# tools/dedup_compat.py で compat 経由 dead entries が除去された。",
        "# 個別 entry の手動編集は OK (PR で reading 修正等)。",
        "",
        "[meta]",
        f'description = "{desc}"',
        "",
        "[entries]",
    ]
    for k in sorted(entries):
        v = entries[k]
        lines.append(f'"{k}" = "{v}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def dedup_unihan(compat_keys: set[str]) -> int:
    """unihan/*.toml から compat key と一致する 1 char surface を削除。
    戻り値: 削除総数。"""
    total_removed = 0
    for fname in META_DESCRIPTIONS_UNIHAN:
        path = UNIHAN_DIR / fname
        if not path.exists():
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        entries: dict[str, str] = dict(data.get("entries", {}))
        before = len(entries)
        removed = [k for k in entries if k in compat_keys]
        for k in removed:
            del entries[k]
        if removed:
            write_unihan_bucket(path, fname, entries)
        print(f"unihan/{fname}: {before:,} → {len(entries):,} (-{len(removed)})")
        total_removed += len(removed)
    return total_removed


def dedup_jukugo_works(compat: dict[str, str]) -> tuple[int, int, int]:
    """jukugo/*.toml + works/**/*.toml から異体字を含む surface を整理。
    戻り値: (削除数, 標準形 rename 追加数, collision 数)。"""
    all_files = sorted(
        f for f in (
            glob.glob(str(ROOT / "core/jukugo/**/*.toml"), recursive=True) +
            glob.glob(str(ROOT / "core/works/**/*.toml"), recursive=True)
        )
        if Path(f).name != "_genre.toml" and not Path(f).name.endswith(".test.toml")
    )

    # global lookup (rename 時の collision 検出用)
    global_entries: dict[str, str] = {}
    for f in all_files:
        e = tomllib.loads(Path(f).read_text(encoding="utf-8")).get("entries", {})
        global_entries.update(e)

    total_removed = 0
    total_added = 0
    collisions = 0

    for f in all_files:
        path = Path(f)
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        entries = data.get("entries", {})
        if not entries:
            continue

        to_remove: list[str] = []
        to_add: list[tuple[str, str]] = []

        for surface, reading in entries.items():
            if not isinstance(reading, str):
                continue
            ns = normalize(surface, compat)
            if ns == surface:
                continue
            existing = global_entries.get(ns)
            if existing is None:
                to_add.append((ns, reading))
                global_entries[ns] = reading
                to_remove.append(surface)
                print(f"  {path.relative_to(ROOT)}: rename {surface}({reading}) → {ns}")
            elif existing == reading:
                to_remove.append(surface)
                print(f"  {path.relative_to(ROOT)}: drop {surface}({reading}) (standard {ns} already exists)")
            else:
                collisions += 1
                print(
                    f"  COLLISION {path.relative_to(ROOT)}: {surface}({reading}) vs standard {ns}({existing}) — skipping",
                    file=sys.stderr,
                )

        if not to_remove and not to_add:
            continue

        # raw text rewrite: entry 行を削除 + 末尾 append (周囲のコメント / [meta] / 区切り保持)
        text = path.read_text(encoding="utf-8")
        for surface in to_remove:
            pattern = re.compile(
                rf'^"{re.escape(surface)}"\s*=\s*"[^"]*"\s*$\n?',
                re.M,
            )
            text = pattern.sub("", text)
        if to_add:
            if not text.endswith("\n"):
                text += "\n"
            additions = "\n".join(f'"{k}" = "{v}"' for k, v in to_add)
            text += additions + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")

        total_removed += len(to_remove)
        total_added += len(to_add)

    return total_removed, total_added, collisions


def main() -> None:
    # ── 処理順 ──
    # 1. compat.toml を load + self-map (key == value) を除外
    #    → self-map は lib normalize で no-op (= 標準字に変化しない)、 unihan に
    #      残しておく必要があるので dedup 対象外。
    # 2. unihan/ を dedup (1 char surface 完全一致)
    #    → ja-furigana lib の Step 1 で異体字は標準字に置換されるので、 unihan に
    #      異体字 char を持つ意味なし。 1 char 単位なので global lookup 不要。
    # 3. jukugo / works を dedup (≥2 char surface 内に compat key char を含む)
    #    → file 横断 global_entries を作って collision 検出、 標準形が居なければ
    #      rename (旧 entry の reading を移植)。 file iteration は sorted で安定。
    #
    # 2 → 3 の順序は互いに独立 (unihan と jukugo は別 dict、 lib lookup でも
    # 別経路) なので結果は変わらないが、 layer が下から上に積み上がる感覚で
    # unihan を先に処理する。

    compat_data = tomllib.loads(COMPAT_TOML.read_text(encoding="utf-8")).get("map", {})
    compat = {k: v for k, v in compat_data.items() if k != v}
    compat_keys = set(compat.keys())
    print(f"compat keys (異体字 → 標準字、 self-map 除外): {len(compat_keys):,}")
    print()

    print("=== unihan/ ===")
    unihan_removed = dedup_unihan(compat_keys)

    print("\n=== jukugo / works ===")
    jukugo_removed, jukugo_added, collisions = dedup_jukugo_works(compat)

    print()
    print(f"unihan removed: {unihan_removed}")
    print(f"jukugo / works removed: {jukugo_removed}, rename added: {jukugo_added}")
    if collisions:
        print(f"collisions ({collisions}): manual review needed", file=sys.stderr)


if __name__ == "__main__":
    main()
