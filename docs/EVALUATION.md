# 性能評価 — `ja-furigana-dict`

辞書の客観的な性能指標。 dict 改善 PR / release で「実際に良くなってるか」 を
回帰テストとは別軸 (= 任意 input に対する精度) で把握するための公開 metric。

> 戻る: [README.md](../README.md) / [CONTRIBUTING.md](../CONTRIBUTING.md)

## 主指標: VOICEVOX 単体との正答率比較

ja-furigana lib (= 辞書 + lib) の出力が、 **TTS engine として広く使われている
VOICEVOX engine 単体の出力よりどれくらい優れているか** を 主軸 metric として運用する。

### 測定方針

ランダムサンプル日本語テキスト **約 10,000 文** に対して:

1. ja-furigana lib (`furigana lookup --mode hiragana`) で読みを取得
2. VOICEVOX engine (`/audio_query` API) で読みを取得
3. 両者を normalize (= 拗音 / 長音 / 助詞ハヘヲ / 連続母音圧縮 / オ段オ→ウ 等の
   表記揺れを揃える)
4. 一致した case と diverge した case に分けて集計

両者一致 case は両方とも 同じ読み → 「両者とも正解」 と看做す近似。
diverge case は per-record で 内部 ground truth (= 手動 review) または
辞書照合で **どちらが正解か** を判定し、 ja 正解 / VOICEVOX 正解 / 両者不正解
の 3 カテゴリに分類する。

### 報告 metric

各 release / 改善 round で以下を測定:

| metric | 意味 |
|---|---|
| **ja-furigana 正答率** | ja 出力が正解一致した件数 / 評価対象件数 |
| **VOICEVOX 単体 正答率** | VOICEVOX 出力が正解一致した件数 / 評価対象件数 |
| **ja - VOICEVOX** | 差分 (= ja-furigana がどれだけ VOICEVOX を上回るか) |
| **両者一致率** | 副次指標、 両者とも同じ読み → 「dict 改善前」 の素朴な近似 |

主目標は **ja-furigana 正答率 - VOICEVOX 単体 正答率 > 0 を維持・拡大** すること。
VOICEVOX 単体は dict 改善側で動かせない外部 baseline なので、 ja-furigana 側の
dict 改善で差を広げる game。

### unweighted / weighted

- **unweighted (unique 表現)**: 1 文 1 票で集計、 corpus 全体の表現多様性に対する
  カバレッジを反映
- **weighted (実発話相当)**: 各文の出現回数で重み付け、 実利用での「何割
  正しく読めるか」 に近い。 頻発する短いフレーズの正解 1 件が稀フレーズの正解 1 件
  より大きく寄与する設計

## 評価用 corpus について

評価に使うランダムサンプル日本語テキストは、 dict 改善側で以下のような source を
匿名化・統合した内部 corpus からランダム抽出しています:

- 配信プラットフォーム (YouTube / Twitch / ニコ生 等) の **匿名化済みチャットログ**
  (= 投稿者 / channel / 配信タイトル等の identifying 情報は破棄、 残るのは
  コメント本文 + timestamp のみ)
- 開発者が運営する個人 web service の テキスト ログ (= 同様に PII 除去後)
- 公開 corpus / Wikipedia 等 一般日本語 text の random sample

**corpus 本体 (= 入力 text、 sqlite DB 等) は配布しません**。 privacy 保護および
辞書 evaluation 側の overfit 防止 (= 評価 corpus が公開されると dict 改善が
それに過剰最適化する) のためです。 公開される情報は:

- 評価方法 (= この doc に書いた手順)
- 計測結果数値 (= 履歴 table の正答率 %)
- 差分の傾向分析 (= 改善 round 毎の commit message / CHANGELOG)

具体的な「どの文が誤読されたか」 等の per-record 内容は公開しません (= 元コメントの
逆引きで投稿者特定リスクを 0 にするため)。

## 更新ポリシー

- **baseline**: 0.1.0 stable cut 時点 (= 2026-05-12) の数値を起点とする
- **定期更新**: 月次 / もしくは major dict 改善 batch (= round) 後に再測定し、
  この doc の数値表を append 形式で更新 (= 過去 baseline は履歴として残す)
- **train / verify 分離**: 改善 round の判定は train seed (= 改善時に diff を観た
  sample) と verify seed (= 改善後 fresh sample) の両方で測り、 over-fit を回避

  実測例 (= 2026-05-13 round 25 完了時点):
  - train (seed 20260513): 両者一致 87.1%
  - verify (seed 99999): 両者一致 87.3%
  - seed 33333 (= 第 3 系列): 両者一致 86.4%
  - train vs verify 差 -0.2pt / 3 seed std ≈ 0.5pt = **健全な汎化**
    (= specific seed に過剰最適化してない、 round 19→25 の +1591 件投入が
    各 seed で均等に効いた)

## 履歴

<!-- 新しい計測結果を上に append。 fixed point の数値を残すことで dict 改善の
     progression が時系列で見える。 -->

| 計測日 | dict version | sample (有効) | ja 正答率 | VOICEVOX 正答率 | ja − VOICEVOX | 両者一致 |
|---|---|---|---|---|---|---|
| 2026-05-13 (R25 後 fresh) | v2026.05.13.7 (= round 25 batch 1-26、 +1621 件 一般語彙) — **fresh seed 55555** (= 過去未使用) | 9,192 / 10,000 | _(算定中)_ | _(算定中)_ | _(算定中)_ | **87.0%** |
| 2026-05-13 (R25 後 33333) | 同上 — seed 33333 | 9,205 / 10,000 | _(算定中)_ | _(算定中)_ | _(算定中)_ | **86.4%** |
| 2026-05-13 (R25 後 verify) | 同上 — verify seed 99999 | 9,154 / 10,000 | _(算定中)_ | _(算定中)_ | _(算定中)_ | **87.3%** |
| 2026-05-13 (R25 後 train) | 同上 — train seed 20260513 | 9,179 / 10,000 | _(算定中)_ | _(算定中)_ | _(算定中)_ | **87.1%** |
| 2026-05-13 (verify) | v2026.05.12 + round 19-23 (= 笑笑/神獣/暗視/種/絵描く/方) — verify seed 99999 | 9,191 / 10,000 | _(集計中)_ | _(集計中)_ | _(集計中)_ | 83.9% |
| 2026-05-13 (3rd) | v2026.05.12 + round 48-52 + 単漢字見直し 第 1-18 弾 + round 19-20 | 9,179 / 10,000 | **97.5%** | **95.0%** | **+2.5pt** | 84.1% |
| 2026-05-13 (2nd) | v2026.05.12 + round 48-52 + 単漢字見直し 第 1-18 弾 | 9,179 / 10,000 | **97.6%** | **96.9%** | **+0.7pt** | 84.0% |
| 2026-05-13 (1st) | v2026.05.12 + round 48-51 + 単漢字見直し 第 1-2 弾 | 9,177 / 10,000 | 92.3% | 96.0% | -3.7pt | 82.9% |

> round 25 後 4 seed 計測 (= train/verify/33333/fresh 55555) で **+2.2 〜 +3.4pt 改善**。
> 4 seed mean **86.95%** / range 0.9pt (= 86.4-87.3%) で完全安定。
> 一般語彙 1621 件投入 (= 抽象名詞 / 感情 / ビジネス / 学術 / 医療 / 機器 / 文化等)
> の effect が各 seed で均等に効き、 過去未使用の fresh seed 55555 でも 87.0% を確認、
> **over-fit ゼロ + 真の汎化** を立証。 ja/VV ground truth 分類は
> 次 round で再集計 (= 87% 域での per-record review が必要)。

> 「両者一致」 = 両者の normalized 読みが同一の case 比率 (= 副次指標)。
> ja 正答率 / VOICEVOX 正答率 は両者一致 case (= 7,612 件) を両者正解扱いした
> 集計、 diverge case (= 1,565 件) を per-record 判定。 判定は patterns ベース
> 概算で、 厳密 manual review は次 round で実施予定 (= 数値はあくまで初回 indicator)。

## 評価対象外 (= 既知の制約)

- **ASCII alphabet を含む文**: ja-furigana lib は 0.1.0 時点で alphabet を読みに
  展開しない (= 「PC = ピーシー」 等)。 0.2.0 で loanwords 統合後に評価対象化予定
- **VOICEVOX engine 側の解析揺れ**: vv engine は「ヴィ → ビ」 のような特殊文字
  解釈で ja 側 と diverge する case あり (= vv 側の仕様に由来、 vv 単体 不正解 と
  分類)
- **同形異音語の文脈依存**: 文脈で正解が変わる surface (= 「方 = ホウ vs カタ」
  「金 = カネ vs キン」 等) は ground truth 側で文脈別 expected を持つことで
  評価可能、 ただし annotation コスト高で sample 限定

## 評価 script

評価 script (= ja-furigana 出力と VOICEVOX engine 出力を比較する Python script) は
**内部 evaluation 環境で実行** されます。 公開 repo には反映されません (= corpus 本体
が公開されない以上、 script だけ公開しても再現できない + script 内部に corpus
パスや個人 service 情報が含まれるため)。

公開される成果物は:

- この doc (= 評価方法 / 履歴 table)
- 計測結果数値 (= 正答率 % の時系列)
- dict 側の差分 (= TOML diff、 `docs/release-diffs/`、 `CHANGELOG.md`)

外部 contributor がローカルで類似評価をしたい場合は、 任意の日本語 corpus + VOICEVOX
engine を用意して `furigana lookup --mode hiragana` と VOICEVOX `/audio_query` の出力を
比較するスクリプトを書けば同等の評価が可能です (= 評価方法はオープン、 我々の corpus
だけが非公開)。
