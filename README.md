# furigana-dict

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Japanese word dictionary for the [furigana](https://github.com/RyuuNeko1107/furigana) library — open, community-maintained.

[`furigana`](https://github.com/RyuuNeko1107/furigana) (フリガナ API + ライブラリ) で利用される
**語彙辞書** をホストする独立リポジトリ。読みの追加・修正は **TOML を編集して PR** だけで完結する。

> ⚠️ **Status**: Pre-alpha — 初期 seed 投入中。空に近い状態です。

---

## なぜ別リポジトリ?

**管理を楽にするため**。辞書エントリ数が増えると本体コードのリポジトリで一緒に管理するのが煩雑なので分けた。

`furigana dict pull` で GitHub Release から tar.gz を取得する仕組み。

## 構成

```
core/
├── jukugo/                    ← 熟語・固有名詞 (PR が主に飛んでくる場所)
│   ├── general.toml           一般熟語・四字熟語
│   ├── proper_nouns.toml      会社名・作品名・ブランド名
│   ├── place_names.toml       地名 (国・都道府県・駅 等)
│   └── personal_names.toml    人名 (姓・名・著名人)
├── unihan.toml                ← 単漢字フォールバック
└── compat.toml                ← 異体字 → 標準字 (上乗せ)

rules/
├── counters/                  ← 助数詞ルール (7 ファイル)
│   ├── simple.toml            ・time.toml ・people.toml
│   ├── objects.toml           ・places.toml ・percent.toml ・recursive.toml
├── context/                   ← 文脈依存読み (3 ファイル)
│   ├── numbers.toml           数字を含む慣用語句
│   ├── homonyms.toml          同形異音語 (上手 / 下手 / 十分 等)
│   └── special.toml           その他読み固定 (今日 / 何日 / 仲人 等)
├── days.toml                  1〜31 日の特殊読み
├── scales.toml                大数 (万 / 億 / 兆 / 京…)
├── units.toml                 SI 単位
├── symbols.toml               記号
├── latin.toml                 ラテン文字
└── numeric_phrases.toml       例外語句 (二十歳→ハタチ 等)
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

1. カテゴリに合うファイル (例: 一般語なら [`core/jukugo/general.toml`](core/jukugo/general.toml)) を GitHub の Web UI で編集
2. 「Commit changes」→「Create pull request」
3. CI (TOML 構文チェック + カタカナ検証) が通れば maintainer が merge

Rust も Git のクローンも不要。
