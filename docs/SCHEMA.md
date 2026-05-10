# TOML スキーマ詳細

`ja-furigana-dict` の各 TOML ファイルの詳細スキーマ。

> 戻る: [CONTRIBUTING.md](../CONTRIBUTING.md) (クイックパス)
> 関連: [INLINE_TESTS.md](./INLINE_TESTS.md) (`*.test.toml` の規約)

カテゴリ別のファイル一覧 / 件数 / サイズは [STATS.md](../STATS.md) で auto-gen される。
本書は **TOML スキーマと書き方の reference**。

## 共通: `[meta]` block

すべての TOML ファイルは冒頭に `[meta]` block を置く:

```toml
[meta]
schema_version = "2"   # 必須 (alpha.10〜、 ★A1b)、 lib が format version を判定
role = "jukugo"        # role tag (lib loader が dispatch に使う)
description = "二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む)"
```

- `schema_version`: **必須** (alpha.10〜、 lib が `[meta] schema_version = "2"`
  で受け入れ判定)。 不在 / `"1"` 等は明確 Validation error で reject。 旧
  alpha era format dict は `tools/migrate_v2.py` で stamp 適用要。
- `role`: `jukugo` / `unihan` / `works` / `loanwords` / `single_overrides` / `compat`
  / `counters` / `context` / `postprocess` / `days` / `scales` / `units`
  / `symbols` / `latin` / `numeric_phrases`
  - `[meta] role` 無しでも path-based fallback で動作 (旧 release 互換)
- `description`: 1 行説明、 `tools/regen_stats.py` が STATS.md の用途列に取り込む

## 共通: `[entries]` block

熟語 / 単漢字 / 外来語 / works / numeric_phrases / days / symbols / latin の各 file
は `[entries]` 配下に key = value で書く (基本形):

```toml
[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
```

ルール (全 entry に共通):

- key (表層) と value (読み) は **ダブルクォート** で囲む
- value は **ひらがな または 全角カタカナ** (半角カナ / ローマ字は不可)
  - 慣習: 訓読み = ひらがな / 音読み = カタカナ
  - lib 側で出力時に正規化されるので、 どちらで書いても挙動は同じ
- 1 ファイル内で同じ key を 2 重登録しない (TOML パーサがエラー)

### detailed entry (= inline match block 持ち、 ★A2 alpha.11〜)

文脈分岐 reading が要る surface (例: 「上手」 = ジョウズ / カミテ) は **detailed
form** で書ける。 同 file 内で simple form と detailed form は混在 OK:

```toml
[entries]
"灰桜" = "ハイザクラ"     # simple form (= 99% の entry はこのまま)

# detailed form: expanded sub-table
[entries."上手"]
reading = "ジョウズ"        # default reading (必須)、 全 match miss 時の fallback

[[entries."上手".match]]
next_eq = "から"            # matcher 条件 (= 直後 token surface 完全一致)
reading = "カミテ"          # 条件 hit 時の reading (必須)

[[entries."上手".match]]
prev_eq = "下"
reading = "シタテ"
```

または **inline form** で 1 行に書く (= match block 数が少ない時に推奨):

```toml
[entries]
"上手" = { reading = "ジョウズ", match = [
  { next_eq = "から", reading = "カミテ" },
  { prev_eq = "下", reading = "シタテ" },
] }
```

### detailed entry の matcher vocabulary (★A2、 alpha.11)

`[[entries."x".match]]` block 内で使える matcher 条件:

| 軸 | prev (直前 token) | next (直後 token) | next2 (直後の更に直後) | 値型 |
|---|---|---|---|---|
| literal 完全一致 | `prev_eq` | `next_eq` | — | string |
| literal いずれか | `prev_eq_any` | `next_eq_any` | — | string array |
| literal 末尾一致 | `prev_ends_any` | — | — | string array |
| literal 先頭一致 | — | `next_starts` | — | string |
| literal 先頭いずれか | — | `next_starts_any` | `next2_starts_any` | string array |
| 文字種 | `prev_char_type` | `next_char_type` | — | "漢字" / "ひらがな" / "カタカナ" / "英数" / "記号" |
| 述語 | `prev_month` | `next_digit` | — | bool |

**意味**:

- 同 `[[match]]` block 内の condition は **AND** (= 全 hit で match 成立)
- 複数 `[[match]]` block は TOML 出現順で **第一 hit 採用** (= OR ordered)
- 全 match miss なら entry の `reading` (= default) 採用
- `prev_month`: 直前 token surface が `一月`〜`十二月` / `1月`〜`12月` / 全角数字
  含む 月名で終わるか (= lib 内蔵 list、 dict 側で記述不要)
- `next_digit`: 直後 token surface が半角 / 全角数字で始まるか (= lib 内蔵 list)

**Lindera 品詞 matcher (`pos`) は不採用** (Lindera 撤廃路線)、 「名詞の後 / 動詞の後」
のような汎用条件は `prev_eq_any = ["階段", "段", "梯子"]` 等の literal 列挙で代用。

### intonation bracket notation (forward compat、 0.2.0 で activate)

reading 内に `[` / `]` / `/` の bracket marker を **0.1.0 から書ける** (= forward
compat、 lib alpha.10〜 0.1.0 stable で reading から strip して無視、 0.2.0 で
accent annotation として activate):

```toml
[entries]
"上手" = "ジョ]ウズ"         # 1型 accent (頭高、 ジョが高くウで下降)
"霧雨" = "キ[リサメ"         # 0型 (平板、 キが低くリで上昇後そのまま)
"桜" = "サ[ク]ラ"            # 中高 (サが低くクで上昇、 ラで下降)
"心" = "コ[コロ]"            # 尾高 (末尾モーラで下降)

[entries."紅魔館"]
reading = "コ[ウマカン]"     # detailed entry の reading にも書ける

[[entries."紅魔館".match]]
prev_eq = "東方"
reading = "ハ[クレイ/レ[イム"  # 複数 phrase は `/` で区切る (= 2 phrase)
```

**書き方 rule** (`tools/validate.py` で CI check):

- `[`: phrase 開始 (= rise marker)、 各 phrase 内 最大 1 個
- `]`: accent peak (= fall marker、 直後で 1 段下がる)、 各 phrase 内 最大 1 個
- `[` と `]` 両方ある場合は `[` が `]` より前 (= 順序強制)
- `/`: phrase 区切り、 連続 `//` / 先頭 `/` / 末尾 `/` 不可 (= 空 phrase 禁止)
- bracket 文字を除いた reading 部分は通常通り **ひらがな または 全角カタカナ** のみ

詳細仕様: lib 側 [`docs/PROPOSALS/intonation.md`](https://github.com/RyuuNeko1107/ja-furigana/blob/master/docs/PROPOSALS/intonation.md)。

**例外 layout** (file 単位で異なる、 各 file 別 section 参照):

- `units.toml`: `[entries]` 内の value が inline-table (`{ kana = "...", ci = true }`)
- `scales.toml`: `[[entry]]` array of tables (`kanji = X / kana = Y` の pair)
- `compat.toml`: `[map]` dict (異体字 → 標準字 の正規化マップ)
- `counters/*.toml`: `[counter."X"]` table + `[[counter."X".rules]]` array
- `context/*.toml` / `postprocess.toml`: `[[rule]]` array of tables

## array marker 規約

TOML の array of tables (`[[counter."X".rules]]` / `[[rule]]` / `[[rule.match]]`)
は 1 つの logical block (= 1 個の counter / 1 個の context rule) が複数 table に
分散する。 これを視覚的に / programmatic に拾えるよう、 各 block を
**`# === begin: <名前> ===` / `# === end: <名前> ===`** で囲む規約を採用している。

```toml
# === begin: 本 ===
[counter."本"]
default = "ホン"

[[counter."本".rules]]
last_digit = [1, 6, 8, 0]
suffix = "ポン"
sokuonize = true

[[counter."本".rules]]
last_digit = [3]
suffix = "ボン"
# === end: 本 ===
```

**適用先**:
- `rules/numbers/counters/{objects,places,percent,time}.toml` — 各 counter (`本` / `匹` 等)
- `rules/context/{homonyms,numbers,special}.toml` — 各 `[[rule]]` (surface 単位)

**適用しない**:
- `rules/numbers/counters/{simple,people,recursive}.toml` — single-table / flat 構造で
  block 概念が無いため
- `rules/numbers/days.toml` 等の `[entries]` 単一 table file

`<名前>` には counter 名 (例: `本`) または `[[rule]]` の `surface` 値 (例: `上手`) を
そのまま入れる。 file 内で重複しなければ良い。

**Why**: TOML 仕様には「array of tables の論理的 block の終わり」 を明示する構文が
ないため、 慣行コメントで補う。 PR diff レビュー時に block 範囲が一目で分かる /
将来 tooling (例: 「rule 本 の定義部分だけ抽出」) を書く時の anchor になる。

## 共通の採録ポリシー

すべての jukugo / works 共通の採録方針:

- **古典的読みは現代読みが無い場合のみ** — 現代口頭 (TTS 用途) を想定するため、
  現代でも読まれる surface に古典読みを default にすると現代の利用者が聞き取れない /
  読めない。 古典作品の固有名詞等、 現代の定着読みが存在しない場合に限り古典定本ベース
- **同 surface 異 reading の競合時は一般的な読みを優先** — works / specialized 等で
  特殊文脈読みを採録しても、 一般文脈で同じ surface が出てくる場合、 一般読みを残す
  方針 (自動振り分けはしないが、 maintainer review で判断)。 例: 作品固有の特殊読み
  「○○ → ××」 が一般語 「○○ → △△」 と衝突した場合、 一般読み △△ を維持し、
  作品 file 側は削除 or 残置 (lib 側 merge は genre sort 順で works が後なので、
  works 残置 + 同 entry 重複時は works が後勝ちで採用される点に注意)

## ファイル別: `core/_inbox.toml` — 分類前の一時 inbox

```toml
[meta]
role = "jukugo"
description = "分類前の一時 inbox (≥2 字 surface、 内容が貯まったら適切な genre dir に振り分ける)"

[entries]
```

「読みは追加したいが、 どの genre dir (basic / nature / society / 等) に入れるべきか
判断付かない」 ときに 1 行追加してここに置く。 lib 側は `[meta] role = "jukugo"` で
jukugo として load される (≥2 字 surface 限定)。 maintainer の整理タイミングで
適切な `core/jukugo/<genre>/<file>.toml` に移動する。

**入れない**:
- 単漢字 (1 字 surface) → `core/unihan/<水準>.toml`
- 外来語 (英字始まり surface) → `core/loanwords/`

## ファイル別: `core/jukugo/` — 一般熟語 + 固有名詞

ジャンル別に複数の dir + 多数の file に細分化されている (basic / humanities /
nature / objects / proper / society 等)。 最新の dir 構成 / file 数 / 件数 は
[STATS.md](../STATS.md) (各 TOML の `[meta] description` から自動生成) を参照。

代表カテゴリ:

| ファイル | 用途 | 例 |
|---|---|---|
| `general.toml` | 二字 / 三字の一般熟語 + 季節 / 行事 / 慣用句 | 灰桜 / 黎明 / 立春 / お盆 |
| `four_char.toml` | 四字熟語 (4 字 + 全部 CJK 漢字) | 一期一会 / 四面楚歌 / 一目瞭然 |
| `proper_nouns.toml` | 大学・中央官庁・元号・歴史的事象 | 早稲田大学 / 文部科学省 / 令和 |
| `place_names.toml` | 国・都道府県・駅・寺社仏閣・観光地 | 北海道 / 京都駅 / 東大寺 / 富士山 |
| `personal_names.toml` | 姓・名・著名人 (古典・歴史中心) | 紫式部 / 夏目漱石 / 渡邊 |
| `animals.toml` / `foods.toml` / `weather.toml` / `colors.toml` | 自然・物質系 | 蝙蝠 / 餃子 / 時雨 / 茜色 |
| `specialized.toml` | 専門用語 (医学 / 軍事 / 法学 / 経済 / IT) | 蕁麻疹 / 駆逐艦 / 量子力学 |
| `body_parts.toml` | 体の部位 / 内臓 / 骨格 / 筋肉 / 神経 | 鳩尾 / 副腎 / 三角筋 |
| `arts.toml` / `music.toml` | 古典芸能 / 武道 / 茶華香 / 工芸 / 楽典 | 三味線 / 歌舞伎 / 撥弦楽器 |
| `architecture.toml` / `vehicles.toml` / `clothes.toml` | 建築 / 乗物 / 衣服 | 天守 / 連絡船 / 狩衣 |
| `literature.toml` / `abstracts.toml` / `idioms.toml` | 古典文学 / 美意識 / 慣用句 | 太平記 / 物の哀れ / 蛇足 |
| `science.toml` | 自然科学 (天文 / 物理 / 化学 / 生物 / 地学) | 突然変異 / 円周率 / 鍾乳洞 |
| `emotions.toml` / `religions.toml` / `politics.toml` / `sports.toml` | 心理 / 宗教 / 政治 / 近代スポーツ | 戦慄 / 修験道 / 公示 / 競歩 |

例 (`core/jukugo/basic/general.toml`):

```toml
[meta]
role = "jukugo"
description = "二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む)"

[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
"曙光" = "ショコウ"
```

判断に迷う場合は `general.toml` でも構わない (review で振り分け可能)。

**制約**:
- **単漢字 (1 字 surface) は jukugo に絶対追加しない** — `core/unihan/` 専用領域、
  混入すると `validate.py` が cross-file 重複として CI を fail させる
- **異体字 (compat の key 側) を jukugo に追加しない** — Step 1 で標準字に正規化
  されるため dead 経路、 master push 時に `dedup_compat.py` が自動削除する

### 人物名の登録方針 (`personal_names.toml`)

人物名は形態素解析で苗字 / 名前 単独 token に分割される場合と、 フルネームで 1 token
として認識される場合の両方が起きる。 どの形でも正しく読まれるよう、
**苗字 / 名前 / フルネーム の 3 通り登録を推奨**:

```toml
[entries]
"夏目"     = "ナツメ"        # 苗字単独
"漱石"     = "ソウセキ"      # 名前単独
"夏目漱石" = "ナツメソウセキ" # フルネーム (formal な並び)
```

理由:
- フルネームだけ登録 → 「夏目」 が単独で出てくる文 (例: 「夏目先生」) で hit しない
- 苗字 / 名前だけ登録 → フルネームが Lindera で 2 token に分割される時に jukugo
  prefix-match が hit しなくて IPADIC の推測読みになり、 結果的に苗字 / 名前単独で
  hit するが連続感が無い読みになる (「ナツメ ソウセキ」)
- 3 通りあると: フルネーム文 → ≥3 字 jukugo prefix-match で 1 chunk 確定、
  苗字単独 → 苗字 entry hit、 名前単独 → 名前 entry hit、 すべての形を網羅

例外: 苗字 / 名前 単体が **一般語と衝突して誤読を引き起こす** 場合は、 衝突する側の
登録を控える (例: 「桜」 という名前を `personal_names.toml` に入れると一般語
「桜 = サクラ」 を override してしまう)。 フルネーム側だけ残す判断もあり。

## ファイル別: `core/works/` — 作品単位辞書

特定の作品 (アニメ / ゲーム / 漫画 等) の固有名詞・造語を **1 作品 = 1 ファイル**
で集める専用ディレクトリ。 loader が全階層再帰でスキャンするため、
`core/works/<medium>/<title>.toml` の構造で配置する (例: `core/works/game/touhou.toml`)。

**追加要件 (jukugo より厳しい)**:
- **原則は公式読み**。 ファン推測 / 同人解釈 / 派生作品の独自設定は **非推奨**
  (広く一般的な通称として定着している場合のみ採録可)
- ファイル先頭に **出典 URL** を comment で必須記載
- **古典的読みは現代読みが無い場合のみ** (TTS = 現代口頭用途を想定)
- 商標的にグレーなコラボ商品名 / 二次商標は入れない
- **同 surface が `core/jukugo/*` に既存する場合は一般読みを優先** (works 側削除 or
  残置 + 説明 comment、 詳細は上の「共通の採録ポリシー」)

詳細サブポリシーは [`core/works/README.md`](../core/works/README.md) を参照。

## ファイル別: `core/loanwords/` — 外来語 (英字 surface)

ASCII / 全角英字始まりの surface に対するカタカナヨミを置く専用ディレクトリ。
ja-furigana 側 chunks 階層 4.7 で **完全一致 lookup** (case-fold + 全角→半角) で参照される。
カテゴリ細分化を許容するサブディレクトリ構造 (例: `core/loanwords/it.toml`)。

```toml
[meta]
role = "loanwords"
description = "IT 用語 / プログラミング言語 / OSS / クラウドサービス / 技術企業"

[entries]
"Anthropic" = "アンソロピック"
"Kubernetes" = "クバネティス"
"PostgreSQL" = "ポストグレスキューエル"
```

**重要な制約 (jukugo と異なる)**:
- surface は **ASCII / 全角英字始まり** + 英数字 + 記号 (`+ # . - _`) のみ
- `validate.py::LOANWORD_SURFACE_RE` で形式チェック (CI で fail)
- reading は カタカナ表記 (lib 側で出力時にひらがな化されないので、 そのままカタカナで残る)
- substring 切断ゼロ なので「Post」 entry を作っても「PostgreSQL」 chunk には部分 hit しない
- canonical form (大文字始まり) で書く ーー 入力側のブレ (大小 / 全角) は lib 側で正規化される

**NG**:
- 「.NET」 「@types/node」 のような **記号始まり** surface (regex に match しない)
- 短すぎる ASCII (例: 「IT」 「OS」) は誤マッチを起こしやすいので慎重に検討

## ファイル別: `rules/numbers/counters/` — 助数詞ルール

サブディレクトリ内の `*.toml` 全てが自動 merge される。 ファイル名は何でも構わない。

| ファイル | 範囲 |
|---|---|
| `simple.toml` | 単純サフィックス助数詞 (`[simple]`) |
| `time.toml` | 月 / 日 / 時 / 分 / 分半 / 週間 / 回 |
| `people.toml` | 人 |
| `objects.toml` | 本 / 匹 / 杯 / 個 / 歳 / 冊 |
| `places.toml` | 階 / ヶ所 / 箇所 / か所 |
| `percent.toml` | % / ％ |
| `recursive.toml` | 目 (再帰モード) |

### 連濁 / 促音化を持つ助数詞 (例: 「本」 / 「匹」)

```toml
# === begin: 本 ===
[counter."本"]
default = "ホン"             # どの rule にも当てはまらない数値で使う読み

[[counter."本".rules]]
last_digit = [1, 6, 8, 0]    # 1 / 6 / 8 / 10 / 100 等で
suffix = "ポン"              # 「ポン」 (1 本 = イッポン)
sokuonize = true             # 直前数値末尾を促音化 (1 → イッ、 6 → ロッ、 8 → ハッ、 10 → ジッ)

[[counter."本".rules]]
last_digit = [3]             # 3 で
suffix = "ボン"              # 「ボン」 (3 本 = サンボン、 連濁のみ)
# === end: 本 ===
```

書きどころ:

- counter 名 (`"本"`) は同 file 内で 3 回登場 (`[counter."本"]` + 2 つの `[[counter."本".rules]]`)
- `last_digit` は **末尾 1 桁** で match (例: `100 → 0`、 `13 → 3`)
- `sokuonize = true` は「促音化」 (直前数字の末尾を ッ に)、 `false` (or 省略) は連濁のみ
- 連濁も促音化も無い助数詞は `default` だけ書く (rules 不要)

```toml
[counter."回"]
default = "カイ"             # 1 回 = イチカイ、 3 回 = サンカイ、 連濁なし
```

### kana 末尾置換 (例: 「分」 ジュウフン → ジップン)

```toml
[counter."分"]
default = "フン"

[[counter."分".rules]]
last_digit = [1, 3, 4, 6, 8, 0]
suffix = "プン"
sokuonize = true
kana_replace = { "ジュウ" = "ジッ" }   # 「ジュウフン」 → 「ジップン」
```

`kana_replace` は数値 surface 側の kana を rule マッチ時に置き換える (限定的、 必要時のみ)。

## ファイル別: `rules/context/` — 文脈依存読み (alpha.11 で entry inline match に migration 中)

> **migration status** (★A2、 alpha.11): 本 dir の `[[rule]]` 形式は 0.1.0 stable cut
> までに **廃止** 予定。 各 surface の文脈分岐 reading は対応 entry の **inline
> `[[entries."x".match]]` に移植**される (= [`[entries]` block の detailed entry](#detailed-entry--inline-match-block-持ち-a2-alpha11) 参照)。
>
> alpha.11 期間中は **両形式が duplicate 共存** (= `tools/migrate_v2_context.py`
> で staging 出力 + `tools/merge_migrated_context.py` で実 core/ に merge 済、
> rules/context/*.toml は Strict engine 後方互換のため残置)。 0.1.0-rc1 で Smart
> engine が default 切替後、 本 dir 削除可能。
>
> **新規 PR のときは entry inline form 推奨** (= rules/context/ には追記しない)、
> 既存 rule の修正は 「rules/context/ 修正 + 対応 entry inline match 修正」 を
> 同時に PR で。

| ファイル | 範囲 |
|---|---|
| `numbers.toml` | 数字を含む慣用語句 (一日 / 一人 / 一月 / 一杯 等) |
| `homonyms.toml` | 同形異音語 (上手 / 下手 / 人気 / 大人気 / 十分) |
| `special.toml` | 単純な読み固定 (大人 / 仲人 / 今日 / 何日 / 日本 等) |

### 書き方

各ルールは「surface (対象表層) + match (条件 → 読み) のリスト + default (任意の fallback)」。
各 `[[rule]]` block は array marker で囲む:

```toml
# === begin: 一日 ===
[[rule]]
surface = "一日"
default = "イチニチ"          # どの match にも当てはまらないときの読み (任意)

[[rule.match]]
prev_ends_with_month = true   # 前トークンが「1月」「12月」等で終わるなら…
reading = "ツイタチ"          # 「ツイタチ」と読む
# === end: 一日 ===
```

match は **上から順に評価** され、最初にマッチしたものが採用される。
1 つの match 内で複数条件を書くと **AND 条件**。

### 使える条件一覧

**前のトークン (prev) を見る**

| 条件 | 意味 |
|---|---|
| `prev_eq = "X"` | 前のトークンが完全に `"X"` |
| `prev_ends_with_any = ["X", "Y"]` | 前のトークンの末尾が X か Y |
| `prev_ends_with_month = true` | 前のトークンが「1月」〜「12月」 |

**後のトークン (next) を見る**

| 条件 | 意味 |
|---|---|
| `next_eq = "X"` | 次のトークンが完全に `"X"` |
| `next_starts_with = "X"` | 次のトークンが `"X"` で始まる |
| `next_starts_with_any = ["X", "Y"]` | 次のトークンが X か Y で始まる |
| `next_starts_with_digit = true` | 次のトークンが数字で始まる |

**2 つ後のトークン (next-next) を見る**

| 条件 | 意味 |
|---|---|
| `next_next_starts_with_any = ["X", "Y"]` | 2 つ後が X か Y で始まる |

**形態素解析の品詞 (pos) を見る** (★A2、 alpha.11 以降 deprecated)

| 条件 | 意味 |
|---|---|
| `pos_eq = "X"` | 当該トークンの品詞が完全に X (例: `"名詞"` / `"形容詞"`) |

> **deprecated**: Lindera 撤廃路線 (= 1.0+ vision で形態素解析依存削除) に伴い、
> 0.1.0 stable 以降は `pos_eq` を採用しない。 「名詞 / 形容詞 のとき」 のような
> 汎用条件は **literal 列挙** で代用 (例: `prev_eq_any = ["階段", "段", "梯子"]`)。
> 既存 rules/context/ の `pos_eq` 行は alpha.11 期間中は受け付けるが、 新規 PR
> での pos_eq 追加は基本却下。

> **migration name mapping** (★A2、 alpha.11): rules/context/ の旧 matcher 名 →
> entry inline match の新 matcher 名:
> - `prev_ends_with_any = [...]` → `prev_ends_any = [...]`
> - `prev_ends_with_month = true` → `prev_month = true`
> - `next_starts_with = "X"` → `next_starts = "X"`
> - `next_starts_with_any = [...]` → `next_starts_any = [...]` (同名)
> - `next_starts_with_digit = true` → `next_digit = true`
> - `next_next_starts_with_any = [...]` → `next2_starts_any = [...]`
> - `pos_eq = "X"` → **削除** (= literal 列挙で代用)

> ヒント: 既存の `numbers.toml` / `homonyms.toml` / `special.toml` をテンプレ
> としてコピーするのが早道。 新ルール PR では **どのテキストでどう変わるか** を
> 1-2 例書いてくれると review が楽。

### triple-quoted string で string list を受ける

`prev_ends` / `next_starts_any` / `next2_starts` 系の field は array (`["a", "b"]`)
に加えて triple-quoted string (`"""\na\nb\n"""`) でも書ける。 後者は newline split
+ trim + 空行 filter で `Vec<String>` に変換される。

```toml
[[rule.match]]
next_starts_any = """
な
無
"""
reading = "ヒトケ"
```

**目的**: 多行 array で各行末に `,` を付ける friction を削減 + merge conflict 耐性
向上 (1 行 1 entry)。 旧形式 (TOML array) は引き続きサポート。

### 典型 pattern 例集

```toml
# (a) 単純な default 固定 (どの文脈でも同じ読み、 unihan を override したい時)
[[rule]]
surface = "大人"
default = "オトナ"           # default だけ書けば全文脈で「オトナ」

# (b) 直前 / 直後トークンで分岐
[[rule]]
surface = "上手"
default = "ウワテ"           # default は 棋士・芸事系
[[rule.match]]
prev_ends_with_any = ["お"]
reading = "ジョウズ"          # 「お上手」 のみ ジョウズ
[[rule.match]]
next_starts_with_any = ["な", "に", "の", "を", "が"]
pos_eq = "形容詞"
reading = "ジョウズ"          # 形容詞用法も ジョウズ

# (c) 数値 + 助数詞風の文脈分岐 (一日 → 月名後ならツイタチ)
[[rule]]
surface = "一日"
default = "イチニチ"
[[rule.match]]
prev_ends_with_month = true   # 「6 月」 「12 月」 等の後
reading = "ツイタチ"

# (d) 2 つ後のトークンを見る (「人気 が 無い」 vs 「人気 が ある」)
[[rule]]
surface = "人気"
default = "ニンキ"
[[rule.match]]
next_eq = "が"
next_next_starts_with_any = ["な", "無"]
reading = "ヒトケ"            # 「人気が無い」 = ヒトケ ガ ナイ
```

evaluate 順は **上から順**、 最初に match した reading が採用される。 `default` を
書かない場合は context rule 自体を skip して通常 pipeline (jukugo / Lindera /
unihan fallback) に流れる。

## ファイル別: `core/unihan/*.toml` — 単漢字フォールバック (水準別)

漢字 1 文字 → カタカナ or ひらがな。 形態素解析でも辞書でもヒットしない単漢字の最終フォールバック。
**水準別に分割** されており (利用頻度の高い常用漢字に review を集中させるため)、
具体的な file 名 / 件数は [STATS.md](../STATS.md) を参照。

```toml
[entries]
"鬱" = "ウツ"
"曰" = "イワク"
```

> 単漢字は文脈で読みが変わるため、**最も一般的な音/訓読み 1 つ** を採用。
> 文脈依存が必要な場合は [`rules/context/`](../rules/context/) で扱う。
> Lindera reading より優先したい単漢字は
> [`core/single_overrides.toml`](../core/single_overrides.toml) で個別 override
> ([issue #15](https://github.com/RyuuNeko1107/ja-furigana/issues/15) の限定解、 1 字 surface のみ)。

## ファイル別: `core/compat.toml` — 異体字 → 標準字

「髙→高」のように、字形が違うが同じ漢字として扱いたい異体字の正規化マップ。
エンジン側に他の compat 表は無いので、ここが正典 (上乗せではなく単独の出典)。

```toml
[map]
"瀧" = "滝"
"靑" = "青"
```

## ファイル別: `rules/text/postprocess.toml` — 後処理 regex (Step 7)

`Furigana::to_{hiragana,ruby,tts,romaji}` の **出力直前** に適用される regex 置換ルール。
辞書 / context rule で表現しづらい文字列レベルの最終調整用 (例: 促音化補正、mode 別の整形)。

```toml
[[rule]]
pattern = "ジュウパー"             # regex (Rust の regex crate 構文)
replacement = "ジュッパー"          # $1, $2 で capture group 参照可
modes = ["hiragana", "tts"]      # 適用 mode (空 = 全 mode)

[[rule]]
pattern = "(\\d+)\\s*ヶ"
replacement = "$1カ"
modes = []                       # 空 = 全 mode に適用
```

**書くとき注意**:

- pattern は Rust `regex` クレートの構文。POSIX 風 + `(?P<name>...)` 名前付きキャプチャ可
- replacement で `$0` は全マッチ、`$1`〜`$N` は順番のキャプチャ
- modes に書ける値: `"hiragana"` / `"ruby"` / `"tts"` / `"romaji"` (or 空 = 全 mode)
- **`ruby` mode は出力に `{漢字|読み}` 構造を含む** ので、`{` `|` `}` を壊さない
  pattern にすること。 心配なら modes に `"ruby"` を入れない
- 起動時に regex を pre-compile するため、不正な pattern は loader 段で fail
- regex 圧縮 size は 10 MB で cap (regex bomb 防御)、 通常 pattern は数百 byte なので問題なし

### よくあるパターン例集

```toml
# (1) 単純な置換 (全 mode 共通)
[[rule]]
pattern = "ジュウパー"
replacement = "ジュッパー"
modes = []

# (2) capture group で一部を残す
[[rule]]
pattern = "(\\d+)\\s*ヶ"               # 数字 + 任意の空白 + ヶ
replacement = "$1カ"                   # 数字を保持して 「ヶ」 → 「カ」
modes = []

# (3) hiragana mode 限定
[[rule]]
pattern = "ぱーせんと"
replacement = "パーセント"
modes = ["hiragana"]

# (4) tts mode で句読点直後の半角スペース除去 (発話時の不自然な間を抑制)
[[rule]]
pattern = "([、。!?])\\s+"
replacement = "$1"
modes = ["tts"]

# (5) 名前付きキャプチャ (可読性アップ)
[[rule]]
pattern = "(?P<num>\\d+)度"
replacement = "${num}ド"
modes = []
```

PR で追加するときは、**該当する例文** (before / after) を comment or PR description に
書いてくれると review しやすい。

## ファイル別: `rules/numbers/numeric_phrases.toml` — 数字を含む例外語句

通常の数値 + 助数詞ロジックでは扱えない、 慣用的な読み (二十歳=ハタチ、 八十=ヤソ 等):

```toml
[entries]
"二十歳" = "ハタチ"
"八十"   = "ヤソ"
"百個"   = "ヒャッコ"        # counter 連濁を超えた特殊読み
"千個"   = "センコ"
```

`[entries]` table に key=value 形式で書くだけ。 数字を含む surface (or 慣用語句的に
固定読みされるもの) を ad-hoc に上書きする領域。

## ファイル別: `rules/numbers/days.toml` — 1〜31 日の特殊読み

```toml
[meta]
role = "days"
description = "1〜31 日の特殊読み (1→ツイタチ 等)"

[entries]
"1"  = "ツイタチ"
"2"  = "フツカ"
"3"  = "ミッカ"
"4"  = "ヨッカ"
"10" = "トオカ"
"14" = "ジュウヨッカ"
"20" = "ハツカ"
"24" = "ニジュウヨッカ"
# ... 他は default (ニチ) 適用
```

数字 (1〜31) → 特殊読み の単純 mapping。 「N 日」 文脈でのみ参照される
(= 通常の数値文脈には影響なし)。

旧形式 (top-level に entries 直書き) も引き続き受け入れる (互換)。 新規 PR は
`[entries]` block 形式で書く。

## ファイル別: `rules/numbers/scales.toml` — 大数 (万 / 億 / 兆 / 京 ...)

`[[entry]]` array of tables で `kanji` / `kana` を pair で書く (大→小 順、 lib 側は
この順序を尊重して大きい単位から処理):

```toml
[[entry]]
kanji = "無量大数"
kana = "ムリョウタイスウ"

[[entry]]
kanji = "万"
kana = "マン"

[[entry]]
kanji = "億"
kana = "オク"
```

scale + 漢字単位 1 文字 (「1 万円」「3 億ドル」) を 1 chunk として処理する基盤。

## ファイル別: `rules/text/units.toml` — SI 単位 + 通貨 + %

`[entries]` 配下に key = inline-table (`{ kana = "..." }`) で書く。 必要に応じて
`ci = true` を付けると case-insensitive lookup になる:

```toml
[entries]
"km" = { kana = "キロメートル" }
"kg" = { kana = "キログラム" }
"mL" = { kana = "ミリリットル", ci = true }
"円" = { kana = "エン" }
"%"  = { kana = "パーセント" }
```

数値 + 単位 を 1 chunk で読む (「3 km」「100 円」)。 lookup は default で
case-insensitive (大文字小文字を区別しない)、 個別 entry で `ci = false` 等の opt-out 可。

## ファイル別: `rules/text/symbols.toml` / `rules/text/latin.toml`

```toml
# symbols.toml
[entries]
"+" = "プラス"
"−" = "マイナス"
"%" = "パーセント"
"〜" = "から"             # 「3〜5 個」 のような表現

# latin.toml
[entries]
"A" = "エー"
"B" = "ビー"
"C" = "シー"
```

単一文字 → 読み の単純 mapping (`[entries]` flat 文字列形式)。
chunks/split() で個別文字 chunk として hit する。

## レビュー方針

「正しい読み」 vs 「自然な読み」で意見が割れた場合は、**TTS 読み上げで
実用上自然な方** を採用する。
