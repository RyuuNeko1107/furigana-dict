# Stats — `ja-furigana-dict`

辞書ボリュームのスナップショット。配布時の中身を一覧で把握する用。
git に commit されている master HEAD の状態を基準にする。

> 列の意味:
> - **エントリ数**: `[entries]` / `[map]` / `[[rule]]` 等の有効レコード数
> - **サイズ**: コメント / 空行を除いた実効サイズ (lib `toml::from_str` は parse 時にコメントを
>   drop するので、 disk file size より memory load の概算に近い)
>
> inline test (`*.test.toml`) と corpus regression (`tests/corpus/*.toml`) のカバレッジは
> 末尾の [QA カバレッジ](#qa-カバレッジ) section に独立してまとめてある。
> release tar から exclude / lib runtime memory にも乗らないため、 データ集計とは別軸で扱う
> (サイズも release 影響無しのため省略)。

> サマリ・件数表は `.github/workflows/regen-stats.yml` で **GitHub 側で自動再生成 + auto-commit**。
> contributor は TOML を編集して push (or PR merge) するだけで OK。
> 用途列は各ファイル冒頭の `[meta] description = "..."` から自動取得。
> ナラティブ部分 (利用側メモリ寄与 / カバレッジの偏り) は手動メンテ。

## サマリ

<!-- AUTO-GENERATED:SUMMARY:BEGIN -->
| カテゴリ | エントリ数 | サイズ |
|---|---:|---:|
| [**単漢字**](#単漢字) (`core/unihan/*`、 水準別 5 ファイル) | **40,688** | **739 KB** |
| [**熟語**](#熟語) (`core/jukugo/*`、手動 PR メンテ) | **8,282** | **278 KB** |
| [**作品造語**](#作品造語) (`core/works/*`、作品単位 1 ファイル) | **311** | **10 KB** |
| [**外来語**](#外来語) (`core/loanwords/*`、IT 用語等の英字 surface) | **168** | **5.2 KB** |
| [**分類前 inbox**](#分類前-inbox) (`core/_inbox.toml`、 後で振り分ける一時置き場) | **0** | **180 B** |
| [**単漢字 [[kanji]] format**](#単漢字-kanji-format) (`core/kanji/*`、 default + 文脈分岐 reading) | **2,767** | **185 KB** |
| [**異体字**](#異体字) (`core/compat.toml`) | **435** | **6.1 KB** |
| [**エンジンルール**](#エンジンルール) (`rules/`) | **228** | **13 KB** |
| **合計** | **52,879** | **1.21 MB** |
<!-- AUTO-GENERATED:SUMMARY:END -->

## 内訳

`core/` (語彙辞書) はカテゴリ別 sub-section に、 `rules/` (エンジンルール) は最後にまとめて。 summary 表のカテゴリ名クリックで該当 sub-section へジャンプ可。

<!-- AUTO-GENERATED:CORE:BEGIN -->
### 単漢字

`core/unihan/*` — 水準別 5 ファイル。 lib の resolve_reading 6 段階で最終 fallback (Step 6) として参照される。 default reading review は使用頻度の高い `joyo.toml` を中心に。

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/unihan/joyo.toml`](core/unihan/joyo.toml) | 9 | 1.0 KB | 常用漢字 2,136 字 (文化庁 2010-11-30 改訂、 内閣告示) — 利用頻度高、 default reading review 対象 |
| [`core/unihan/jinmeiyou.toml`](core/unihan/jinmeiyou.toml) | 0 | 185 B | 人名用漢字 (法務省、 子の名に使用可、 常用と重複する 128 字を除外した残り 855 字) |
| [`core/unihan/jis_basic.toml`](core/unihan/jis_basic.toml) | 13,051 | 236 KB | JIS 基本 (CJK Basic Block U+4E00-U+9FFF のうち常用 / 人名用以外、 概ね JIS X 0208 第1+第2水準カバー) |
| [`core/unihan/jis_supplement.toml`](core/unihan/jis_supplement.toml) | 4,825 | 83 KB | JIS 補助 (CJK Extension A + Compatibility Ideographs、 概ね JIS X 0213 第3+第4水準カバー) |
| [`core/unihan/extension.toml`](core/unihan/extension.toml) | 22,803 | 418 KB | 拡張漢字 (CJK Extension B 以降、 表外字 / 中国専用字 / 異体字、 機械的扱い、 ほぼ lib lookup されない) |
| **小計** (5 ファイル) | **40,688** | **739 KB** | |

### 熟語

`core/jukugo/<genre>/*` — 手動 PR メンテのジャンル別 jukugo (≥ 2 字 surface)。 lib の Step 3 (jukugo lookup) で Lindera より優先採用。 各 genre dir の `_genre.toml` がカテゴリ description を持つ。

**合計**: 8,282 件 / 278 KB (genre 6 区分)

#### 自然・生命

動植物 / 食品 / 気象 / 体の部位 / 地名 / 自然科学 — 自然界と生物に関わる語彙

`core/jukugo/nature/` — 6 ファイル

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/jukugo/nature/weather.toml`](core/jukugo/nature/weather.toml) | 189 | 5.7 KB | 気象 / 天候 / 季語的気象 / 二十四節気 / 海洋気象 |
| [`core/jukugo/nature/animals.toml`](core/jukugo/nature/animals.toml) | 186 | 5.0 KB | 動植物 / 魚介 / 鳥 / 昆虫 / 茸 / 海藻の難読 |
| [`core/jukugo/nature/science.toml`](core/jukugo/nature/science.toml) | 184 | 5.4 KB | 自然科学 (天文 / 物理 / 化学 / 生物 / 地学) |
| [`core/jukugo/nature/body_parts.toml`](core/jukugo/nature/body_parts.toml) | 171 | 5.2 KB | 体の部位 / 内臓 / 骨格 / 筋肉 / 神経 |
| [`core/jukugo/nature/place_names.toml`](core/jukugo/nature/place_names.toml) | 167 | 5.3 KB | 地名 (47 都道府県 / 主要都市 / 駅 / 寺社仏閣 / 観光地) |
| [`core/jukugo/nature/foods.toml`](core/jukugo/nature/foods.toml) | 157 | 4.6 KB | 食べ物 / 料理 / 和菓子 / 郷土料理 / 食材 / 調味料 |
| **小計** (6 ファイル) | **1,054** | **31 KB** | |

#### 人文・芸術

古典文学 / 芸術 / 慣用句 / 抽象概念 / 音楽 / 宗教 / 感情 — 人の精神活動に関わる語彙

`core/jukugo/humanities/` — 7 ファイル

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/jukugo/humanities/arts.toml`](core/jukugo/humanities/arts.toml) | 188 | 5.5 KB | 古典芸能 / 武道 / 茶華香 / 工芸 |
| [`core/jukugo/humanities/music.toml`](core/jukugo/humanities/music.toml) | 177 | 5.5 KB | 音楽ジャンル / 楽典 / 楽器 / 演奏 / 音楽用語 |
| [`core/jukugo/humanities/literature.toml`](core/jukugo/humanities/literature.toml) | 176 | 6.0 KB | 古典文学 / 作品名 / 文学用語 / 詩歌 / 評論 |
| [`core/jukugo/humanities/religions.toml`](core/jukugo/humanities/religions.toml) | 165 | 5.0 KB | 神道 / 仏教 / キリスト教 / イスラム / 儀礼 |
| [`core/jukugo/humanities/emotions.toml`](core/jukugo/humanities/emotions.toml) | 149 | 4.0 KB | 感情 / 心理状態 / 性格 / 心情 |
| [`core/jukugo/humanities/idioms.toml`](core/jukugo/humanities/idioms.toml) | 148 | 7.6 KB | 慣用句 / ことわざ / 故事成語 (フレーズ単位) |
| [`core/jukugo/humanities/abstracts.toml`](core/jukugo/humanities/abstracts.toml) | 135 | 3.6 KB | 美意識 / 古典文学 / 仏教 / 儒教 / 思想 |
| **小計** (7 ファイル) | **1,138** | **37 KB** | |

#### 社会・制度

政治 / 金融 / スポーツ / 専門用語 — 社会構造 / 制度に関わる語彙

`core/jukugo/society/` — 4 ファイル

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/jukugo/society/politics.toml`](core/jukugo/society/politics.toml) | 151 | 4.2 KB | 政治 / 行政 / 立法 / 司法 / 国際関係 |
| [`core/jukugo/society/specialized.toml`](core/jukugo/society/specialized.toml) | 144 | 4.5 KB | 専門用語 (医学 / 軍事 / 法学 / 経済 / IT / 工学) |
| [`core/jukugo/society/sports.toml`](core/jukugo/society/sports.toml) | 144 | 4.6 KB | 近代スポーツ / 球技 / 陸上 / 水泳 / 体操 / 大会 |
| [`core/jukugo/society/finance.toml`](core/jukugo/society/finance.toml) | 97 | 3.5 KB | 経済金融 (商品 / 市場 / 会計 / 税務 / 保険) |
| **小計** (4 ファイル) | **536** | **17 KB** | |

#### 固有名詞

人名 / 大学・官庁・元号などの固有名詞 — 個別実体を指す語彙

`core/jukugo/proper/` — 2 ファイル

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/jukugo/proper/personal_names.toml`](core/jukugo/proper/personal_names.toml) | 253 | 9.6 KB | 人名 (戦国 / 平安 / 江戸 / 明治大正 / 古典作家、現代私人除く) |
| [`core/jukugo/proper/proper_nouns.toml`](core/jukugo/proper/proper_nouns.toml) | 188 | 8.2 KB | 固有名詞 (大学 / 中央官庁 / 元号 / 歴史的事象、PR 募集中) |
| **小計** (2 ファイル) | **441** | **18 KB** | |

#### 物体・工芸

色 / 衣服 / 乗り物 / 建築 / 鉄道 — 人工物と工芸に関わる語彙

`core/jukugo/objects/` — 5 ファイル

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/jukugo/objects/colors.toml`](core/jukugo/objects/colors.toml) | 201 | 6.0 KB | 色名 / 染色 / 模様 / 古典色 / 鉱物色 |
| [`core/jukugo/objects/vehicles.toml`](core/jukugo/objects/vehicles.toml) | 174 | 5.7 KB | 乗り物 / 交通手段 / 船舶 / 航空 / 鉄道 |
| [`core/jukugo/objects/clothes.toml`](core/jukugo/objects/clothes.toml) | 167 | 4.6 KB | 衣服 / 装束 / アクセサリー / 履物 |
| [`core/jukugo/objects/architecture.toml`](core/jukugo/objects/architecture.toml) | 147 | 4.2 KB | 建築 / 建造物 / 寺社建築 / 城郭 / 庭園 |
| [`core/jukugo/objects/railway.toml`](core/jukugo/objects/railway.toml) | 73 | 2.4 KB | 鉄道専門用語 (線路 / 駅 / 運行 / 車両) |
| **小計** (5 ファイル) | **762** | **23 KB** | |

#### 基本・構造

一般熟語 / 四字熟語 — 全カテゴリに横断する基本語彙

`core/jukugo/basic/` — 2 ファイル

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/jukugo/basic/general.toml`](core/jukugo/basic/general.toml) | 4,168 | 144 KB | 二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む) |
| [`core/jukugo/basic/four_char.toml`](core/jukugo/basic/four_char.toml) | 183 | 7.6 KB | 四字熟語 (4 字 + 全 CJK 漢字) |
| **小計** (2 ファイル) | **4,351** | **152 KB** | |


### 作品造語

`core/works/<medium>/*` — 媒体 (game / literature 等) ごとに 1 作品 1 ファイル。 原則は公式読み (一般通称として定着していれば採録可)、 出典コメント必須、 古典読みは現代読み無い場合のみ。

**合計**: 311 件 / 10 KB (genre 2 区分)

#### ゲーム

ゲーム作品の固有名詞 (キャラクター / 場所 / 用語、 公式読みベース)

`core/works/game/` — 1 ファイル

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/works/game/touhou.toml`](core/works/game/touhou.toml) | 269 | 8.8 KB | 東方Project (上海アリス幻樂団): キャラクター名 / 場所 / 用語 (公式読みベース) |

#### 文学

文学作品の固有名詞 (登場人物 / 巻名 / 場所、 古典定本ベース)

`core/works/literature/` — 1 ファイル

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/works/literature/genji_monogatari.toml`](core/works/literature/genji_monogatari.toml) | 42 | 1.3 KB | 源氏物語 (紫式部): 登場人物 / 巻名 / 場所 (平安中期、 古典定本ベース) |


### 外来語

`core/loanwords/*` — ASCII surface (英字始まり) を完全一致 lookup する別管理辞書。 case-fold + 全角→半角 正規化。

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/loanwords/it.toml`](core/loanwords/it.toml) | 168 | 5.2 KB | IT 用語 / プログラミング言語 / OSS / クラウドサービス / 技術企業 (ASCII surface) |

### 分類前 inbox

`core/_inbox.toml` — 「読みは追加したいが genre dir の振り分け判断付かない」 用の一時置き場。 lib 側は `[meta] role = "jukugo"` で jukugo として load される (≥2 字 surface 限定)。 maintainer の整理タイミングで適切な `core/jukugo/<genre>/<file>.toml` に移動する。

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/_inbox.toml`](core/_inbox.toml) | 0 | 180 B | 分類前の一時 inbox (≥2 字 surface、 内容が貯まったら適切な genre dir に振り分ける) |

### 単漢字 [[kanji]] format

`core/kanji/*` — 1 字 surface に対する `[[kanji]]` block 形式 entry。 各 block は `char` (1 字必須) + `default` reading + optional `[[kanji.match]]` 配列 (= 文脈分岐 reading、 matcher vocabulary は entry inline match と同一)。 「ルール数」 列は **block 数 + 各 [[kanji.match]] 合計** (= default + 文脈分岐の総ルール数)。

| ファイル | 文字数 | ルール数 | サイズ | 用途 |
|---|---:|---:|---:|---|
| [`core/kanji/overrides.toml`](core/kanji/overrides.toml) | 2,767 | 3,585 | 185 KB | 単漢字 default override + 文脈分岐 reading |

### 異体字

`core/compat.toml` — 異体字 → 標準字の正規化マッピング (例: 髙→高)。 reading lookup 前の前処理として lib が参照。

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| [`core/compat.toml`](core/compat.toml) | 435 | 6.1 KB | 異体字 → 標準字の正規化マップ (髙→高 等、 lib Step 1 で入力テキストを正規化) |
<!-- AUTO-GENERATED:CORE:END -->

### エンジンルール

`rules/` — エンジン挙動 (助数詞 / 文脈 / 後処理 等) を制御するルール群。 lib コードに embed されるのではなく、 ここで宣言的に外部化されている。

<!-- AUTO-GENERATED:RULES:BEGIN -->
**合計**: 228 エントリ / 274 ルール / 13 KB (genre 2 区分)

#### 数値系

日付 / 大数 / 助数詞 / 数値慣用句 — 数値表現の読み解決

`rules/numbers/` — 10 ファイル

| ファイル | エントリ数 | ルール数 | サイズ | 用途 |
|---|---:|---:|---:|---|
| [`rules/numbers/counters/simple.toml`](rules/numbers/counters/simple.toml) | 80 | 80 | 1.8 KB | 単純サフィックス助数詞 (円 / 点 / 度 / 名 / 話 等、 数値カナ + value 連結のみ) |
| [`rules/numbers/counters/objects.toml`](rules/numbers/counters/objects.toml) | 27 | 62 | 3.9 KB | 物を数える助数詞 (本 / 匹 / 杯 / 個 / 歳 / 冊、 連濁 / 促音化) |
| [`rules/numbers/days.toml`](rules/numbers/days.toml) | 31 | 31 | 978 B | 1〜31 日の特殊読み (1→ツイタチ / 20→ハツカ 等) |
| [`rules/numbers/numeric_phrases.toml`](rules/numbers/numeric_phrases.toml) | 23 | 23 | 893 B | 数字を含む例外語句 (二十歳→ハタチ / 明後日→アサッテ 等、 助数詞ルールより先に確定) |
| [`rules/numbers/scales.toml`](rules/numbers/scales.toml) | 19 | 19 | 1.0 KB | 大数スケール (万 / 億 / 兆 / 京 / 垓 / 不可思議 / 無量大数 等、 大→小順、 N+漢字単位 連結用) |
| [`rules/numbers/counters/time.toml`](rules/numbers/counters/time.toml) | 11 | 15 | 1.5 KB | 時間系助数詞 (月 / 日 / 時 / 分 / 週間 / 回、 4/7/9 の特殊読み + カナ末尾置換) |
| [`rules/numbers/counters/places.toml`](rules/numbers/counters/places.toml) | 4 | 9 | 720 B | 場所を数える助数詞 (階 / ヶ所 / 箇所 / か所、 連濁 / 促音化) |
| [`rules/numbers/counters/percent.toml`](rules/numbers/counters/percent.toml) | 2 | 4 | 408 B | パーセンテージ (% / ％、 1/6/8/0 で促音化 + パーセント) |
| [`rules/numbers/counters/people.toml`](rules/numbers/counters/people.toml) | 1 | 1 | 225 B | 人を数える助数詞 (人、 1=ヒトリ / 2=フタリ の特殊読み) |
| [`rules/numbers/counters/recursive.toml`](rules/numbers/counters/recursive.toml) | 1 | 1 | 202 B | 再帰モード助数詞 (個目 / 階目 等、 既存助数詞解決後に末尾連結) |
| **小計** (10 ファイル) | **199** | **245** | **12 KB** | |

#### テキスト系

単位 / 記号 / ラテン文字 / 後処理 regex — 文字単位の読み解決と最終整形

`rules/text/` — 3 ファイル

| ファイル | エントリ数 | ルール数 | サイズ | 用途 |
|---|---:|---:|---:|---|
| [`rules/text/units.toml`](rules/text/units.toml) | 17 | 17 | 813 B | SI 単位 + 通貨 + % (km / kg / mL / 円 / % 等、 数値 + 単位を 1 chunk で読む。 lookup は case-insensitive) |
| [`rules/text/symbols.toml`](rules/text/symbols.toml) | 10 | 10 | 386 B | 記号 1 文字読み (+ / − / % / ‰ / 〜 / ・ / ※ 等、 chunks/split() の symbols 階層で個別 hit) |
| [`rules/text/postprocess.toml`](rules/text/postprocess.toml) | 2 | 2 | 325 B | 出力後処理 regex (Step 7、 mode 別: hiragana / ruby / tts / romaji の出力直前に適用) |
| **小計** (3 ファイル) | **29** | **29** | **1.5 KB** | |

<!-- AUTO-GENERATED:RULES:END -->

**エントリ数** は top-level (counter 名 / `[[rule]]` surface 数 / `[entries]` key 数)、
**ルール数** は深掘り pattern count (counters の `[[counter."X".rules]]` や context の
`[[rule.match]]` 等の内部配列要素も含む合計)。 counters / context 以外では両者は同値。

## QA カバレッジ

QA は **corpus 回帰** (`tests/corpus/should_read.toml` 等の永続スナップショット) と
**inline test** (隣接 `<name>.test.toml` で file 単位 lock) の 2 階層で組まれる。
両方とも release tar から `--exclude='*.test.toml'` で除外され、 lib runtime memory
にも乗らない (実行時には影響しない、 CI 時のみの assertion)。

- 詳細仕様: [`docs/INLINE_TESTS.md`](docs/INLINE_TESTS.md) (inline) /
  [`tests/corpus/README.md`](tests/corpus/README.md) (corpus)
- corpus 単一 file が大きくなったら同名 dir に分割可能 (`should_read/<topic>.toml` 等を
  再帰 load)
- PR 時の追加方針: 新機能 / bug fix を加えた PR は、 その PR がカバーした case を
  corpus または inline test に **1 件以上** 追加する (PR template でチェック)

<!-- AUTO-GENERATED:QA:BEGIN -->
### Corpus (回帰)

**合計**: should_read 673 ケース / should_not_read_yet 1 ケース / out_of_scope 0 ケース

| バケット | ファイル | ケース数 |
|---|---|---:|
| `should_read` | [`tests/corpus/should_read/extended.toml`](tests/corpus/should_read/extended.toml) | 94 |
|  | [`tests/corpus/should_read/general.toml`](tests/corpus/should_read/general.toml) | 33 |
|  | [`tests/corpus/should_read/regression.toml`](tests/corpus/should_read/regression.toml) | 317 |
|  | [`tests/corpus/should_read/sentences.toml`](tests/corpus/should_read/sentences.toml) | 49 |
|  | [`tests/corpus/should_read/touhou.toml`](tests/corpus/should_read/touhou.toml) | 30 |
|  | [`tests/corpus/should_read.toml`](tests/corpus/should_read.toml) | 150 |
| `should_not_read_yet` | [`tests/corpus/should_not_read_yet.toml`](tests/corpus/should_not_read_yet.toml) | 1 |
| `out_of_scope` | [`tests/corpus/out_of_scope.toml`](tests/corpus/out_of_scope.toml) | 0 |

### Inline test (`*.test.toml`)

**合計**: 1 ファイル / 7 ケース

| テストファイル | 対象本体 | ケース数 |
|---|---|---:|
| [`rules/numbers/counters/objects.test.toml`](rules/numbers/counters/objects.test.toml) | [`rules/numbers/counters/objects.toml`](rules/numbers/counters/objects.toml) | 7 |
<!-- AUTO-GENERATED:QA:END -->

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
- **熟語 (jukugo)** は genre 別ディレクトリで分類管理 (件数は上の `core/` テーブル参照)
- **作品造語 (works)** は `core/works/<medium>/<title>.toml` 形式で 1 作品 1 ファイル運用。
  公式読み原則 (詳細は [`core/works/README.md`](core/works/README.md))
- **現代の私人 / 私企業 / 商標** は seed していない (誤読リスク回避方針)。
  公式読みが定まっていれば PR 単位で個別判断

→ 体感では「**著名な漢字熟語 / 単漢字 / 古典 / 学術 / 自然物 / 公式読みのある作品は読める、
現代私人 / 商標 / 私企業は手薄**」。 PR 大歓迎。

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
