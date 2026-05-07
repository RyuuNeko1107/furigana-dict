# Stats — `ja-furigana-dict`

辞書ボリュームのスナップショット。配布時の中身を一覧で把握する用。
git に commit されている master HEAD の状態を基準にする。

> サマリ・件数表は `tools/regen_stats.py` で自動再生成される。
> 用途列の編集はスクリプト内 `DESCRIPTIONS` を直接いじる。
> ナラティブ部分 (利用側メモリ寄与 / カバレッジの偏り) は手動メンテ。

## サマリ

<!-- AUTO-GENERATED:SUMMARY:BEGIN -->
| カテゴリ | エントリ数 | サイズ |
|---|---:|---:|
| **単漢字** (`core/unihan.toml`、本番 dump) | **43,749** | **796 KB** |
| **熟語** (`core/jukugo/*`、手動 PR メンテ) | **4,351** | **175 KB** |
| **作品造語** (`core/works/*`、作品単位 1 ファイル) | **72** | **4.4 KB** |
| **異体字** (`core/compat.toml`) | **436** | **6.3 KB** |
| **エンジンルール** (`rules/`) | **249** | **25 KB** |
| **合計** | **48,857** | **1007 KB** |
<!-- AUTO-GENERATED:SUMMARY:END -->

配布物 (`furigana-dict-vX.Y.Z.tar.gz`) は gzip 圧縮後 ~226 KB (`v0.1.2` 時点)。
ラウンド 7/8 で大幅拡充したため、次回 release で再計測予定。

## 内訳

### `core/` — 語彙辞書

<!-- AUTO-GENERATED:CORE:BEGIN -->
| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| `core/unihan.toml` | 43,749 | 796 KB | 単漢字フォールバック (本番 ryuuneko.com 由来 + override 14 件) |
| `core/jukugo/general.toml` | 739 | 20 KB | 二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む) |
| `core/jukugo/personal_names.toml` | 214 | 9.5 KB | 人名 (戦国 / 平安 / 江戸 / 明治大正 / 古典作家、現代私人除く) |
| `core/jukugo/colors.toml` | 201 | 6.9 KB | 色名 / 染色 / 模様 / 古典色 / 鉱物色 |
| `core/jukugo/proper_nouns.toml` | 193 | 9.7 KB | 固有名詞 (大学 / 中央官庁 / 元号 / 歴史的事象、PR 募集中) |
| `core/jukugo/animals.toml` | 186 | 5.8 KB | 動植物 / 魚介 / 鳥 / 昆虫 / 茸 / 海藻の難読 |
| `core/jukugo/music.toml` | 180 | 10 KB | 音楽ジャンル / 楽典 / 楽器 / 演奏 / 音楽用語 |
| `core/jukugo/arts.toml` | 178 | 10.0 KB | 古典芸能 / 武道 / 茶華香 / 工芸 |
| `core/jukugo/body_parts.toml` | 163 | 5.5 KB | 体の部位 / 内臓 / 骨格 / 筋肉 / 神経 |
| `core/jukugo/place_names.toml` | 163 | 5.5 KB | 地名 (47 都道府県 / 主要都市 / 駅 / 寺社仏閣 / 観光地) |
| `core/jukugo/religions.toml` | 154 | 5.9 KB | 神道 / 仏教 / キリスト教 / イスラム / 儀礼 |
| `core/jukugo/abstracts.toml` | 152 | 5.3 KB | 美意識 / 古典文学 / 仏教 / 儒教 / 思想 |
| `core/jukugo/emotions.toml` | 150 | 5.0 KB | 感情 / 心理状態 / 性格 / 心情 |
| `core/jukugo/politics.toml` | 149 | 5.1 KB | 政治 / 行政 / 立法 / 司法 / 国際関係 |
| `core/jukugo/literature.toml` | 148 | 10 KB | 古典文学 / 作品名 / 文学用語 / 詩歌 / 評論 |
| `core/jukugo/specialized.toml` | 145 | 5.4 KB | 専門用語 (医学 / 軍事 / 法学 / 経済 / IT / 工学) |
| `core/jukugo/sports.toml` | 144 | 9.1 KB | 近代スポーツ / 球技 / 陸上 / 水泳 / 体操 / 大会 |
| `core/jukugo/architecture.toml` | 143 | 8.7 KB | 建築 / 建造物 / 寺社建築 / 城郭 / 庭園 |
| `core/jukugo/foods.toml` | 141 | 4.8 KB | 食べ物 / 料理 / 和菓子 / 郷土料理 / 食材 / 調味料 |
| `core/jukugo/four_char.toml` | 141 | 6.3 KB | 四字熟語 (4 字 + 全 CJK 漢字) |
| `core/jukugo/vehicles.toml` | 137 | 5.1 KB | 乗り物 / 交通手段 / 船舶 / 航空 / 鉄道 |
| `core/jukugo/weather.toml` | 137 | 4.8 KB | 気象 / 天候 / 季語的気象 / 二十四節気 / 海洋気象 |
| `core/jukugo/science.toml` | 136 | 5.2 KB | 自然科学 (天文 / 物理 / 化学 / 生物 / 地学) |
| `core/jukugo/clothes.toml` | 135 | 4.4 KB | 衣服 / 装束 / アクセサリー / 履物 |
| `core/jukugo/idioms.toml` | 122 | 6.8 KB | 慣用句 / ことわざ / 故事成語 (フレーズ単位) |
| `core/works/game/touhou.toml` | 72 | 4.4 KB | 東方Project (上海アリス幻樂団): キャラクター名 / 場所 / 用語 (公式読みベース) |
| `core/compat.toml` | 436 | 6.3 KB | 異体字 → 標準字 (髙→高 等) |
| **小計** | **48,608** | **982 KB** | (jukugo: 24 ファイル / **4,351 件** / 175 KB ・ works: 1 ファイル / **72 件** / 4.4 KB) |
<!-- AUTO-GENERATED:CORE:END -->

### `rules/` — エンジンルール

<!-- AUTO-GENERATED:RULES:BEGIN -->
| ファイル | エントリ数 | サイズ | 内容 |
|---|---:|---:|---|
| `rules/days.toml` | 31 | 1.0 KB | 1〜31 日の特殊読み (1→ツイタチ 等) |
| `rules/scales.toml` | 19 | 988 B | 万 / 億 / 兆 / 京 等の大数スケール |
| `rules/units.toml` | 17 | 811 B | SI 単位 (km / kg / mL …、case-insensitive) |
| `rules/symbols.toml` | 10 | 238 B | 記号読み (+ / − / % / ‰ …) |
| `rules/latin.toml` | 26 | 554 B | ラテン文字読み (A→エー …) |
| `rules/numeric_phrases.toml` | 23 | 892 B | 数字を含む例外語句 (二十歳→ハタチ 等) |
| `rules/postprocess.toml` | 2 | 1.4 KB | 後処理 regex 置換 (本番 Step 7 互換) |
| `rules/counters/*.toml` (7 ファイル) | 76 | 9.0 KB | 助数詞ルール (本 / 匹 / 個 / 年 / 月 / 日 …、連濁 / 促音化 / kana 末尾置換) |
| `rules/context/*.toml` (3 ファイル) | 45 | 9.9 KB | 文脈依存読み (一日→ツイタチ/イチニチ 等) |
| **小計** | **249** | **25 KB** | |
<!-- AUTO-GENERATED:RULES:END -->

(rules はエントリ数より「ルールパターン数」の方が意味的に正しいが、ここでは
TOML の top-level エントリ数を概数として表記)

## 利用側 (`ja-furigana`) でのメモリ寄与

`ja-furigana-cli` 起動時のプロセス全体は **~70 MB** だが、その内訳:

| 構成要素 | メモリ寄与 |
|---|---:|
| Lindera + IPADIC (形態素解析の辞書) | **~50 MB** ← 支配的 |
| 本リポジトリの語彙辞書 + ルール | **~3 MB** (TOML を `HashMap` 等に展開後) |
| その他 (Rust runtime / Tokio / etc) | ~17 MB |

10 万件規模の辞書になっても、本リポジトリ側の寄与は ~10 MB 程度に収まる試算。
Lindera が支配的なので、辞書増加によるメモリ圧迫は当面気にしなくて良い。

## カバレッジの偏り

- **単漢字 (unihan)** はほぼ全 CJK 漢字をカバー (43k 字)
- **熟語 (jukugo)** は本番 ryuuneko.com 実用 1.7k 件 → ラウンド 4-8 で seed 拡充して 3.3k 件、24 ファイルに分類
- カテゴリ別の件数は上の `core/` テーブルを参照 (自動生成、最新値が反映される)
- **現代の私人 / 私企業 / アニメ作品 / 商標** は seed していない (誤読リスク回避方針)。
  公式読みが定まっていれば PR 単位で個別判断。

→ 体感では「**著名な漢字熟語 / 単漢字 / 古典 / 学術 / 自然物は読める、現代私人 / 商標 / 私企業は手薄**」。
PR 大歓迎。

## 更新方法

サマリと件数表は **自動生成** なので、TOML を編集したあとは:

```sh
python3 tools/regen_stats.py
git diff STATS.md
git add STATS.md
```

新規ファイルを追加した場合は `tools/regen_stats.py` 内の `DESCRIPTIONS` 辞書に
`"core/jukugo/<new>.toml": "用途説明"` を追加してから再生成すること。

CI (`.github/workflows/validate.yml`) は再生成して `git diff --exit-code STATS.md`
が non-zero ならジョブを fail させる (drift 検知)。
