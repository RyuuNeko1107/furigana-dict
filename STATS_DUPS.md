# Cross-file duplicates (`core/jukugo/` + `core/works/`)

> `tools/list_dups.py` で自動生成。 commit 前にこのファイルが pull できれば
> どのファイルのどの surface が cross-file 重複してるか一目で分かる。
> divergent reading は `tools/validate.py` が CI で fail させる (修正必須)。

## ⚠️ 異なる reading (0 件 — critical)

(なし — divergent reading 0 件、 健全)

## 同一 reading (0 件)

実害なし (jukugo merge で同値が上書きされても reading 不変)。 整理目安として list 化。
長期的にどちらか 1 ファイルに寄せたいケースを発見する用。

(なし)
