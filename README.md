# furigana-dict

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Japanese word dictionary for the [furigana](https://github.com/RyuuNeko1107/ja-furigana) library — open, community-maintained.

[`furigana`](https://github.com/RyuuNeko1107/ja-furigana) (フリガナ API + ライブラリ) で利用される
**語彙辞書** をホストする独立リポジトリ。読みの追加・修正は **TOML を編集して PR** だけで完結する。

> 件数 / カテゴリ別内訳 / サイズの最新値は [**STATS.md**](STATS.md) を参照
> (TOML 編集後の master push で GitHub Actions が auto-commit するので、contributor は何もしなくて OK)。
> 最新リリースは [GitHub Releases](https://github.com/RyuuNeko1107/ja-furigana-dict/releases) を参照。

---

## なぜ別リポジトリ?

**管理を楽にするため**。辞書エントリ数が増えると本体コードのリポジトリで一緒に管理するのが煩雑なので分けた。

`furigana dict pull` で GitHub Release から tar.gz を取得する仕組み。

## 構成

```
core/
├── jukugo/         ← 熟語・固有名詞 (一般熟語 / 地名 / 人名 / 専門 / 文化等のカテゴリ別 24 ファイル)
├── works/          ← 作品単位の固有名詞・造語 (例: works/game/touhou.toml — 公式読みのみ採録、サブポリシーあり)
├── unihan.toml     ← 単漢字フォールバック (43k 字、初期 seed 由来)
└── compat.toml     ← 異体字 → 標準字 (髙→高 等)

rules/
├── counters/       ← 助数詞ルール (本 / 匹 / 個 / 年 / 月 / 日 …、連濁・促音化)
├── context/        ← 文脈依存読み (一日→ツイタチ/イチニチ 等)
├── days / scales / units / symbols / latin / numeric_phrases / postprocess
```

各ファイルの **詳細な用途・件数・サイズ** は [STATS.md](STATS.md) で自動生成されるテーブル参照。
ファイル先頭の `[meta] description = "..."` がそのまま STATS.md の用途列に使われる仕組み。

> 配布側 (`furigana dict pull` で展開後) は `data/` 1 階層に flat に並ぶ。
> repo 内の `core/` `rules/` の階層分けは PR レビュー上の分類のためで、エンジン側は
> ファイル名と中身の構造で自動振り分けする。
> ja-furigana 0.1.0-alpha.6 以降は `core/works/<medium>/<title>.toml` のような
> 任意深度のサブディレクトリも全階層再帰でロードされる。

## TOML 形式

すべて以下の形式:

```toml
[meta]
description = "<このファイルの用途説明、STATS.md に自動引用される>"

[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
"明後日" = "アサッテ"
```

- `[meta] description`: 1 行説明、`tools/regen_stats.py` が STATS.md の用途列に取り込む
- `[entries]` key: 表層形 (漢字を含む文字列)
- `[entries]` value: ひらがな または 全角カタカナ の読み (慣習: 訓=ひら / 音=カタ)
- 1 行 = 1 エントリ
- ファイル内では **50 音順** または **追加日時順** で整理

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照。

## 利用側 (`furigana` から)

```sh
$ furigana dict pull               # 最新 release を取得 + ローカルに展開
$ furigana dict pull --version v0.1.1   # ピン留め
```

default では `<furigana.exe と同じフォルダ>/data/` に展開される (portable 配置)。
`furigana serve` / `furigana lookup` / `furigana repl` が自動的にロード。
REPL の中からは `:pull` (or `pull`) でも同じ操作ができる。

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
