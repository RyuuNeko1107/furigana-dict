# core/works — 作品単位辞書

特定の作品 (アニメ / ゲーム / ライトノベル / 漫画) の固有名詞・造語を
**1 作品 = 1 ファイル** で集めるディレクトリ。
ja-furigana 0.1.0-alpha.6 以降の loader が **全階層再帰** で `*.toml` を
拾うため、`core/works/<medium>/<title>.toml` の構造で配置すれば
そのまま jukugo (≥2 字 surface 固定読み) として lookup される。

## なぜ jukugo と分けるのか

- 一般語 (`core/jukugo/general.toml` 等) と作品造語が混ざると
  「同じ表層が違う読み」のとき commit log で衝突が見えにくくなる
- 作品ごとに公式読みのソース (公式サイト / 作者監修書籍) が違うので、
  **ファイル先頭 comment に出典を書く** 運用にしたい
- 「自分の好きな作品だけロードしたい」需要が出たら、将来の loader 拡張で
  `load_filter: ["works/game/touhou", "works/anime/madoka"]` 等で対応しやすい

## サブポリシー (works/ の追加で必須)

`core/jukugo/*` の seed 方針は「現代の私人 / 私企業 / アニメ作品 / 商標は
seed しない (誤読リスク回避)」だった。works/ ではこれを部分的に緩和する代わりに、
以下のサブルールを **必ず** 守る:

1. **公式読みが確定しているもののみ** seed
   - 作者公式 / 公式サイト / 公式書籍 / 公式 wiki に明記された読みのみ
   - ファン推測 / 同人解釈 / 派生作品の独自設定は **不可**
2. **ファイル先頭に出典を必ず書く**
   - 例: `# 出典: 上海アリス幻樂団 公式 (https://...)`、`# 出典: TVアニメ公式設定資料集`
3. **二次創作の独自読みは禁止**
   - 例えば公式が読みを与えていない脇役の「ファン推奨読み」は不可
4. **商標問題のあるエントリは除外**
   - 作品タイトルや主要ブランド名そのものは引用範囲だが、商標的にグレーな
     コラボ商品名 / 二次商標は入れない
5. **1 作品 = 1 ファイル**
   - `core/works/<medium>/<title>.toml` の構造を守る
   - 作品が大きくて分けたい場合は `core/works/<medium>/<title>/{characters,locations,terms}.toml`
     のように 1 階層下げる (loader は再帰なのでロードされる)
6. **TOML 形式は jukugo と同じ**
   ```toml
   [entries]
   "博麗霊夢" = "ハクレイレイム"
   ```
7. **単漢字 (1 文字) は jukugo と同様に絶対に入れない**
   - validate.py が cross-file 重複として検出して fail させる

## 現在の収録作品

| ファイル | 作品 | 出典 |
|---|---|---|
| [`game/touhou.toml`](game/touhou.toml) | 東方Project | 上海アリス幻樂団 公式 |

## 追加要望

PR 歓迎。新規作品を入れる場合は:
1. 上記サブポリシー全部に該当するか確認
2. ファイル先頭に出典 URL を書く
3. `tools/regen_stats.py` の `DESCRIPTIONS` に
   `"core/works/<medium>/<title>.toml": "<作品名>: <概要>"` を追加
4. PR description に「公式読みのソース」を明記
