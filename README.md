# furigana-dict

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Japanese word dictionary for the [furigana](https://github.com/RyuuNeko1107/ja-furigana) library — open, community-maintained.

[`furigana`](https://github.com/RyuuNeko1107/ja-furigana) (フリガナ API + ライブラリ) で利用される
**語彙辞書** をホストする独立リポジトリ。 読みの追加・修正は **TOML を編集して PR** だけで完結する。

> 件数 / カテゴリ別内訳 / サイズの最新値は [**STATS.md**](STATS.md) を参照
> (master push で GitHub Actions が auto-commit、 contributor は何もしなくて OK)。
> 最新リリースは [GitHub Releases](https://github.com/RyuuNeko1107/ja-furigana-dict/releases) を参照。

> 🔍 **全 entries を web 上で検索 / フィルタ / 閲覧**:
> <https://ryuuneko1107.github.io/ja-furigana-dict/>
> ([`tools/build_dict_browser.py`](tools/build_dict_browser.py) が master push のたび
> [GitHub Actions で auto-deploy](.github/workflows/build-pages.yml)、 漢字別 sweep
> 進捗管理機能 / 冗長 jukugo 検出 / `[[kanji]]` block detail view あり)

## なぜ別リポジトリ?

辞書エントリ数が増えると本体コードのリポジトリと一緒に管理するのが煩雑なので分けた。
`furigana dict pull` で GitHub Release から tar.gz を取得する仕組み。

## 構成

```
core/
├── jukugo/         ← 熟語・固有名詞 (一般熟語 / 地名 / 人名 / 専門 / 文化等のカテゴリ別 24 ファイル)
├── works/          ← 作品単位の固有名詞・造語 (例: works/game/touhou.toml)
├── loanwords/      ← 外来語 (IT 用語等の英字 surface、 例: loanwords/it.toml)
├── unihan/*.toml   ← 単漢字フォールバック (43k+ 字、 5 水準別)
├── single_overrides.toml ← 単漢字 default の明示的 override (限定解)
└── compat.toml     ← 異体字 → 標準字 (髙→高 等)

rules/
├── counters/       ← 助数詞ルール (本 / 匹 / 個 / 年 / 月 / 日 …、連濁・促音化)
├── context/        ← 文脈依存読み (一日→ツイタチ/イチニチ 等)
├── days.toml / scales.toml / units.toml / symbols.toml / latin.toml
├── numeric_phrases.toml / postprocess.toml
```

各ファイルの **詳細な用途・件数・サイズ** は [STATS.md](STATS.md) で auto-gen される
(ファイル先頭の `[meta] description` が用途列に取り込まれる)。

> **cross-file 重複** が気になるときは [STATS_DUPS.md](STATS_DUPS.md) で「同 reading の重複」
> 「異 reading の divergent (CI fail 対象)」 を一覧で確認できる。

> 配布側 (`furigana dict pull` で展開後) は `data/` 1 階層に flat に並ぶ。
> repo 内の `core/` `rules/` の階層分けは PR レビュー上の分類のためで、 エンジン側は
> ファイル名と中身の構造で自動振り分けする (alpha.9+ は `[meta] role` tag 駆動 + path-based fallback)。

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | クイックパス + 1 行追加の流れ + TOML 形式の最低限ルール |
| [`docs/SCHEMA.md`](docs/SCHEMA.md) | 各 file の詳細 TOML schema (counters / context / postprocess 等の構文) |
| [`docs/INLINE_TESTS.md`](docs/INLINE_TESTS.md) | `*.test.toml` の append-only 仕様 |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | 客観性能評価 (VOICEVOX engine 一致率 / 定期更新) |
| [`MAINTAINING.md`](MAINTAINING.md) | release / CI / upstream seed 再投入手順 |
| [`STATS.md`](STATS.md) | 件数 / カテゴリ別内訳 / サイズ (auto-gen) |
| [dict_browser (web)](https://ryuuneko1107.github.io/ja-furigana-dict/) | 全 entries 検索・フィルタ・漢字別 sweep 進捗 (auto-deploy、 dark mode 対応) |
| [`SECURITY.md`](SECURITY.md) | 脆弱性報告窓口 (engine 側に集約) |
| [`core/works/README.md`](core/works/README.md) | 作品単位辞書のサブポリシー |
| [`tests/corpus/README.md`](tests/corpus/README.md) | 回帰テスト用 corpus の運用 |

## AI ツールの活用について

開発側 (= maintainer) は **辞書 entry の追加・修正に AI (LLM) ツールを主力で活用**
しています。 具体的には:

- **読み候補の列挙・提案** (= 漢字 / 熟語に対して AI に読み候補を出させる)
- **例文の作成** (= `tests/corpus/*.toml` / `*.test.toml` の `input` フィールド)
- **副作用の洗い出し / 設計判断** (= 「この変更で何が壊れるか」 を AI 込みで検討)
- **コメント / doc の整形・推敲**

ただし **maintainer が必ず確認** することを前提運用にしています:

- **読み (= reading フィールド) は必ず辞書 / 公的資料で出典確認** (= 国語辞典 /
  漢和辞典 / 公式 site)、 AI 単独の出力は採用しない
- **`tools/validate.py` で TOML schema gate**
- **`tools/run_corpus.py` で regression test gate** (= 既存 case が壊れたら fail)
- **VOICEVOX engine 一致率で副作用検証** ([docs/EVALUATION.md](docs/EVALUATION.md))

外部 contributor の PR でも AI 利用は自由ですが、 同じく **出典確認 + regression
test 追加** をお願いしています (= AI が hallucination で生成した誤読を素通しさせない
ため、 validate + corpus regression + maintainer review の 3 段 gate で押さえます)。

## 利用側 (`furigana` から)

```sh
$ furigana dict pull               # 最新 release を取得 + ローカルに展開
$ furigana dict pull --version v2026.05.07     # 過去の特定 release に pin
```

default では `<furigana.exe と同じフォルダ>/data/` に展開される (portable 配置)。
`furigana serve` / `furigana lookup` / `furigana repl` が自動的にロード。
REPL の中からは `:pull` (or `pull`) でも同じ操作ができる。

## ライセンス

[MIT License](LICENSE)。 語彙辞書のエントリ自体に著作権を主張する根拠は薄いが、
ファイル形式・編集ガイドラインなどの contribution は MIT で公開する。

## コントリビュート

歓迎! 詳細は [CONTRIBUTING.md](CONTRIBUTING.md)。

最も多いケース (読みを 1 件追加):

1. カテゴリに合うファイル (例: 一般語なら [`core/jukugo/basic/general.toml`](core/jukugo/basic/general.toml)) を GitHub の Web UI で編集
2. 「Commit changes」→「Create pull request」
3. CI (TOML 構文チェック + カタカナ検証) が通れば maintainer が merge

Rust も Git のクローンも不要。
