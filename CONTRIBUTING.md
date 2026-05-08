# Contributing to furigana-dict

語彙辞書の追加・修正は **TOML を 1 行追加するだけ** で完結する。
Rust 知識・Git クローン不要。

## クイックパス: GitHub Web UI で 1 件追加

1. 該当ファイルを開く:
   - **熟語 (≥ 2 字 surface)** → [`core/jukugo/<genre>/<file>.toml`](core/jukugo/)
     (ジャンル別 dir 階層、 [STATS.md の「熟語」 section](STATS.md#熟語) で
     どの dir に何があるかを確認)
   - **単漢字 (1 字 surface)** → [`core/unihan/<水準>.toml`](core/unihan/)
     (5 水準別 file、 [STATS.md の「単漢字」 section](STATS.md#単漢字) 参照)
   - **異体字 → 標準字** → [`core/compat.toml`](core/compat.toml)
   - **単漢字 default override** ([issue #15](https://github.com/RyuuNeko1107/ja-furigana/issues/15) 限定解) → [`core/single_overrides.toml`](core/single_overrides.toml)
   - **外来語 (英字始まり surface)** → [`core/loanwords/`](core/loanwords/)
   - **作品造語 (作品単位 1 ファイル)** → [`core/works/<medium>/<title>.toml`](core/works/)

   どの genre / 水準にどの file があるかの最新一覧は [STATS.md](STATS.md) を参照
   (master push 後 CI で auto-regen される)。
2. 右上の鉛筆アイコン (Edit) をクリック
3. `[entries]` セクションに 1 行追加:
   ```toml
   "新しい表層" = "シンシイヒョウソウ"
   ```
4. ページ下部の「Commit changes」→ ブランチ自動生成 → PR 作成

## ローカル編集 (複数件・差分大きめ)

```sh
git clone https://github.com/RyuuNeko1107/ja-furigana-dict
cd furigana-dict
# core/*.toml を編集
git checkout -b add-readings
git commit -am "add: 灰桜/黎明 等"
gh pr create
```

## TOML 形式の注意点

### 必須

- ファイル冒頭に `[meta] description = "..."` を書く (1 行説明、`tools/regen_stats.py` が STATS.md の用途列に取り込む)
- 各エントリは `[entries]` テーブル配下に書く
- key (表層) と value (読み) は **ダブルクォート** で囲む: `"灰桜" = "ハイザクラ"`
- value は **ひらがな または 全角カタカナ** (半角カナ・ローマ字は不可)
  - 慣習的に **訓読み = ひらがな / 音読み = カタカナ** で書き分ける (例: `"桜" = "さくら"` / `"音" = "オン"`)
  - エンジン側で出力時に正規化されるため、どちらで書いても挙動は同じ
- 1 ファイル内で同じ key を二重登録しない (TOML パーサがエラーを吐く)
- **単漢字 (1 文字 surface) は jukugo / works に絶対追加しない** — `core/unihan/<水準>.toml` 専用領域、混入すると validate.py が cross-file 重複として CI を fail させる
- **異体字 (compat の key 側) を jukugo / works / unihan に追加しない** — lib の Step 1 で標準字に正規化されるため dead 経路、 master push 時に CI の `dedup_compat.py` が自動削除する

最小例:

```toml
[meta]
description = "二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む)"

[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
```

### 推奨

- ファイル内のエントリは **50 音順** で並べる (PR diff が読みやすくなる)
- 大量追加するときは:
  - 同じ PR に **同じ分野 (人名 / 地名 / 一般語)** をまとめる
  - 1 PR あたり ~50 件程度を目安に分割すると review が楽
- `STATS.md` の更新は不要 — master に push されると GitHub Actions が自動で再生成 + auto-commit する (`.github/workflows/regen-stats.yml`)

### NG

- 商標・固有名詞のうち **公的に認知されていない読み** (誤読をデフォルト化しない)
- 文脈で読みが変わる語の片方だけを `core/jukugo/*` の default にする (それは [`rules/context/`](rules/context) 配下の文脈ルールで扱う領域)
- 単漢字 1 文字の surface (上記参照、unihan 専用)

## ファイルが大きくなりすぎたら

`core/jukugo/` `rules/counters/` `rules/context/` の 3 つは **同名サブディレクトリ
配下の `*.toml` を全て自動 merge** する仕組みになっている (lib loader 側で対応済み)。
1 ファイルが PR レビューしづらいサイズになったら、**自由に分割して構わない**:

```
core/jukugo/
├── general.toml                # 既存
├── general_a.toml              # 「あ」始まりだけ別ファイルに分けたい場合
└── general_ka.toml             # ...等

rules/counters/
├── simple.toml                 # 既存カテゴリ
├── time.toml
├── objects.toml
└── new_category.toml           # 新カテゴリも自由に追加 OK
```

- ファイル名は何でも構わない (lib は filename ソート順で全 toml を merge)
- 同じ key を複数ファイルに書くと **後勝ち** (filename ソート後の最後が採用)
- counters / context のように **複雑な構造の merge** が必要なものは `merge()` ロジックが
  lib 側にあるので「分け方」は自由 (例: `01_basics.toml` `02_special.toml` 等の数字 prefix で順序制御も可)

PR で大きく追加するときは:
1. 1 PR あたり ~50 件程度に分割すると review が早い
2. 分野別 (人名 / 地名 / IT 用語 / 古典文学 ...) で別 PR にすると merge conflict も避けやすい

## ファイル別ガイド

### `core/jukugo/` — 一般熟語 + 固有名詞 + 文化系 (24 ファイルに細分化)

カテゴリ別に 24 ファイルに分かれているので適切なファイルに追加する。
**最新の件数 / 用途一覧は [STATS.md](STATS.md)** (各 TOML の `[meta] description` から自動生成、
カテゴリの粒度を知りたい時はそれを参照)。

代表カテゴリ (例):

| ファイル | 用途 | 例 |
|---|---|---|
| `general.toml`        | 二字 / 三字の一般熟語 + 季節 / 行事 / 慣用句 | 灰桜 / 黎明 / 立春 / お盆 |
| `four_char.toml`      | 四字熟語 (4 字 + 全部 CJK 漢字) | 一期一会 / 四面楚歌 / 一目瞭然 |
| `proper_nouns.toml`   | 大学・中央官庁・元号・歴史的事象 | 早稲田大学 / 文部科学省 / 令和 |
| `place_names.toml`    | 国・都道府県・駅・寺社仏閣・観光地 | 北海道 / 京都駅 / 東大寺 / 富士山 |
| `personal_names.toml` | 姓・名・著名人 (古典・歴史中心、現代私人は避ける) | 紫式部 / 夏目漱石 / 渡邊 |
| `animals.toml` / `foods.toml` / `weather.toml` / `colors.toml` | 自然・物質系の難読 | 蝙蝠 / 餃子 / 時雨 / 茜色 |
| `specialized.toml`    | 専門用語 (医学 / 軍事 / 法学 / 経済 / IT) | 蕁麻疹 / 駆逐艦 / 量子力学 |
| `body_parts.toml`     | 体の部位 / 内臓 / 骨格 / 筋肉 / 神経 | 鳩尾 / 副腎 / 三角筋 |
| `arts.toml` / `music.toml` | 古典芸能 / 武道 / 茶華香 / 工芸 / 楽典 | 三味線 / 歌舞伎 / 撥弦楽器 |
| `architecture.toml` / `vehicles.toml` / `clothes.toml` | 建築 / 乗物 / 衣服 | 天守 / 連絡船 / 狩衣 |
| `literature.toml` / `abstracts.toml` / `idioms.toml` | 古典文学 / 美意識 / 慣用句 | 太平記 / 物の哀れ / 蛇足 |
| `science.toml`        | 自然科学 (天文 / 物理 / 化学 / 生物 / 地学) | 突然変異 / 円周率 / 鍾乳洞 |
| `emotions.toml` / `religions.toml` / `politics.toml` / `sports.toml` | 心理 / 宗教 / 政治 / 近代スポーツ | 戦慄 / 修験道 / 公示 / 競歩 |

追加例 (`core/jukugo/basic/general.toml`):
```toml
[meta]
description = "二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む)"

[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
"曙光" = "ショコウ"
```

判断に迷う場合は `general.toml` でも構わない (review で振り分け可能)。

### `core/works/` — 作品単位の固有名詞・造語

特定の作品 (アニメ / ゲーム / 漫画 等) の固有名詞・造語を **1 作品 = 1 ファイル** で集める専用ディレクトリ。
loader が全階層再帰でスキャンするため、`core/works/<medium>/<title>.toml` の構造で配置する
(例: `core/works/game/touhou.toml`)。

**追加要件 (jukugo より厳しい)**:
- **公式読みのみ採録** (二次創作読み・ファン推測は不可)
- ファイル先頭に **出典 URL** を comment で必須記載
- 商標的にグレーなコラボ商品名 / 二次商標は入れない

詳細サブポリシーは [`core/works/README.md`](core/works/README.md) を参照。

### `core/loanwords/` — 外来語 (IT 用語等の英字 surface)

ASCII / 全角英字始まりの surface に対するカタカナ ヨミを置く専用ディレクトリ。
ja-furigana 側 chunks 階層 4.7 で **完全一致 lookup** (case-fold + 全角→半角) で参照される。
将来的にカテゴリ細分化を許容するサブディレクトリ構造 (例: `core/loanwords/it.toml`、
`core/loanwords/company.toml` など) で配置。

**形式**:
```toml
[meta]
description = "IT 用語 / プログラミング言語 / OSS / クラウドサービス / 技術企業 (ASCII surface)"

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
- 「.NET」 「@types/node」 のような **記号始まり** surface (regex に match しない、 alias で「DotNET」 等を別 entry に)
- 短すぎる ASCII (例: 「IT」 「OS」) は誤マッチを起こしやすいので慎重に検討

### `rules/counters/` — 助数詞ルール (7 ファイルに細分化)

| ファイル | 範囲 |
|---|---|
| `simple.toml`     | 単純サフィックス助数詞 (`[simple]`) |
| `time.toml`       | 月 / 日 / 時 / 分 / 分半 / 週間 / 回 |
| `people.toml`     | 人 |
| `objects.toml`    | 本 / 匹 / 杯 / 個 / 歳 / 冊 |
| `places.toml`     | 階 / ヶ所 / 箇所 / か所 |
| `percent.toml`    | % / ％ |
| `recursive.toml`  | 目 (再帰モード) |

新しい助数詞は **既存カテゴリの該当ファイル** に足すか、当てはまらなければ
カテゴリを増やしてもよい (PR で議論)。エンジン側はサブディレクトリ内の `*.toml`
全てを自動マージするので、ファイル名は何でも構わない。

#### 書き方 (連濁 / 促音化 を持つ助数詞、 例: 「本」 / 「匹」)

```toml
[counter."本"]
default = "ホン"             # どの rule にも当てはまらない数値で使う読み

[[counter."本".rules]]
last_digit = [1, 6, 8, 0]    # 1 / 6 / 8 / 10 / 100 等で
suffix = "ポン"              # 「ポン」 (1 本 = イッポン)
sokuonize = true             # 直前の数値末尾を促音化 (1 → イッ、 6 → ロッ、 8 → ハッ、 10 → ジッ)

[[counter."本".rules]]
last_digit = [3]             # 3 で
suffix = "ボン"              # 「ボン」 (3 本 = サンボン、 連濁のみ、 促音化なし)
```

書きどころ:

- **counter 名** (`"本"`) は同 file 内で 3 回登場するが、 toml の table path として
  必要 (`[counter."本"]` + 2 つの `[[counter."本".rules]]`)
- `last_digit` は 数字の **末尾 1 桁** で match (例: `100 → 0`、 `13 → 3`、 `100000 → 0`)
- `sokuonize = true` は「促音化」 (直前数字の末尾 を ッ に)、 `false` (or 省略) は連濁のみ
- 連濁も促音化も無い助数詞は `default` だけ書く (rules 不要)

```toml
[counter."回"]
default = "カイ"             # 1 回 = イチカイ、 3 回 = サンカイ、 連濁なし
```

#### 「kana 末尾置換」 (例: 「分」 ジュウフン → ジップン)

```toml
[counter."分"]
default = "フン"

[[counter."分".rules]]
last_digit = [1, 3, 4, 6, 8, 0]
suffix = "プン"
sokuonize = true
kana_replace = { "ジュウ" = "ジッ" }   # 「ジュウフン」 → 「ジップン」 のような置換
```

`kana_replace` は数値 surface 側の kana を rule マッチ時に置き換える (限定的、 必要時のみ使う)。

### `rules/context/` — 文脈依存読み (3 ファイルに細分化)

| ファイル | 範囲 |
|---|---|
| `numbers.toml`  | 数字を含む慣用語句 (一日 / 一人 / 一月 / 一杯 等) |
| `homonyms.toml` | 同形異音語 (上手 / 下手 / 人気 / 大人気 / 十分) |
| `special.toml`  | 単純な読み固定 (大人 / 仲人 / 今日 / 何日 / 日本 等) |

#### 書き方

各ルールは「surface (対象表層) + match (条件 → 読み) のリスト + default (任意のフォールバック)」:

```toml
[[rule]]
surface = "一日"
default = "イチニチ"          # どの match にも当てはまらないときの読み (任意)

[[rule.match]]
prev_ends_with_month = true   # 前トークンが「1月」「12月」等で終わるなら…
reading = "ツイタチ"          # 「ツイタチ」と読む
```

match は **上から順に評価** され、最初にマッチしたものが採用されます。
1 つの match 内で複数条件を書くと **AND 条件** (全部満たす必要あり)。

#### 使える条件一覧

**前のトークン (prev) を見る**
| 条件 | 意味 | 例 |
|---|---|---|
| `prev_eq = "X"` | 前のトークンが完全に `"X"` | `prev_eq = "毎"` |
| `prev_ends_with_any = ["X", "Y"]` | 前のトークンの末尾が X か Y | `prev_ends_with_any = ["毎", "約", "丸"]` |
| `prev_ends_with_month = true` | 前のトークンが「1月」〜「12月」 | (例: `「6月一日」の前=「6月」`) |

**後のトークン (next) を見る**
| 条件 | 意味 | 例 |
|---|---|---|
| `next_eq = "X"` | 次のトークンが完全に `"X"` | `next_eq = "が"` |
| `next_starts_with = "X"` | 次のトークンが `"X"` で始まる | `next_starts_with = "な"` |
| `next_starts_with_any = ["X", "Y"]` | 次のトークンが X か Y で始まる | `next_starts_with_any = ["中", "間", "分"]` |
| `next_starts_with_digit = true` | 次のトークンが数字で始まる | (例: `「一月7日」の次=「7日」`) |

**2 つ後のトークン (next-next) を見る**
| 条件 | 意味 | 例 |
|---|---|---|
| `next_next_starts_with_any = ["X", "Y"]` | 2 つ後が X か Y で始まる | `next_next_starts_with_any = ["な", "無"]`  (`人気 が 無い` の判定) |

**形態素解析の品詞 (pos) を見る**
| 条件 | 意味 | 例 |
|---|---|---|
| `pos_eq = "X"` | 当該トークンの品詞が完全に X | `pos_eq = "名詞"`、`pos_eq = "形容詞"` |

> ヒント: 条件名で迷ったら既存の `numbers.toml` / `homonyms.toml` / `special.toml`
> をテンプレートとしてコピーするのが早道です。新ルールを追加する PR では
> **どのテキストでどう変わるか** を 1-2 例書いてくれると review が楽です。

#### 典型 pattern 例集 (コピペ start)

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

evaluate 順は **上から順**、 最初に match した reading が採用される。 `default` はどの match
にも当てはまらない時の fallback。 default を書かない場合は context rule 自体を skip して
通常 pipeline (jukugo / Lindera / unihan fallback) に流れる。

### `core/unihan/*.toml` — 単漢字フォールバック (水準別)

漢字 1 文字 → カタカナ or ひらがな。 形態素解析でも辞書でもヒットしない単漢字の最終フォールバック。
**水準別に分割** されており (利用頻度の高い常用漢字に review を集中させるため)、
具体的な file 名 / 件数は [STATS.md の「単漢字」 section](STATS.md#単漢字) を参照。

例:
```toml
[entries]
"鬱" = "ウツ"
"曰" = "イワク"
```

> 単漢字は文脈で読みが変わるため、**最も一般的な音/訓読み 1 つ** を採用。
> 文脈依存が必要な場合は [`rules/context/`](rules/context) 配下のルールで扱う。
> Lindera reading より優先したい単漢字は [`core/single_overrides.toml`](core/single_overrides.toml) で個別に override
> ([issue #15](https://github.com/RyuuNeko1107/ja-furigana/issues/15) の限定解、 1 字 surface のみ)。

### `core/compat.toml` — 異体字 → 標準字

「髙→高」のように、字形が違うが同じ漢字として扱いたい異体字の正規化マップ。
エンジン側に他の compat 表は無いので、ここが正典 (上乗せではなく単独の出典)。

例:
```toml
[map]
"瀧" = "滝"
"靑" = "青"
```

### `rules/postprocess.toml` — 後処理 regex (Step 7 (mode 別後処理 regex))

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

- pattern は Rust `regex` クレートの構文。POSIX 風 + `(?P<name>...)` 名前付きキャプチャ可。
- replacement で `$0` は全マッチ、`$1`〜`$N` は順番のキャプチャ。
- modes に書ける値: `"hiragana"` / `"ruby"` / `"tts"` / `"romaji"` のいずれか (or 空 = 全 mode)。
- **`ruby` mode は出力に `{漢字|読み}` 構造を含む** ので、`{` `|` `}` を壊さない pattern にすること。
  心配なら modes に `"ruby"` を入れない。
- 起動時に regex を pre-compile するため、不正な pattern は loader 段で fail する。
- regex 圧縮 size は 10 MB で cap される (regex bomb 防御)、 通常 pattern は数百 byte なので問題なし。

#### よくあるパターン例集

```toml
# (1) 単純な置換 (全 mode 共通)
[[rule]]
pattern = "ジュウパー"
replacement = "ジュッパー"
modes = []                            # 空 = 全 mode

# (2) capture group で一部を残す
[[rule]]
pattern = "(\\d+)\\s*ヶ"               # 数字 + 任意の空白 + ヶ
replacement = "$1カ"                   # 数字を保持して 「ヶ」 → 「カ」
modes = []

# (3) hiragana mode 限定
[[rule]]
pattern = "ぱーせんと"
replacement = "パーセント"
modes = ["hiragana"]                  # hiragana 出力時のみ

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

PR で追加するときは、**該当する例文** (before / after) をコメント or PR description に
書いてくれると review しやすい。

### `rules/numeric_phrases.toml` — 数字を含む例外語句

通常の数値 + 助数詞 ロジックでは扱えない、 慣用的な読み (二十歳=ハタチ、 八十=ヤソ 等):

```toml
[entries]
"二十歳" = "ハタチ"
"八十"   = "ヤソ"
"百個"   = "ヒャッコ"        # counter 連濁を超えた特殊読み
"千個"   = "センコ"
```

`[entries]` table に key=value 形式で書くだけ。 数字を含む surface (or 慣用語句的に
固定読みされるもの) を ad-hoc に上書きする領域。

### `rules/days.toml` — 1〜31 日の特殊読み

```toml
[entries]
"1"  = "ツイタチ"          # 1 日 = ツイタチ
"2"  = "フツカ"
"3"  = "ミッカ"
"4"  = "ヨッカ"
"5"  = "イツカ"
"6"  = "ムイカ"
"7"  = "ナノカ"
"8"  = "ヨウカ"
"9"  = "ココノカ"
"10" = "トオカ"
"14" = "ジュウヨッカ"
"20" = "ハツカ"
"24" = "ニジュウヨッカ"
# ... 他は default (ニチ) 適用
```

数字 (1〜31) → 特殊読み の単純 mapping。 「N 日」 文脈でのみ参照される (= 通常の数値文脈には影響なし)。

### `rules/scales.toml` — 大数 (万 / 億 / 兆 / 京 ...)

```toml
[entries]
"万" = "マン"
"億" = "オク"
"兆" = "チョウ"
"京" = "ケイ"
"垓" = "ガイ"
```

scale + 漢字単位 1 文字 (「1 万円」「3 億ドル」) を 1 chunk として処理する基盤。

### `rules/units.toml` — SI 単位 + 通貨 + %

```toml
[entries]
"km" = "キロメートル"      # case-insensitive (KM / Km / km 全部 hit)
"kg" = "キログラム"
"mL" = "ミリリットル"
"円" = "エン"
"%"  = "パーセント"
```

数値 + 単位 を 1 chunk で読む (「3 km」「100 円」)。 case-insensitive lookup で書く側は小文字推奨。

### `rules/symbols.toml` / `rules/latin.toml`

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

単一文字 → 読み の単純 mapping。 chunks/split() で個別文字 chunk として hit する。

## Inline test (各 file 内に書ける小型テスト)

各 dict / rule TOML の **末尾** に `[[test]]` array を書くと、 CI で binary に
input を流して expected (hiragana mode) と一致するか自動検証される。 corpus
regression (`tests/corpus/should_read.toml`) は repo 全体の最終ロック、 inline
test は **file 単位の「この file が担当する変換」 ロック**。

```toml
# rules/counters/objects.toml の末尾
[[test]]
input = "1本"
expected = "いっぽん"

[[test]]
input = "3本"
expected = "さんぼん"
```

走らせ方 (local):
```sh
python tools/test_inline_rules.py \
  --binary path/to/furigana \
  --data-dir path/to/data-dir
```

CI では ja-furigana 側 `ci.yml` の corpus regression job 内で `tools/test_inline_rules.py`
を併走。 inline test 0 件の file は skip、 contributor は書きたい file から書ける緩い制約。

`[[test]]` を書ける場所:
- core/jukugo/<...>.toml / core/works/<...>.toml / core/loanwords/<...>.toml
- core/single_overrides.toml / core/compat.toml
- rules/*.toml (counters / context / postprocess / 等含む全 file)

注: `[[test]]` table は lib では silent skip される (entries / map / 各 rule schema
に含まれない field は serde で無視)、 配布 tar.gz には含まれるが parse 後 memory
に乗らない (= disk 上だけ存在、 runtime memory には影響なし)。

## CI (validate)

PR を出すと GitHub Actions で:

1. **TOML 構文チェック** (taplo) — 全 `*.toml` のパース可能性
2. **スキーマ + カタカナ検証** (`tools/validate.py`):
   - 各ファイルの構造 (`[entries]`, `[map]`, `[[entry]]`, `[[rule]]` 等)
   - 必須フィールド (kana / kanji / surface 等) の存在
   - **読み (value) が ひらがな または 全角カタカナ** で書かれているか
     - ❌ ローマ字 (Haizakura)、半角カナ (ﾊｲｻﾞｸﾗ)、混在 (はいザクラ)
     - ✅ ひらがな (はいざくら) / 全角カタカナ (ハイザクラ) / 長音 (ー) / 中点 (・)
   - jukugo / unihan の **cross-file 重複** 検出

これらが緑になれば merge 可能。

### ローカルで事前チェック

```sh
python3 tools/validate.py
# → [OK] N ファイル検査済 (jukugo X / unihan Y entries)
# 失敗時は [FAIL] と詳細が出る
```

Python 3.11+ が必要 (`tomllib` 使用)。

`jukugo/` `counters/` `context/` のサブディレクトリは展開して全 `*.toml` が
順に検査される。重複 key 等のエラーは該当ファイル名 + 行情報付きで出る。

## Release / 配布

`v*` タグを push すると Release workflow が `furigana-dict-vX.Y.Z.tar.gz` を生成し
GitHub Release に upload する。利用側は `furigana dict pull --version vX.Y.Z` で取得。

## レビュー方針

「正しい読み」 vs 「自然な読み」で意見が割れた場合は、**TTS 読み上げで
実用上自然な方** を採用する。
