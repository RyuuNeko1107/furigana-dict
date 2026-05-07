# Test Corpus

辞書 / ルールの **期待動作スナップショット**。OSS 辞書を更新するときに「これは
読める / これは今は読めない / これは仕様上諦める」を切り分けて、回帰を起こさない
ようにするための材料です。

将来的に CI で自動回帰チェックする想定 (今は人が眺める材料)。

## ファイル

- [`should_read.toml`](./should_read.toml) — **読めるはず**: 辞書 / ルールが正しく
  動けば必ず正しい読みが返る期待値。これが壊れたら何かを失った。
- [`should_not_read_yet.toml`](./should_not_read_yet.toml) — **今はまだ読めない**:
  辞書追加 PR で改善できるもの。「ここに書かれた語が読めるようになった!」が
  contributors の達成感。
- [`out_of_scope.toml`](./out_of_scope.toml) — **仕様上諦める**: 高度な文脈推論や
  古文・方言など、機械学習なしのこのエンジンの範囲外。期待しない。

## ja-furigana 側 `tools/check_samples.txt` との関係

検証ループ (誤読の探索 → 修正) のワークフロー:

```
[ja-furigana/tools/check_samples.txt]   ← 探索の場 (1 回限りで使い捨て可)
       ↓ 試す
   誤読を発見 → lib / dict を修正
       ↓ 全部 OK になった例文
[ja-furigana-dict/tests/corpus/should_read.toml]   ← アーカイブ + 回帰防止
       ↓
   CI (`tools/run_corpus.py` ベース) で常時検証 → regression したら fail
```

つまり `should_read.toml` は **過去に直した誤読の永久保存場所**。CI で守ることで
「lib / dict を改修したらまたあの誤読が復活した」を防ぐ。`check_samples.txt` の方は
新しい検証バッチに置き換える前提で、その時々の探索用 (アーカイブはここの should_read 側に promote する)。

## 形式

各ファイルは以下の TOML 形式:

```toml
[[case]]
input = "灰桜の散る道"
mode = "ruby"   # ruby / hiragana / tts / romaji のいずれか
expected = "{灰桜|はいざくら}の{散る|ちる}{道|みち}"
note = "桜の品種名、辞書 hit"

[[case]]
input = "灰桜の散る道"
mode = "hiragana"
expected = "はいざくらのちるみち"
```

`should_not_read_yet.toml` / `out_of_scope.toml` では `expected` の代わりに
`expected_failure_reason` を書きます (どう間違うか、なぜ正解にならないか)。

## 自動チェック (将来)

```sh
# ja-furigana CLI を使って各 case を検証する script (未実装)
python3 tools/run_corpus.py tests/corpus/should_read.toml
```

PR 受付時に CI で `should_read.toml` の全 case が pass することを保証する
仕組みを将来導入予定。
