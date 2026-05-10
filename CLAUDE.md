# ja-furigana-dict (TOML 辞書)

ja-furigana lib 用の TOML 辞書 + 校正ルール data repo。

- **GitHub**: <https://github.com/RyuuNeko1107/ja-furigana-dict>
- **License**: CC BY-SA 4.0 (data) + Apache-2.0 (tools/scripts)
- **release 形式**: GitHub Releases tar.gz、 lib 側 `furigana dict pull` で取得
- **現 release**: `v2026.05.09` (CalVer)

## 構成

```
core/                — 単語辞書 (entry data、 役割別 sub-dir)
├── jukugo/          — 熟語 (24 カテゴリ、 32 file)
├── unihan/          — 単漢字 fallback (5 file)
├── works/           — 作品固有名詞 (game / literature)
├── loanwords/       — 外来語 (1 file)
├── single_overrides.toml  — 1 字 surface override (Issue #15)
└── compat.toml      — 異体字 → 標準字 mapping

rules/               — 校正ルール (data + 動的合成)
├── counters/        — 助数詞 (時間系 / 物体系 等、 13 file)
├── context/         — 文脈依存読み (4 file、 alpha.10 で entry inline に migration 予定)
├── numbers/         — 数字読み / スケール / 単位
├── text/            — 記号 / ラテン文字 / 後処理
└── *.toml           — days / scales / units / symbols / latin / numeric_phrases / postprocess

tests/
└── corpus/
    └── should_read.toml  — 回帰テスト (~50+ case、 alpha.10 で 108+ に拡充予定)

tools/
├── validate.py      — TOML 構文 + 読み形式 + cross-file 重複検出 (CI gate)
├── run_corpus.py    — corpus regression runner
├── test_inline_rules.py  — *.test.toml inline test 実行
├── regen_stats.py   — STATS.md 自動生成
├── list_dups.py     — cross-file 重複検出
├── dedup_compat.py  — 異体字 mapping 経由 dead code 削除
├── add_role_tags.py — 全 TOML に [meta] role bulk 追加 (1 回限り migration 用)
└── migrate_v2.py — `[meta] schema_version = "2"` bulk 追加 (★A1b、 alpha.10、 1 回限り)
```

## 既存 [meta] role 値

loader が role 駆動 dispatch する tag。 各 TOML 冒頭に `[meta] role = "..."` を書く:

`jukugo` / `unihan` / `works` / `loanwords` / `single_overrides` / `compat` /
`counters` / `context` / `days` / `scales` / `units` / `symbols` /
`latin` / `numeric_phrases` / `postprocess`

## alpha.10〜alpha.11 期 dict 側 mechanical 完了 (★A1b / ★A2)

- ✅ **schema_version 必須化** (★A1b、 alpha.10 coordinated): 全 dict / rule TOML
  54 file に `[meta] schema_version = "2"` を bulk 適用
  (`tools/migrate_v2.py --apply`)、 `validate.py` で gate 化
- ✅ **rules/context → entry inline match 機械変換** (★A2、 alpha.11):
  `tools/migrate_v2_context.py` (= staging 生成) + `tools/merge_migrated_context.py`
  (= 実 core/ に surgical merge) で 31 既存 entry を Detailed 化 + 21 missing
  surface を catch-all 配置 (general.toml)、 5 件 POS-only match は drop (= default
  reading で fallback、 redundant)
- ✅ **single_overrides → [[kanji]] block 機械変換** (★A2、 alpha.11):
  `tools/migrate_kanji_format.py` で `core/kanji/overrides.toml` 生成、 旧
  `single_overrides.toml` は Strict engine 後方互換のため保持
- ✅ **validate.py 拡張**: detailed entry / `[[kanji]]` block / bracket syntax
  check 対応
- ✅ **docs/SCHEMA.md / CONTRIBUTING.md update**: 新 format / matcher / bracket
  notation を contributor 向けに整備

## alpha.11+ 期 dict 側 残作業 (= 人手 PR series、 multi-week 規模)

mechanical 機械変換 phase 完了後の継続作業 (= LLM 1 session で完結しない、
maintainer / community PR で漸進):

- 5 件 POS-only rule の literal 列挙化 (= 上手 / 下手 / 十分 / 一月 / 二月、
  ただし default reading で実用上動くため非緊急)
- 21 件 missing surface の sub-dir 再 triage (= 現在 general.toml catch-all)
- 重複 / 古い / 出典なし entry の purge (= source attribution data 不在で慎重要)
- `core/jukugo/` 24 カテゴリ再分類 (= 5024 entries の review、 multi-week)
- `core/works/` / `core/loanwords/` 整理確認

## lib coordinated で残る作業

- lib `DictBridgeProvider` integration: Smart engine が `lookup_rich` で取った
  `[[match]]` block を Viterbi DP に統合 (= alpha.12+ で実装)
- lib `[[kanji]]` block loader: `core/kanji/*.toml` を読み込んで KanjiProvider
  で provide (= 上記と coordinated)
- 0.1.0-rc1 で Smart default 切替後、 dict から `rules/context/` /
  `single_overrides.toml` を削除 (= source of truth 一本化)

## 新 format 例 (alpha.10 投入後)

### entry 省略形 (大半の entry はこのまま、 50k+ 既存 entry が無修正で動く)

```toml
[meta]
schema_version = "2"
role = "entries"

[entries]
"魔理沙" = "マリサ"
"紅魔館" = "コウマカン"
```

### entry 完全形 (文脈分岐が要る entry のみ)

```toml
[entries]
"上手" = "ジョウズ"

[[entries."上手".match]]
next_eq = "から"
reading = "カミテ"

[[entries."上手".match]]
prev_eq = "下"
reading = "シタテ"
```

### `[[kanji]]` block (= 旧 single_overrides + unihan 統合)

```toml
[meta]
schema_version = "2"
role = "kanji"

[[kanji]]
char = "生"
default = "セイ"

[[kanji.match]]
next_eq = "じる"
reading = "ショウ"

[[kanji.match]]
prev_char_type = "ひらがな"
reading = "ナマ"
```

## matcher vocabulary (品詞 不採用)

| 軸 | prev 側 | next 側 | 値型 |
|---|---|---|---|
| literal 一致 | `prev_eq` | `next_eq` | string |
| literal いずれか | `prev_eq_any` | `next_eq_any` | string array |
| 文字種 | `prev_char_type` | `next_char_type` | "漢字" / "ひらがな" / "カタカナ" / "英数" / "記号" |

**`prev_pos` / `next_pos` (Lindera 品詞) は採用しない** (Lindera 撤廃路線)。

## bracket notation (= 0.1.0 から書ける、 lib は strip / 無視、 0.2.0 で活用)

```toml
[entries]
"上手" = "ジョ]ウズ"     # 1型 accent (頭高)
"霧雨" = "キ[リサメ"     # 0型 (平板)

[entries."橋"]
reading = "ハ]シ"

[[entries."橋".match]]
prev_eq = "鉄"
reading = "テッキョウ"   # match 候補も bracket 付きで書ける
```

## よく使うコマンド

```powershell
# validate (CI gate)
python tools/validate.py

# corpus regression test (= should_read.toml + should_read/ 配下)
python tools/run_corpus.py

# inline rule tests (= *.test.toml)
python tools/test_inline_rules.py

# STATS.md 自動再生成
python tools/regen_stats.py

# cross-file 重複検出
python tools/list_dups.py
```

## 主要 doc

- `docs/SCHEMA.md` — TOML スキーマ詳細 (= alpha.10 で全面 update 予定)
- `docs/INLINE_TESTS.md` — *.test.toml inline test 規約
- `STATS.md` / `STATS_DUPS.md` — auto-gen (= 各 PR の STATS verify が CI で走る)

## 注意点

- **daily-release.yml schedule 停止中** (commit `e1e8d0b`、 2026-05-09 から)、 stable cut 後に再開判断
- **release pace は Hybrid**: lib coordinated は SemVer (`v0.1.0` 等)、 daily-release / 修正は CalVer (`v2026.07.01` 等)
- **Immutable Releases 設定 OFF** (alpha.7 経緯)、 stable cut 時に ON 推奨
- **CI auto-merge**: dependabot PR + 特定 label PR が auto-merge 対象
- **author email**: `mail@ryuuneko.com` (個人 gmail を直書きしない方針)
