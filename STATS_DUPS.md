# Cross-file duplicates (`core/jukugo/` + `core/works/`)

> `tools/list_dups.py` で自動生成。 commit 前にこのファイルが pull できれば
> どのファイルのどの surface が cross-file 重複してるか一目で分かる。
> divergent reading は `tools/validate.py` が CI で fail させる (修正必須)。

## ⚠️ 異なる reading (0 件 — critical)

(なし — divergent reading 0 件、 健全)

## 同一 reading (19 件)

実害なし (jukugo merge で同値が上書きされても reading 不変)。 整理目安として list 化。
長期的にどちらか 1 ファイルに寄せたいケースを発見する用。

| surface | reading | files |
|---|---|---|
| 中華丼 | チュウカドン | `core/jukugo/basic/general.toml`, `core/jukugo/nature/foods.toml` |
| 元素 | ゲンソ | `core/jukugo/basic/general.toml`, `core/jukugo/nature/science.toml` |
| 単衣 | ヒトエ | `core/jukugo/basic/general.toml`, `core/jukugo/objects/clothes.toml` |
| 唐揚げ | カラアゲ | `core/jukugo/basic/general.toml`, `core/jukugo/nature/foods.toml` |
| 山風 | ヤマカゼ | `core/jukugo/basic/general.toml`, `core/jukugo/nature/weather.toml` |
| 巫女 | ミコ | `core/jukugo/basic/general.toml`, `core/jukugo/humanities/religions.toml` |
| 水素 | スイソ | `core/jukugo/basic/general.toml`, `core/jukugo/nature/science.toml` |
| 海老天 | エビテン | `core/jukugo/basic/general.toml`, `core/jukugo/nature/foods.toml` |
| 海風 | ウミカゼ | `core/jukugo/basic/general.toml`, `core/jukugo/nature/weather.toml` |
| 石川 | イシカワ | `core/jukugo/nature/place_names.toml`, `core/jukugo/proper/personal_names.toml` |
| 神輿 | ミコシ | `core/jukugo/basic/general.toml`, `core/jukugo/objects/vehicles.toml` |
| 素人 | シロウト | `core/jukugo/basic/general.toml`, `core/jukugo/humanities/arts.toml` |
| 親子丼 | オヤコドン | `core/jukugo/basic/general.toml`, `core/jukugo/nature/foods.toml` |
| 豚丼 | ブタドン | `core/jukugo/basic/general.toml`, `core/jukugo/nature/foods.toml` |
| 質素 | シッソ | `core/jukugo/basic/general.toml`, `core/jukugo/humanities/abstracts.toml` |
| 雨乞い | アマゴイ | `core/jukugo/basic/general.toml`, `core/jukugo/nature/weather.toml` |
| 雨垂れ | アマダレ | `core/jukugo/basic/general.toml`, `core/jukugo/nature/weather.toml` |
| 鯛焼き | タイヤキ | `core/jukugo/basic/general.toml`, `core/jukugo/nature/foods.toml` |
| 鰻丼 | ウナドン | `core/jukugo/basic/general.toml`, `core/jukugo/nature/foods.toml` |
