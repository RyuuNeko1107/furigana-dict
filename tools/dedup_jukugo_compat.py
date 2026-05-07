#!/usr/bin/env python3
"""
core/jukugo/*.toml と core/works/**/*.toml から、 surface 内に compat 異体字
key を含む entry を削除する (一度限りの cleanup)。

ja-furigana lib の処理順:
  1. 異体字正規化 (kana::normalize_text — compat 適用)
  2. 慣用語句先行確定
  3. token 化 + lookup (jukugo / unihan / 等)

つまり jukugo に「髙橋」 entry を持っても lib は「高橋」 で lookup するので
dead。 「高橋」 entry が同じ reading で居るか確認:
- 居る (collision なし): 旧 entry 削除のみ
- 居ない: 標準形に rename (旧削除 + 新追加、 元の file の末尾に append)
- 居る が reading 違う (collision): 削除 skip + 警告 (manual review)

走らせ方:
    python tools/dedup_jukugo_compat.py

冪等性: 既に重複なしなら no-op。 rename された entry の reading source は元の
異体字 entry の reading をそのまま使う (= 移植)。
"""
from __future__ import annotations

import glob
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize_surface(s: str, compat: dict[str, str]) -> str:
    """surface 内の各 char に compat[c] を適用した形を返す。"""
    return "".join(compat.get(c, c) for c in s)


def main() -> None:
    compat = tomllib.loads((ROOT / "core/compat.toml").read_text(encoding="utf-8")).get("map", {})

    # 全 jukugo + works を集めて global lookup map を作る
    all_files = sorted(
        glob.glob(str(ROOT / "core/jukugo/*.toml")) +
        glob.glob(str(ROOT / "core/works/**/*.toml"), recursive=True)
    )
    global_entries: dict[str, str] = {}
    for f in all_files:
        e = tomllib.loads(Path(f).read_text(encoding="utf-8")).get("entries", {})
        global_entries.update(e)

    total_removed = 0
    total_added = 0
    collisions: list[tuple[str, str, str, str, str]] = []

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
            ns = normalize_surface(surface, compat)
            if ns == surface:
                continue
            existing = global_entries.get(ns)
            if existing is None:
                # 標準形がどこにも居ない → 元 file に rename で追加
                to_add.append((ns, reading))
                global_entries[ns] = reading
                to_remove.append(surface)
                print(f"  {path.relative_to(ROOT)}: rename {surface}({reading}) → {ns}")
            elif existing == reading:
                # 標準形が同じ reading で居る → 削除のみ
                to_remove.append(surface)
                print(f"  {path.relative_to(ROOT)}: drop {surface}({reading}) (standard {ns} already exists)")
            else:
                # 衝突: 標準形が違う reading で居る → manual review
                collisions.append((str(path.relative_to(ROOT)), surface, reading, ns, existing))
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

    print(f"\nremoved: {total_removed}, added (rename target): {total_added}")
    if collisions:
        print(f"collisions ({len(collisions)}): manual review needed", file=sys.stderr)


if __name__ == "__main__":
    main()
