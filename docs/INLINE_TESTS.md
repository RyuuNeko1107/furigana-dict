# Inline test (`*.test.toml`)

各 dict / rule TOML に対して、 同 dir に **`<name>.test.toml`** を作って `[[test]]`
を書くと、 CI で binary に input を流して expected (hiragana mode) と一致するか
自動検証される。

> 戻る: [CONTRIBUTING.md](../CONTRIBUTING.md)
> 関連: [SCHEMA.md](./SCHEMA.md) (各 file の TOML schema)

## 位置づけ

- **inline test (本書)** = file 単位の「この file が担当する変換」 ロック
- **corpus regression** ([`tests/corpus/should_read.toml`](../tests/corpus/should_read.toml))
  = repo 全体の最終ロック

両者は補完関係。 個々の file 編集 PR では inline test を、 横断的な誤読修正 PR で
は corpus を主に追加する。

## 書き方

```toml
# rules/numbers/counters/objects.test.toml (rules/numbers/counters/objects.toml の隣接 test)

# ─── 本 ────────────────────────────────────────────
[[test]]
input = "1本"
expected = "いっぽん"

[[test]]
input = "3本"
expected = "さんぼん"

# ─── 匹 ────────────────────────────────────────────
[[test]]
input = "1匹"
expected = "いっぴき"
```

### 推奨: 1 例文 → 複数 target ([[test.targets]])

corpus と同じく、 **1 例文の中で複数の対象語句を同時に検証** する形式が推奨:

```toml
[[test]]
input = "3本の傘と5匹の猫"
expected = "さんぼんのかさとごひきのねこ"
note = "助数詞 2 種 (本 / 匹) を 1 例文で同時 lock"

[[test.targets]]
surface = "3本"
reading = "さんぼん"

[[test.targets]]
surface = "5匹"
reading = "ごひき"
```

runner (`tools/test_inline_rules.py`) は full match (`expected` と完全一致) と
target match (各 `surface` の `reading` が output 中に含まれるか substring check) の
両方を pass で初めて test 通過。 失敗時は full / target どちらが原因かを別表示する。

**従来形式 (`targets` 無し) も backward compat で動作する** ので、 既存 test の
migration は急がなくて OK。 新規追加時に新形式で書くと、 「この file が何を lock
しているか」 が宣言的に分かりやすくなる。

## ルール (重要)

- **`[[test]]` block 形式** (1 case 3 行、 縦書きで読みやすい)。 inline-table
  `test = [{...}, {...}]` も TOML semantic 上同じ意味で受け付けられるが、
  block 形式の方が新 case を追加しやすく、 input / expected が長文でも書きやすい
- **末尾追記が基本**、 関連 case 同士は `# ─── タイトル ──` コメントでグループ化
  すると見通し良い
- **append-only**: 既存 case の **削除は禁止** (= regression 検出のロックなので
  削除すると過去の不具合が再発しうる)。 reading が変わった場合は新 case を追加して、
  古い case は残す方針 (= corpus と同じく「過去通せたものは通し続ける」)
  - **CI で強制**: `validate.yml` の `test-append-only` job が PR trigger で
    `tools/check_test_append_only.py` を走らせ、 PR base との `*.test.toml`
    比較で case 削除 / reading 変更があれば fail する

### どうしても無効化したい場合

削除ではなく **コメント化 + DISABLED tag** で抜け道を残せる (file に痕跡 + 理由が残る
ので後で復元可)。 PR review で reason の妥当性を確認する運用:

```toml
# DISABLED: 1個 -- kana_replace logic 変更で「いっこ」 → 「イチコ」、 一旦無効化
# [[test]]
# input = "1個"
# expected = "いっこ"
```

`# DISABLED: <input> -- <reason>` 形式 (区切りは `--` `—` `―` のいずれか) を file 内の
どこかに 1 行入れれば、 その input を持つ case の削除は CI で許容される。

順序は問わない (TOML array なので並べ替えは不要、 PR で挿入位置を調整しなくて OK)。

## なぜ別 file (`*.test.toml`)?

- **release tar から除外**: `release.yml` の tar 化で `--exclude='*.test.toml'` →
  配布物 (`furigana-dict-<TAG>.tar.gz`) には含まれない、 利用者の disk を消費しない
- **lib runtime memory にも載らない**: lib loader (`Dict::from_toml_dir` /
  `Loanwords::from_toml_dir` / rules loader) が file 名 match (`*.test.toml`) で
  skip → parse すらされない、 entries にも tokens にも乗らない
- **merge 競合最小化**: rule 編集 PR は本体 file、 test 追加 PR は test file、
  別 path で衝突しにくい
- **隣接配置で発見容易**: `objects.toml` と `objects.test.toml` が同 dir に並ぶので
  contributor が「rule + test」 ペアで認知できる

## 走らせ方 (local)

```sh
python tools/test_inline_rules.py \
  --binary path/to/furigana \
  --data-dir path/to/data-dir
```

CI では ja-furigana 側 `ci.yml` の corpus regression job 内で
`tools/test_inline_rules.py` を併走。 `*.test.toml` 0 件なら skip、 contributor は
書きたい file から書ける緩い制約。

## `*.test.toml` を置ける場所

- `core/jukugo/<genre>/<file>.test.toml`
- `core/works/<medium>/<title>.test.toml`
- `core/loanwords/<file>.test.toml`
- `core/<single_overrides|compat>.test.toml`
- `rules/<file>.test.toml` (counters / context / postprocess / 等含む全 file)
