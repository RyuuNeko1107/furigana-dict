# furigana-dict

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Japanese word dictionary for the [furigana](https://github.com/RyuuNeko1107/ja-furigana) library — open, community-maintained.

[`furigana`](https://github.com/RyuuNeko1107/ja-furigana) (フリガナ API + ライブラリ) で利用される
**語彙辞書** をホストする独立リポジトリ。読みの追加・修正は **TOML を編集して PR** だけで完結する。

> **Status**: v0.1.2 リリース済、master は v0.1.3 候補 — jukugo を **605 → 2,665** (約 +340%、24 ファイルに分割) に拡充、`postprocess.toml` 新設、
> ja-furigana 0.1.0-alpha.3 以降の本番 ryuuneko 互換 5 段階優先順位に対応した unihan 音読み正規化済。
> 人名・固有名詞は更に手動 PR で拡充歓迎。詳細は [STATS.md](STATS.md) / [CHANGELOG.md](CHANGELOG.md)。

---

## なぜ別リポジトリ?

**管理を楽にするため**。辞書エントリ数が増えると本体コードのリポジトリで一緒に管理するのが煩雑なので分けた。

`furigana dict pull` で GitHub Release から tar.gz を取得する仕組み。

## 構成

```
core/
├── jukugo/                    ← 熟語・固有名詞 + 自然 / 文化系 (24 ファイル / 計 2,665 件)
│   ├── general.toml           一般熟語 + 季節 / 行事 / 慣用句 (610)
│   ├── four_char.toml         四字熟語 (141、4 字 + 全部 CJK 漢字)
│   ├── personal_names.toml    人名: 戦国 / 平安 / 古典作家 + 異体字姓 (121)
│   ├── place_names.toml       地名: 47 都道府県 + 主要都市 + 駅 + 寺社仏閣 (163)
│   ├── proper_nouns.toml      大学 / 中央官庁 / 元号 / 歴史的事象 (116)
│   ├── animals.toml           動植物 / 魚介の難読 (62)
│   ├── foods.toml             食べ物 / 料理 (70)
│   ├── specialized.toml       医学 / 軍事 / 法学 / 学術 (75)
│   ├── body_parts.toml        体の部位 / 内臓 / 骨格 / 筋肉 (95)
│   ├── weather.toml           気象 / 天候 (69)
│   ├── colors.toml            色名 / 染色 / 模様 (62)
│   ├── arts.toml              古典芸能 / 武道 / 茶華香 / 工芸 (95)
│   ├── abstracts.toml         美意識 / 古典文学 / 仏教 / 思想 (86)
│   ├── vehicles.toml          乗り物 / 交通手段 (76)
│   ├── clothes.toml           衣服 / 装束 / アクセサリー (86)
│   ├── architecture.toml      建築 / 建造物 (84)
│   ├── literature.toml        古典文学 / 作品名 (73)
│   ├── science.toml           自然科学 (天文 / 物理 / 化学 / 生物 / 地学) (76)
│   ├── emotions.toml          感情 / 心理用語 (78)
│   ├── idioms.toml            慣用句 / ことわざ (79)
│   ├── politics.toml          政治 / 行政 (73)
│   ├── religions.toml         神道 / 仏教 / キリスト教 / 概念 (91)
│   ├── music.toml             音楽 / ジャンル / 楽典 / 西洋楽器 (107)
│   └── sports.toml            近代スポーツ / 球技 / 陸上水泳 (77)
├── unihan.toml                ← 単漢字フォールバック (43,749 字、音読み正規化済)
└── compat.toml                ← 異体字 → 標準字 (436)

rules/
├── counters/                  ← 助数詞ルール (7+ ファイル、自由分割)
│   ├── simple.toml             ・time.toml      ・people.toml
│   ├── objects.toml            ・places.toml    ・percent.toml ・recursive.toml
│   └── (time.toml に「年度 / 時間半」を含む)
├── context/                   ← 文脈依存読み
│   ├── numbers.toml           数字を含む慣用語句
│   ├── homonyms.toml          同形異音語 (上手 / 下手 / 十分 等)
│   └── special.toml           単漢字 default 上書き (能 / 差 / 約 / 本 / 円 等)
├── days.toml                  1〜31 日の特殊読み
├── scales.toml                大数 (万 / 億 / 兆 / 京…)
├── units.toml                 単位 (km / kg / mL …) + 円 / % (N+漢字単位 連結用)
├── symbols.toml               記号 (+/-/% / 〜→から / ・→ナカグロ 等)
├── latin.toml                 ラテン文字
├── numeric_phrases.toml       数字を含む例外語句 (二十歳→ハタチ + 百個 / 千個 等)
└── postprocess.toml           ★後処理 regex 置換 (本番 Step 7 互換、0.1.2 新設)
```

> 配布側 (`furigana dict pull` で展開後) は `data/` 1 階層に flat に並ぶ。
> repo 内の `core/` `rules/` の階層分けは PR レビュー上の分類のためで、エンジン側は
> ファイル名と中身の構造で自動振り分けする。

## TOML 形式

すべて以下の形式:

```toml
[entries]
"灰桜" = "ハイザクラ"
"黎明" = "レイメイ"
"明後日" = "アサッテ"
```

- key: 表層形 (漢字を含む文字列)
- value: ひらがな または 全角カタカナ の読み (慣習: 訓=ひら / 音=カタ)
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
