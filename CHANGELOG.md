# Changelog

`ja-furigana-dict` (語彙辞書 + ルールデータ) の変更履歴。
[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) 形式。

利用側の `ja-furigana-cli` は `furigana dict pull --version vX.Y.Z` でピン留め可能。
未指定時は GitHub Releases の latest を自動取得。

## [Unreleased]

(次の release で入れる変更をここに追記)

## [0.1.3] - 2026-05-07

語彙辞書の継続拡充 (jukugo 1,832 → 4,351、約 +138%、24 ファイル分類維持) +
作品単位辞書ディレクトリ `core/works/` 新設 + STATS.md 自動生成基盤の整備。
ja-furigana 0.1.0-alpha.6 (loader 全階層再帰対応) とペアの release。

### Added (語彙辞書 +2,591 件 / works 72 件)

- **ラウンド 7-10 で jukugo 24 ファイル全てを大幅拡充**:
  - 平均 +108 件 / ファイル、最大 general.toml が 610 → 739 (+129)
  - 詳細は [STATS.md](STATS.md) を参照 (各ファイルの最新件数 / サイズが自動反映)
- **`core/works/` ディレクトリ新設 (作品単位 1 ファイル)**:
  - サブポリシー: 公式読みのみ採録、出典 comment 必須、二次創作読み禁止
  - `core/works/README.md` で運用ルール文書化
  - `core/works/game/touhou.toml` (東方Project, 72 件) を seed として収録
- **ja-furigana 0.1.0-alpha.6 の loader 全階層再帰対応**:
  - `core/works/<medium>/<title>.toml` のような任意深度の構造を許容
  - dict 側 v0.1.2 の `core/jukugo/*.toml` 1 階層構造は新 loader でも互換

### Changed (用途説明を [meta] description に移行)

各 TOML ファイル先頭に `[meta] description = "..."` を追加。
`tools/regen_stats.py` がこれを読んで STATS.md の用途列を自動生成する仕組みに。
README.md の構造ブロック (24 ファイル分の手書きツリー) は廃止して
STATS.md ポインタ化 (更新が手動で面倒だったため)。

### Added (CI / 開発基盤)

- **`tools/regen_stats.py`**: STATS.md のサマリ / core / rules テーブルを自動再生成
  - マーカー (`<!-- AUTO-GENERATED:* -->`) で囲んだ範囲だけ書き換え
  - サマリは「単漢字 / 熟語 / 作品造語 / 異体字 / ルール」5 区分表示
- **`.github/workflows/validate.yml` に stats-drift ジョブ追加**:
  - regen 後 `git diff --exit-code STATS.md` が non-zero なら CI fail
  - TOML 編集後の re-generation 忘れを検出
- **`tools/validate.py` 全階層対応**: `core/jukugo/**/*.toml` および
  `core/works/**/*.toml` を再帰スキャン (ja-furigana 0.1.0-alpha.6 loader と
  挙動を揃える)

### Fixed (単漢字混入の自動検出 + 一掃)

ラウンド 7-9 で agent 拡充中に jukugo に紛れ込んだ単漢字 entry 22 件を
全 jukugo ファイルから除去 (validate.py が cross-file 重複として検出済、
これらは unihan.toml に既存だが jukugo は ≥2 字ルールに反するため不要)。

## [0.1.2] - 2026-05-06

語彙辞書の大規模拡充 (jukugo 605 → 1,163、約 +90%) + ルールエンジン側との連動。
本番 ryuuneko.com の公開フリガナ API パイプラインに合わせて辞書 / context / units の
構造を整え、ja-furigana lib (0.1.0-alpha.3) と協調動作する。

### Added (語彙辞書 +560 件)

- **新規ファイル 8 つ** (jukugo 細分化):
  - `core/jukugo/animals.toml` (動植物 / 魚介、36 件)
  - `core/jukugo/foods.toml` (食べ物 / 料理、26 件)
  - `core/jukugo/specialized.toml` (医学 / 軍事 / 法学 / 学術、35 件 + 駆逐艦 / 戦艦 等)
  - `core/jukugo/body_parts.toml` (体の部位 / 内臓、24 件)
  - `core/jukugo/weather.toml` (気象 / 天候、40 件)
  - `core/jukugo/colors.toml` (色名 / 染色 / 模様、30 件)
  - `core/jukugo/arts.toml` (楽器 / 古典芸能 / 武道 / 茶華香、35 件)
  - `core/jukugo/abstracts.toml` (美意識 / 古典文学 / 仏教 / 思想、29 件)
- **既存ファイル拡充**:
  - `general.toml`: +66 (季節 / 二十四節気 / 年中行事 / 慣用句 + 検証ループ補強)
  - `personal_names.toml`: 0 → 71 (戦国 / 平安 / 古典作家 + 異体字姓)
  - `place_names.toml`: 5 → 109 (47 都道府県 + 主要都市 + 駅 + 寺社仏閣 + 観光地)
  - `proper_nouns.toml`: 0 → 67 (大学 / 中央官庁 / 元号 / 歴史的事象)
- `core/unihan.toml` の override に「魚=サカナ」「魚=サカナ」を追加（旧 unihan の
  「なまうお」を上書き）。
- `tests/corpus/` を新設 (`should_read.toml` / `should_not_read_yet.toml` /
  `out_of_scope.toml`)。`tools/run_corpus.py` で回帰テスト可能。

### Changed (本番 ryuuneko 互換のため、単漢字 unihan を音読みに正規化)

ja-furigana 0.1.0-alpha.3 で resolve_reading が
`context rule → jukugo → Lindera reading → unihan` の本番互換 5 段階優先順位
になったのに合わせて、unihan.toml の **動詞活用形 / 古訓 / 訓読みを音読みに
正規化** (16 文字):

- 能 (あたう → ノウ)、差 (さす → サ)、約 (つづまやか → ヤク)、本 (もと → ホン)、
  率 (ひきいる → リツ)、半 (なかば → ハン)、屋 (オク → ヤ)、者 (もの → シャ)、
  見 (みる → ミ、Lindera 動詞「見る」連用形「見」surface 用)、面 (オモテ → メン)、
  階 (きざはし → カイ)、円 (まるい → エン)、度 (たび → ド)、札 (ふだ → サツ)、
  史 (ふびと → シ)、間 (あいだ → カン)。

### Added (ルール / 後処理)

- `rules/context/special.toml` に検証ループ補強の default rule 一式を追加:
  - 能 / 約 / 差 / 本 / 率 / 半 / 屋 / 者 / 市場 / 間 / 円 (default 音読み固定)。
- `rules/context/homonyms.toml` の「上手」rule に `next_eq = "から"` →
  カミテ の match を追加 (舞台用語)。
- `rules/context/numbers.toml` の「一日」rule に `default = "イチニチ"` を追加
  (期間文脈の fallback)。
- `rules/units.toml` に「円」「%」を追加 (NumberChunker の N+漢字単位 連結用)。
- `rules/counters/time.toml` に「年度 (ネンド)」「時間半 (ジカンハン)」「年」「時間」
  を新設。
- `rules/numeric_phrases.toml` に「百個 / 千個 / 百本 / 千本 / 百匹 / 百冊」追加。
- `rules/symbols.toml` に「〜 / ~ → から」「・ → ナカグロ」「※ → コメ」追加。
- **`rules/postprocess.toml`** を新設 (本番 Step 7 互換): regex ベースの mode 別
  置換ルール。初期 rule として「ジュウパー → ジュッパー」(50% 促音化補正) を投入。

### Validation

- `tools/validate.py`: 全 `*.toml` 構文 + cross-file 重複 + カナ範囲チェック OK。
- `tests/corpus/should_read.toml` の各 case を `tools/run_corpus.py` で回帰検証
  可能 (CI gate にも組み込み予定)。
- ja-furigana 側で実例文 75 件を回帰し、合計 75/75 (100%) で正解を確認。

### Stats (master HEAD 時点)

- 語彙辞書 (`core/`): 45,328 entries (~865 KB)
- エンジンルール (`rules/`): ~260 entries (~19 KB) + postprocess.toml (新規)
- 配布 tarball: ~240 KB (gzip 圧縮後、推定)

## [0.1.1] - 2026-05-05

### Added
- `core/jukugo/four_char.toml` を新設し、`general.toml` から **四字熟語 58 件** を分離
  (一期一会 / 四面楚歌 / 優柔不断 等)。判定: 4 字 + 全部 CJK 漢字。
- `tools/classify_jukugo.py` を拡張: `looks_like_four_char` で機械的に振り分け、
  `--apply` で `general.toml` / `four_char.toml` / `place_names.toml` を一括書き換え。
- `CONTRIBUTING.md` に **`rules/context/` 書き方ガイド** を追加: 8 つの match 条件
  (`prev_eq` / `prev_ends_with_any` / `prev_ends_with_month` / `next_eq` /
  `next_starts_with` / `next_starts_with_any` / `next_starts_with_digit` /
  `next_next_starts_with_any` / `pos_eq`) を意味と例で表形式に明示。
- `CONTRIBUTING.md` に **「ファイルが大きくなりすぎたら」** セクションを追加。
  `core/jukugo/` `rules/counters/` `rules/context/` は同名サブディレクトリ配下を
  自動 merge する仕組みが lib loader にあることを明示し、分割運用ガイドを記載。

### Changed
- `core/jukugo/general.toml`: 600 → 542 entries (四字熟語 58 件を `four_char.toml` へ移動)。
- jukugo 全体は 605 entries で変わらず (general 542 + four_char 58 + place_names 5 +
  personal_names 0 + proper_nouns 0)。
- README の status を「初期 seed 投入中、空に近い」から実態 (44k+ entries) に更新。

## [0.1.0] - 2026-05-05

初回 GitHub Release。本番 ryuuneko.com から seed 投入完了版。

### Added
- **本番 ryuuneko.com から seed 投入**:
  - `core/unihan.toml`: 単漢字フォールバック **43,749 字**
    (本番 override 14 件を含む: 中=ジュウ / 乙=オツ / 午=ヒル / 専=せん / 拍=ウ /
     木=キ / 柵=サク / 踵=カカト / 面=オモテ / 頬=ホホ / 𡚴=セイ / 𡱖=つび /
     𡸴=ロウ / 𢈘=ロク)。
  - `core/jukugo/general.toml`: 一般熟語 600 件 (4 字+漢字の四字熟語 58 件含む、
    後の 0.1.1 で `four_char.toml` に分離)。
  - `core/jukugo/place_names.toml`: 地名 5 件 (北海道 / 吉祥寺 / 秋葉原 / 表参道 /
    鹿児島 — 機械振り分け済み)。
  - `core/compat.toml`: 異体字マップ 436 件。
- `tools/import_from_production.py`: 本番 PostgreSQL の `furigana_*` テーブルを
  CSV export → TOML 化 + 本番優先 merge する maintainer 専用ツール。
- `tools/classify_jukugo.py` (初版): 単漢字を `jukugo` から削除して `unihan` に
  統合、地名接尾語で `place_names.toml` へ機械振り分け。
- Release workflow に `core/` と `rules/` 両方を archive に含める修正。

### Changed
- `tools/validate.py` を kana 全般 (ひらがな + 全角カタカナ) 許容に緩和
  (本番データの慣習: 訓読み = ひらがな / 音読み = カタカナ に追従)。

## [一覧]

[Unreleased]: https://github.com/RyuuNeko1107/ja-furigana-dict/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/RyuuNeko1107/ja-furigana-dict/releases/tag/v0.1.2
[0.1.1]: https://github.com/RyuuNeko1107/ja-furigana-dict/releases/tag/v0.1.1
[0.1.0]: https://github.com/RyuuNeko1107/ja-furigana-dict/releases/tag/v0.1.0
