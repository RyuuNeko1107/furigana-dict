# Contributing to furigana-dict

語彙辞書の追加・修正は **TOML を 1 行追加するだけ** で完結する。
Rust 知識・Git クローン不要。

## クイックパス: GitHub Web UI で 1 件追加

1. 該当ファイルを開く:
   - 一般語 → [`core/jukugo/general.toml`](core/jukugo/general.toml)
   - 固有名詞 (会社・作品名等) → [`core/jukugo/proper_nouns.toml`](core/jukugo/proper_nouns.toml)
   - 地名 → [`core/jukugo/place_names.toml`](core/jukugo/place_names.toml)
   - 人名 → [`core/jukugo/personal_names.toml`](core/jukugo/personal_names.toml)
   - 単漢字フォールバック → [`core/unihan.toml`](core/unihan.toml)
   - 異体字 → [`core/compat.toml`](core/compat.toml)
2. 右上の鉛筆アイコン (Edit) をクリック
3. `[entries]` セクションに 1 行追加:
   ```toml
   "新しい表層" = "シンシイヒョウソウ"
   ```
4. ページ下部の「Commit changes」→ ブランチ自動生成 → PR 作成

## ローカル編集 (複数件・差分大きめ)

```sh
git clone https://github.com/RyuuNeko1107/furigana-dict
cd furigana-dict
# core/*.toml を編集
git checkout -b add-readings
git commit -am "add: 灰桜/黎明 等"
gh pr create
```

## TOML 形式の注意点

### 必須

- key (表層) と value (読み) は **ダブルクォート** で囲む: `"灰桜" = "ハイザクラ"`
- value は **ひらがな または 全角カタカナ** (半角カナ・ローマ字は不可)
  - 慣習的に **訓読み = ひらがな / 音読み = カタカナ** で書き分ける (例: `"桜" = "さくら"` / `"音" = "オン"`)
  - エンジン側で出力時に正規化されるため、どちらで書いても挙動は同じ
- 1 ファイル内で同じ key を二重登録しない (TOML パーサがエラーを吐く)

### 推奨

- ファイル内のエントリは **50 音順** で並べる (PR diff が読みやすくなる)
- 大量追加するときは:
  - 同じ PR に **同じ分野 (人名 / 地名 / 一般語)** をまとめる
  - 1 PR あたり ~50 件程度を目安に分割すると review が楽

### NG

- 商標・固有名詞のうち **公的に認知されていない読み** (誤読をデフォルト化しない)
- 文脈で読みが変わる語の片方だけを `core/jukugo/*` の default にする (それは [`rules/context/`](rules/context) 配下の文脈ルールで扱う領域)

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

### `core/jukugo/` — 一般熟語 + 固有名詞 (5 ファイルに細分化)

カテゴリ別に分かれているので適切なファイルに追加する:

| ファイル | 用途 | 例 |
|---|---|---|
| `general.toml`        | 二字 / 三字の一般熟語 | 灰桜 / 黎明 / 曙光 / 所謂 |
| `four_char.toml`      | 四字熟語 (4 字 + 全部 CJK 漢字) | 一期一会 / 四面楚歌 / 優柔不断 |
| `proper_nouns.toml`   | 会社名・作品名・ブランド名等 | (拡充予定) |
| `place_names.toml`    | 国名・都道府県名・市区町村名・駅名・著名スポット | 湯島天神 |
| `personal_names.toml` | 姓・名・著名人のフルネーム | 金田一 |

追加例 (`core/jukugo/general.toml`):
```toml
[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
"曙光" = "ショコウ"
```

判断に迷う場合は `general.toml` でも構わない (review で振り分け可能)。

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

### `core/unihan.toml` — 単漢字フォールバック

漢字 1 文字 → カタカナ。形態素解析でも辞書でもヒットしない単漢字の最終フォールバック。

例:
```toml
[entries]
"鬱" = "ウツ"
"曰" = "イワク"
```

> 単漢字は文脈で読みが変わるため、**最も一般的な音/訓読み 1 つ** を採用。
> 文脈依存が必要な場合は [`rules/context/`](rules/context) 配下のルールで扱う。

### `core/compat.toml` — 異体字 → 標準字

「髙→高」のように、字形が違うが同じ漢字として扱いたい異体字の正規化マップ。
エンジン側に他の compat 表は無いので、ここが正典 (上乗せではなく単独の出典)。

例:
```toml
[map]
"瀧" = "滝"
"靑" = "青"
```

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

「正しい読み」 vs 「自然な読み」で意見が割れた場合は、**本番 ryuuneko.com で
実用上自然な方** を採用する (TTS 読み上げ用途を優先)。
