# Stats — `ja-furigana-dict`

辞書ボリュームのスナップショット。配布時の中身を一覧で把握する用。
git に commit されている master HEAD の状態を基準にする。

> **「サイズ」 列はコメント / 空行を除いた実効サイズ** (`tools/regen_stats.py` の
> `effective_bytes`)。 ja-furigana lib は `toml::from_str` で parse 時にコメント /
> 空行 / セクション区切り を破棄し、 entries の key→value だけを memory に乗せる
> ため、 disk file size そのままを出すと利用者が memory 使用量を実態より大きく
> 見積もる原因になる。 ここでは parse 入力として実質的に意味を持つ bytes を
> 数えて、 runtime memory load の **オーダー近似** とする。

> サマリ・件数表は `.github/workflows/regen-stats.yml` で **GitHub 側で自動再生成 + auto-commit**。
> contributor は TOML を編集して push (or PR merge) するだけで OK。
> 用途列は各ファイル冒頭の `[meta] description = "..."` から自動取得。
> ナラティブ部分 (利用側メモリ寄与 / カバレッジの偏り) は手動メンテ。

## サマリ

<!-- AUTO-GENERATED:SUMMARY:BEGIN -->
| カテゴリ | エントリ数 | サイズ |
|---|---:|---:|
| **単漢字** (`core/unihan.toml`、seed) | **43,749** | **796 KB** |
| **熟語** (`core/jukugo/*`、手動 PR メンテ) | **4,699** | **148 KB** |
| **作品造語** (`core/works/*`、作品単位 1 ファイル) | **113** | **3.7 KB** |
| **外来語** (`core/loanwords/*`、IT 用語等の英字 surface) | **160** | **5.0 KB** |
| **単漢字 override** (`core/single_overrides.toml`、 issue #15 限定解) | **1** | **110 B** |
| **異体字** (`core/compat.toml`) | **436** | **6.0 KB** |
| **エンジンルール** (`rules/`) | **256** | **15 KB** |
| **合計** | **49,414** | **973 KB** |
<!-- AUTO-GENERATED:SUMMARY:END -->

## 内訳

### `core/` — 語彙辞書

<!-- AUTO-GENERATED:CORE:BEGIN -->
| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| `core/unihan.toml` | 43,749 | 796 KB | 単漢字フォールバック (初期 seed + override 14 件) |
| `core/jukugo/general.toml` | 684 | 19 KB | 二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む) |
| `core/jukugo/personal_names.toml` | 214 | 8.6 KB | 人名 (戦国 / 平安 / 江戸 / 明治大正 / 古典作家、現代私人除く) |
| `core/jukugo/colors.toml` | 201 | 6.0 KB | 色名 / 染色 / 模様 / 古典色 / 鉱物色 |
| `core/jukugo/proper_nouns.toml` | 189 | 8.3 KB | 固有名詞 (大学 / 中央官庁 / 元号 / 歴史的事象、PR 募集中) |
| `core/jukugo/weather.toml` | 189 | 5.3 KB | 気象 / 天候 / 季語的気象 / 二十四節気 / 海洋気象 |
| `core/jukugo/arts.toml` | 184 | 5.4 KB | 古典芸能 / 武道 / 茶華香 / 工芸 |
| `core/jukugo/science.toml` | 184 | 5.3 KB | 自然科学 (天文 / 物理 / 化学 / 生物 / 地学) |
| `core/jukugo/animals.toml` | 183 | 4.8 KB | 動植物 / 魚介 / 鳥 / 昆虫 / 茸 / 海藻の難読 |
| `core/jukugo/music.toml` | 177 | 5.4 KB | 音楽ジャンル / 楽典 / 楽器 / 演奏 / 音楽用語 |
| `core/jukugo/literature.toml` | 176 | 5.9 KB | 古典文学 / 作品名 / 文学用語 / 詩歌 / 評論 |
| `core/jukugo/vehicles.toml` | 174 | 5.7 KB | 乗り物 / 交通手段 / 船舶 / 航空 / 鉄道 |
| `core/jukugo/clothes.toml` | 167 | 4.5 KB | 衣服 / 装束 / アクセサリー / 履物 |
| `core/jukugo/religions.toml` | 165 | 4.9 KB | 神道 / 仏教 / キリスト教 / イスラム / 儀礼 |
| `core/jukugo/place_names.toml` | 164 | 5.2 KB | 地名 (47 都道府県 / 主要都市 / 駅 / 寺社仏閣 / 観光地) |
| `core/jukugo/body_parts.toml` | 163 | 5.0 KB | 体の部位 / 内臓 / 骨格 / 筋肉 / 神経 |
| `core/jukugo/four_char.toml` | 153 | 6.4 KB | 四字熟語 (4 字 + 全 CJK 漢字) |
| `core/jukugo/emotions.toml` | 149 | 3.9 KB | 感情 / 心理状態 / 性格 / 心情 |
| `core/jukugo/politics.toml` | 149 | 4.1 KB | 政治 / 行政 / 立法 / 司法 / 国際関係 |
| `core/jukugo/architecture.toml` | 148 | 4.2 KB | 建築 / 建造物 / 寺社建築 / 城郭 / 庭園 |
| `core/jukugo/idioms.toml` | 148 | 7.6 KB | 慣用句 / ことわざ / 故事成語 (フレーズ単位) |
| `core/jukugo/foods.toml` | 145 | 4.2 KB | 食べ物 / 料理 / 和菓子 / 郷土料理 / 食材 / 調味料 |
| `core/jukugo/specialized.toml` | 144 | 4.5 KB | 専門用語 (医学 / 軍事 / 法学 / 経済 / IT / 工学) |
| `core/jukugo/sports.toml` | 144 | 4.6 KB | 近代スポーツ / 球技 / 陸上 / 水泳 / 体操 / 大会 |
| `core/jukugo/abstracts.toml` | 135 | 3.5 KB | 美意識 / 古典文学 / 仏教 / 儒教 / 思想 |
| `core/jukugo/finance.toml` | 97 | 3.5 KB | 経済金融 (商品 / 市場 / 会計 / 税務 / 保険) |
| `core/jukugo/railway.toml` | 73 | 2.4 KB | 鉄道専門用語 (線路 / 駅 / 運行 / 車両) |
| `core/works/game/touhou.toml` | 71 | 2.4 KB | 東方Project (上海アリス幻樂団): キャラクター名 / 場所 / 用語 (公式読みベース) |
| `core/works/literature/genji_monogatari.toml` | 42 | 1.3 KB | 源氏物語 (紫式部): 登場人物 / 巻名 / 場所 (平安中期、 古典定本ベース) |
| `core/loanwords/it.toml` | 160 | 5.0 KB | IT 用語 / プログラミング言語 / OSS / クラウドサービス / 技術企業 (ASCII surface) |
| `core/single_overrides.toml` | 1 | 110 B | 単漢字 default reading override (issue #15 の限定解) |
| `core/compat.toml` | 436 | 6.0 KB | 異体字 → 標準字 (髙→高 等) |
| **小計** | **49,158** | **958 KB** | (jukugo: 26 ファイル / **4,699 件** / 148 KB ・ works: 2 ファイル / **113 件** / 3.7 KB) |
<!-- AUTO-GENERATED:CORE:END -->

### `rules/` — エンジンルール

<!-- AUTO-GENERATED:RULES:BEGIN -->
| ファイル | エントリ数 | サイズ | 内容 |
|---|---:|---:|---|
| `rules/days.toml` | 31 | 844 B | 1〜31 日の特殊読み (1→ツイタチ 等) |
| `rules/scales.toml` | 19 | 848 B | 万 / 億 / 兆 / 京 等の大数スケール |
| `rules/units.toml` | 17 | 631 B | SI 単位 (km / kg / mL …、case-insensitive) |
| `rules/symbols.toml` | 10 | 223 B | 記号読み (+ / − / % / ‰ …) |
| `rules/latin.toml` | 26 | 436 B | ラテン文字読み (A→エー …) |
| `rules/numeric_phrases.toml` | 23 | 701 B | 数字を含む例外語句 (二十歳→ハタチ 等) |
| `rules/postprocess.toml` | 2 | 160 B | 後処理 regex 置換 (Step 7、mode 別) |
| `rules/counters/*.toml` (7 ファイル) | 76 | 3.9 KB | 助数詞ルール (本 / 匹 / 個 / 年 / 月 / 日 …、連濁 / 促音化 / kana 末尾置換) |
| `rules/context/*.toml` (3 ファイル) | 52 | 6.9 KB | 文脈依存読み (一日→ツイタチ/イチニチ 等) |
| **小計** | **256** | **15 KB** | |
<!-- AUTO-GENERATED:RULES:END -->

(rules はエントリ数より「ルールパターン数」の方が意味的に正しいが、ここでは
TOML の top-level エントリ数を概数として表記)

## 利用側 (`ja-furigana`) でのメモリ寄与

`ja-furigana-cli serve` (HTTP サーバー mode) 起動直後の Windows 実測値 (release build、dict ~1 MB 時点):

| 計測指標 | 値 |
|---|---:|
| WorkingSet (実 RSS) | **~54 MB** |
| PrivateMemory | **~28 MB** |
| バイナリ on-disk | **~64 MB** (Lindera + IPADIC を embed) |

内訳の概算 (実測ではなく推定):

| 構成要素 | メモリ寄与 |
|---|---:|
| Lindera + IPADIC (形態素解析の辞書、 binary embed) | **大半** (~30-50 MB) ← 支配的 |
| 本リポジトリの語彙辞書 + ルール | **数 MB** (TOML を `HashMap` 等に展開後、 dict サイズの 2-3x オーダー) |
| その他 (Rust runtime / Tokio multi-thread runtime / system libs) | **数 MB** |

dict (jukugo + works) が 10x に育っても、本リポジトリ側の寄与は **数 MB オーダー** に収まる試算
(unihan は seed として固定サイズ、jukugo の伸びが本体)。
Lindera + IPADIC が支配的なので、 dict 拡充によるメモリ圧迫は当面気にしなくて良い。

> 計測コマンド (PowerShell):
> ```powershell
> $p = Start-Process -FilePath 'target\release\furigana.exe' `
>   -ArgumentList 'serve','--bind','127.0.0.1:18765' -PassThru
> Start-Sleep -Seconds 2
> $p.Refresh()
> Write-Output ('WS={0} MB, Private={1} MB' -f `
>   [int]($p.WorkingSet64/1MB), [int]($p.PrivateMemorySize64/1MB))
> Stop-Process $p
> ```

## カバレッジの偏り

- **単漢字 (unihan)** はほぼ全 CJK 漢字をカバー (43k 字)
- **熟語 (jukugo)** は初期 seed の 1.7k 件 → seed 拡充で 4k 件超、24 ファイルに分類
- カテゴリ別の件数は上の `core/` テーブルを参照 (自動生成、最新値が反映される)
- **現代の私人 / 私企業 / アニメ作品 / 商標** は seed していない (誤読リスク回避方針)。
  公式読みが定まっていれば PR 単位で個別判断。

→ 体感では「**著名な漢字熟語 / 単漢字 / 古典 / 学術 / 自然物は読める、現代私人 / 商標 / 私企業は手薄**」。
PR 大歓迎。

## 更新方法

**何もしなくて OK**。TOML を編集して master に push (or PR merge) すれば、
`.github/workflows/regen-stats.yml` が自動で `tools/regen_stats.py` を走らせて
diff があれば `chore: regen STATS.md [skip stats]` で auto-commit する。

新規ファイルを追加した場合は、ファイル冒頭に以下を入れるだけ:

```toml
[meta]
description = "<このファイルの 1 行説明>"

[entries]
...
```

`tools/regen_stats.py` がこの `[meta].description` を STATS.md の用途列に取り込む。

ローカルで手動再生成したい場合は `python3 tools/regen_stats.py` で生成可能 (CI と同じ挙動)。
