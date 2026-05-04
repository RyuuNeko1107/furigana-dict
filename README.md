# furigana-dict

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Japanese word dictionary for the [furigana](https://github.com/RyuuNeko1107/furigana) library — open, community-maintained.

[`furigana`](https://github.com/RyuuNeko1107/furigana) (フリガナ API + ライブラリ) で利用される
**語彙辞書** をホストする独立リポジトリ。読みの追加・修正は **TOML を編集して PR** だけで完結する。

> ⚠️ **Status**: Pre-alpha — 初期 seed 投入中。空に近い状態です。

---

## なぜ別リポジトリ?

語彙辞書は数万エントリ規模になり、本体コード (Rust) のリポジトリと一緒に管理すると:

- 辞書の PR レビューがコード PR と混じって視認性が落ちる
- 言語学者・日本語教師など Rust に触らない contributor が PR を躊躇する
- 辞書だけ更新したくても本体ビルドの CI が走る

これを避けるため、辞書は本リポジトリで **独立にバージョニング・配布** している。
[`furigana dict pull`](https://github.com/RyuuNeko1107/furigana#辞書の置き場所) で
GitHub Release から tar.gz を取得する仕組み。

## 構成

```
core/
├── jukugo.toml      ← 熟語・固有名詞 (PR が主に飛んでくる場所)
├── unihan.toml      ← 単漢字フォールバック
└── compat.toml      ← 異体字 → 標準字 (本体の compat_map に上乗せ)
```

## TOML 形式

すべて以下の形式:

```toml
[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
"明後日" = "アサッテ"
```

- key: 表層形 (漢字を含む文字列)
- value: 全角カタカナの読み
- 1 行 = 1 エントリ
- ファイル内では **50 音順** または **追加日時順** で整理

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照。

## 利用側 (`furigana` から)

```sh
$ furigana dict pull               # 最新 release を取得
$ furigana dict pull --version v0.1.0   # ピン留め
```

`~/.local/share/furigana/dict/core/` に展開され、`furigana serve` / `furigana lookup` が
自動的にロードする。

## ライセンス

[MIT License](LICENSE)。語彙辞書のエントリ自体に著作権を主張する根拠は薄いが、
ファイル形式・編集ガイドラインなどの contribution は MIT で公開する。

## コントリビュート

歓迎! 詳細は [CONTRIBUTING.md](CONTRIBUTING.md)。

最も多いケース (読みを 1 件追加):

1. 該当ファイル ([`core/jukugo.toml`](core/jukugo.toml) 等) を GitHub の Web UI で編集
2. 「Commit changes」→「Create pull request」
3. CI (TOML 構文チェック) が通れば maintainer が merge

Rust も Git のクローンも不要。
