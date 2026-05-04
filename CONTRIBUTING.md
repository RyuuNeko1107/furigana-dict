# Contributing to furigana-dict

語彙辞書の追加・修正は **TOML を 1 行追加するだけ** で完結する。
Rust 知識・Git クローン不要。

## クイックパス: GitHub Web UI で 1 件追加

1. 該当ファイルを開く:
   - 一般語・固有名詞 → [`core/jukugo.toml`](core/jukugo.toml)
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
- 文脈で読みが変わる語の片方だけを default にする (それは本体 [`furigana`](https://github.com/RyuuNeko1107/furigana) の `data/rules/context.toml` で扱う領域)

## ファイル別ガイド

### `core/jukugo.toml` — 一般熟語 + 固有名詞

メインの PR 受付先。誰でも気軽に追加 OK。

例:
```toml
[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
"曙光" = "ショコウ"
"金田一" = "キンダイチ"   # 人名
"湯島天神" = "ユシマテンジン" # 固有名詞
```

### `core/unihan.toml` — 単漢字フォールバック

漢字 1 文字 → カタカナ。形態素解析でも辞書でもヒットしない単漢字の最終フォールバック。

例:
```toml
[entries]
"鬱" = "ウツ"
"曰" = "イワク"
```

> 単漢字は文脈で読みが変わるため、**最も一般的な音/訓読み 1 つ** を採用。
> 文脈依存が必要な場合は本体 `data/rules/context.toml` で扱う。

### `core/compat.toml` — 異体字 → 標準字

本体 [`compat_map.toml`](https://github.com/RyuuNeko1107/furigana/blob/master/data/rules/compat_map.toml)
の **上乗せ** 用。本体に既にあるエントリを再録する必要はない。

例:
```toml
[map]
"瀧" = "滝"
"靑" = "青"
```

## CI (validate)

PR を出すと GitHub Actions で:

1. **TOML 構文チェック** (taplo) — `[entries]` セクション + `"key" = "value"` 形式
2. **ビルド確認** — 本体 `furigana` から実際にロードできるかの smoke test

これらが緑になれば merge 可能。

## Release / 配布

`v*` タグを push すると Release workflow が `furigana-dict-vX.Y.Z.tar.gz` を生成し
GitHub Release に upload する。利用側は `furigana dict pull --version vX.Y.Z` で取得。

## 行動規範

- PR レビューは技術的指摘に限定 (人格・属性への言及はしない)
- 「正しい読み」 vs 「自然な読み」 で意見が割れた場合は **本番 ryuuneko.com で実用上自然な方** を採用 (TTS 用途優先)

ありがとうございます 🍀
