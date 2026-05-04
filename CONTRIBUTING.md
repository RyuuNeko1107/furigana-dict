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
- value は **全角カタカナ** (ひらがな・半角カナは不可)
- 1 ファイル内で同じ key を二重登録しない (TOML パーサがエラーを吐く)

### 推奨

- ファイル内のエントリは **50 音順** で並べる (PR diff が読みやすくなる)
- 大量追加するときは:
  - 同じ PR に **同じ分野 (人名 / 地名 / 一般語)** をまとめる
  - 1 PR あたり ~50 件程度を目安に分割すると review が楽

### NG

- 商標・固有名詞のうち **公的に認知されていない読み** (誤読をデフォルト化しない)
- 文脈で読みが変わる語の片方だけを `core/jukugo/*` の default にする (それは [`rules/context/`](rules/context) 配下の文脈ルールで扱う領域)

## ファイル別ガイド

### `core/jukugo/` — 一般熟語 + 固有名詞 (4 ファイルに細分化)

カテゴリ別に分かれているので適切なファイルに追加する:

| ファイル | 用途 | 例 |
|---|---|---|
| `general.toml`        | 一般熟語・四字熟語等 | 灰桜 / 黎明 / 曙光 / 所謂 |
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
   - **読み (value) が全角カタカナのみ** で書かれているか
     - ❌ ひらがな (はいざくら)、ローマ字 (Haizakura)、半角カナ
     - ✅ 全角カタカナ (ハイザクラ) + 長音 (ー) + 中点 (・)
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
