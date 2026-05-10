# RECIPES — よくある書き方の copy-paste 集

`ja-furigana-dict` でやりたいことを **「○○したい → こう書く」** の形で並べた
practical guide。 spec の正確な記述は [SCHEMA.md](SCHEMA.md)、 こちらは **動く例** を
重視する。

> 各レシピは `core/jukugo/<genre>/<file>.toml` 等にそのまま paste できる形。
> 既存 entry と重複させないこと、 50 音順を維持すること は前提。
>
> 困ったら GitHub Issue / PR で 「こういう読み分けをやりたい」 と書いて
> 質問してくれて構わない。 spec に書きにくい例があれば本書に追加する。

## index

- [単純な読み追加 (99% のケース)](#単純な読み追加-99-のケース)
- [同形異音語 (= 文脈で読みが変わる)](#同形異音語--文脈で読みが変わる)
- [助詞 / 文末で読み分け](#助詞--文末で読み分け)
- [前後 token の prefix / suffix で分岐](#前後-token-の-prefix--suffix-で分岐)
- [文字種 (漢字 / ひらがな / 英数) で分岐](#文字種-漢字--ひらがな--英数-で分岐)
- [月名 / 数字の後で分岐](#月名--数字の後で分岐)
- [単漢字に default + 文脈分岐を持たせる](#単漢字に-default--文脈分岐を持たせる)
- [助数詞 (= 数字 + 〜) を追加したい](#助数詞--数字--を追加したい)
- [外来語 (英字 surface) を追加](#外来語-英字-surface-を追加)
- [作品造語 (アニメ / ゲーム 固有読み)](#作品造語-アニメ--ゲーム-固有読み)
- [intonation (アクセント) を書きたい](#intonation-アクセント-を書きたい-02-で-activate)
- [アンチパターン / よくある間違い](#アンチパターン--よくある間違い)

---

## 単純な読み追加 (99% のケース)

**やりたい**: 「魔理沙」 → 「マリサ」 で常に変換したい。 文脈で変わらない。

**配置**: `core/jukugo/<genre>/<file>.toml` (= 適切な genre を [STATS.md](../STATS.md#熟語) から選ぶ)

```toml
[entries]
"魔理沙" = "マリサ"
```

**ポイント**: 99% の entry はこれで終わる。 inline match は context 必要時のみ。

---

## 同形異音語 (= 文脈で読みが変わる)

**やりたい**: 「上手」 を default 「ジョウズ」、 「上手から」 のときだけ 「カミテ」。

**配置**: 既存 entry と同じ file (= ここでは `core/jukugo/basic/general.toml`)

```toml
[entries."上手"]
reading = "ジョウズ"           # default (= 全 match miss 時の fallback)

[[entries."上手".match]]
next_eq = "から"               # 「上手から」
reading = "カミテ"
```

**ポイント**:
- `[entries."X"]` で書くのは **文脈分岐がある entry のみ**、 simple form と混在 OK
- `reading` は default、 必須 (= 不在は parse error)
- `[[match]]` block は **TOML 出現順で第一 hit 採用** (= 早い 1 件で確定)
- 同 block 内の condition 複数は **AND** (= 全 hit で match 成立)

**応用**: 複数文脈で同 reading に切り替えたい場合 → match を増やす:

```toml
[entries."人気"]
reading = "ニンキ"

[[entries."人気".match]]
next_eq = "が"
next2_starts_any = ["な", "無"]   # 「人気が無い / 人気がない」
reading = "ヒトケ"

[[entries."人気".match]]
next_eq = "の"
next2_starts_any = ["な", "無"]   # 「人気の無い / 人気のない」
reading = "ヒトケ"
```

---

## 助詞 / 文末で読み分け

**やりたい**: 「十分」 を default 「ジュウブン」、 「十分間 / 十分前」 等の time 文脈で 「ジュップン」。

```toml
[entries."十分"]
reading = "ジュウブン"          # 「sufficient」 の default

[[entries."十分".match]]
next_starts_any = [             # 後続 token が time 単位語頭で始まれば
  "前",
  "後",
  "間",
  "以内",
  "おき",
  "ごろ",
  "頃",
]
reading = "ジュップン"
```

**ポイント**:
- `next_starts_any` は **next_token surface の先頭一致 (any of)**
- `next_eq_any` は完全一致 (= surface 全体が list のいずれかと等しい)
- 用法的には: 「next が短い助詞」 → `next_eq` / 「next が長い名詞 prefix」 → `next_starts_any` が適切

---

## 前後 token の prefix / suffix で分岐

**やりたい**: 「上手」 を 「お上手」 「ご上手」 のとき 「ジョウズ」。

```toml
[entries."上手"]
reading = "カミテ"               # 舞台用語が default

[[entries."上手".match]]
prev_eq_any = ["お", "御", "ご"]  # 直前 token 完全一致
reading = "ジョウズ"
```

**やりたい**: 「学校」 で終わる surface (= 「中学校 / 高校」 等) の後の 「生」 を 「セイ」。

```toml
[[kanji]]
char = "生"
default = "セイ"

[[kanji.match]]
prev_ends_any = [               # 直前 token surface が "校" / "学校" で終わる
  "校",
  "学校",
]
reading = "セイ"                # 念押し (default と同じ、 明示)
```

**ポイント**:
- `prev_ends_any`: 直前 token の **末尾** が list のいずれかに一致 (= 単純 endswith)
- `next_starts_any`: 直後 token の **先頭** が list のいずれかに一致 (= 単純 startswith)
- 「前の前」 は `next2_starts_any` (= 1 飛ばし参照、 例: 「人気が無い」 で idx+2 = 「無い」)

---

## 文字種 (漢字 / ひらがな / 英数) で分岐

**やりたい**: 「生」 を ひらがな の後では 「ナマ」 (= 訓読み)、 漢字の後では 「セイ」 (= 音読み)。

```toml
[[kanji]]
char = "生"
default = "セイ"

[[kanji.match]]
prev_char_type = "ひらがな"      # 直前文字 (= 直前 token の末尾) がひらがな
reading = "ナマ"                # 「きの生クリーム」 等
```

**ポイント**:
- `prev_char_type` / `next_char_type` の値は string で 5 種:
  - `"漢字"` (= CJK Unified Ideographs)
  - `"ひらがな"`
  - `"カタカナ"` (= 全角 + 半角 + 長音)
  - `"英数"` (= ASCII alphanumeric + 全角英数字)
  - `"記号"` (= 句読点 / 括弧 / その他)
- 判定対象は **直前 token の最後の文字** / **直後 token の最初の文字** 1 文字のみ
- 文頭 / 文末 (= prev / next 不在) なら no match

---

## 月名 / 数字の後で分岐

**やりたい**: 「一日」 を 「6 月一日」 「12 月一日」 のとき 「ツイタチ」、 それ以外は 「イチニチ」。

```toml
[entries."一日"]
reading = "イチニチ"            # 「1 日 = 24 時間」

[[entries."一日".match]]
prev_month = true               # 直前 token が「一月」〜「十二月」 / 「1月」〜「12月」 で終わる
reading = "ツイタチ"            # = 暦の 1 日
```

**やりたい**: 「日」 を 「3 日 / 5 日」 等数字の後で 「ニチ」。

```toml
[[kanji]]
char = "日"
default = "ヒ"

[[kanji.match]]
prev_eq = "数字"  # ❌ NG — 「数字」 という string と完全一致だけ、 動的 検出できない
```

**正しい**: 数字+助数詞 は **`rules/numbers/counters/` 側で書く**:

```toml
# rules/numbers/counters/time.toml
[counter."日"]
default = "ニチ"

# 1 日, 2 日, ... のように数字 + 日 → 数字読み + 「ニチ」 (= 内蔵 logic で合成)
```

**ポイント**:
- `prev_month` / `next_digit` は **boolean**、 内蔵 list と照合
- 月名 list (= 一月〜十二月 / 1月〜12月 / １月〜９月) は lib 内蔵、 dict 側で書かない
- 数字判定 (= 半角 + 全角 0-9) も lib 内蔵
- 「数字 + 助数詞」 動的合成は entry inline match では書けない (= rules/numbers/counters/ に書く)

---

## 単漢字に default + 文脈分岐を持たせる

**やりたい**: 「土」 の default を 「ツチ」 にしたい (= Lindera が音読み 「ド」 を返すケース対策)。

**配置**: `core/kanji/<file>.toml`

```toml
[meta]
schema_version = "2"
role = "kanji"

[[kanji]]
char = "土"
default = "ツチ"
```

**やりたい**: 「生」 を default 「セイ」、 「生まれ / 生まれる」 のときは 「ウ」、 「生じる」 のときは 「ショウ」、 ひらがな後は 「ナマ」。

```toml
[[kanji]]
char = "生"
default = "セイ"

[[kanji.match]]
next_eq_any = ["まれ", "まれる"]
reading = "ウ"

[[kanji.match]]
next_eq = "じる"
reading = "ショウ"

[[kanji.match]]
prev_char_type = "ひらがな"
reading = "ナマ"
```

**ポイント**:
- `[[kanji]]` は entry inline match と **完全に同じ matcher vocabulary**
- 違いは: surface が **必ず 1 字漢字** (validate.py が check)、 array of tables 形式
- core/unihan/ の simple lookup と並走 (= unihan は default-only fallback、 [[kanji]] は context-aware)

---

## 助数詞 (= 数字 + 〜) を追加したい

**やりたい**: 新 counter 「語」 (= "3 語" → 「サンゴ」) を追加。

**配置**: `rules/numbers/counters/<該当 file>.toml` (= objects / people / time 等から選ぶ)

```toml
[counter."語"]
default = "ゴ"

[[counter."語".rules]]
last_digit = [1, 6, 8, 0]      # 末尾数字が 1/6/8/10 のとき
suffix = "ゴ"                  # 連濁無し
sokuonize = true               # 「1 語 → イチゴ → イッゴ」 の促音化
```

**やりたい**: 数字依存の特殊読み (= 「4 月 → シガツ」 のような数値 specials) を追加。

```toml
[counter."月"]
default = "ガツ"
specials = { "4" = "シガツ", "7" = "シチガツ", "9" = "クガツ" }
```

**やりたい**: 末尾置換 (= 「4 時 → ヨジ」 のように 「ヨン」 → 「ヨ」)。

```toml
[counter."時"]
default = "ジ"

[[counter."時".replacements]]
last_digit = [4]
from = "ヨン"
to = "ヨ"
```

**ポイント**:
- `simple` 表 (= 単純 suffix のみ) と `counter` 表 (= 連濁 / 促音化等の複雑 logic) を使い分け
- `simple = { "X" = "Y" }`: 数字読み + Y 連結のみ (例: 「3 円 → サンエン」)
- `counter."X"`: 上記の specials / replacements / rules / mode 機能あり
- 連濁 / 促音化 / kana 末尾置換 logic は **lib 内蔵**、 dict は declarative に書く

---

## 外来語 (英字 surface) を追加

**やりたい**: 「Kubernetes」 → 「クバネティス」 を IT 用語辞書に追加。

**配置**: `core/loanwords/it.toml`

```toml
[entries]
"Kubernetes" = "クバネティス"
"PostgreSQL" = "ポストグレスキューエル"
```

**ポイント**:
- key は **ASCII / 全角英字始まり**、 英数字 + 記号 (`+ # . _ -`) を許容
- value は通常通りカタカナ
- lookup は **case-fold + 全角→半角 normalize** で比較 (= 「KUBERNETES」 / 「ＫＵＢＥＲＮＥＴＥＳ」 でも hit)
- **完全一致のみ** (= 「PostgreSQL」 dict 登録時に 「Postgre」 部分だけ hit しない)

---

## 作品造語 (アニメ / ゲーム 固有読み)

**やりたい**: 東方 Project の 「霊夢」 「魔理沙」 を追加。

**配置**: `core/works/<medium>/<title>.toml` (= 1 作品 1 file)

```toml
[meta]
schema_version = "2"
role = "works"
description = "東方 Project (上海アリス幻樂団 / 黄昏フロンティア)"

[entries]
"霊夢" = "レイム"
"魔理沙" = "マリサ"
```

**ポイント** (= [`core/works/README.md`](../core/works/README.md) のサブポリシー):
- **公式読みのみ** (= 二次創作読みは禁止)
- 出典 comment 必須 (= ファイル冒頭で URL or 作品名)
- 一般通称として定着していれば OK (= 公式記載が無いキャラ通称名等)
- 古典読みは現代読みが無い場合のみ (= 平安時代の作品で読み方が複数候補ある場合)

---

## intonation (アクセント) を書きたい (0.2.0 で activate)

**やりたい**: 「橋」 のアクセント (= 「ハ↘シ」、 = 1 型頭高) を表現。

```toml
[entries]
"橋" = "ハ]シ"     # ] の左がアクセント核
"霧雨" = "キ[リサメ"  # [ から右が高、 末尾下降無し = 0 型平板
"桜" = "サ[ク]ラ"   # 中高、 [ から上昇、 ] で下降
```

**ポイント**:
- `[`: phrase 開始 (= rise marker)、 0 型 (平板) と 中高 で使う
- `]`: accent peak (= fall marker、 直後で 1 段下がる)、 1 型〜 (頭高 / 中高 / 尾高) で使う
- `/`: phrase 区切り (= 「ハ[クレイ/レ[イム」 のような複合語の 2 phrase 表現)
- **0.1.0 stable lib では strip して無視** (= reading に bracket 文字を残せる forward compat)
- **0.2.0 stable で parse + 利用** (= AccentPhrase 出力 / TTS engine 連携)
- syntax check は `tools/validate.py` の `validate_bracket_syntax` で CI gate

---

## アンチパターン / よくある間違い

### ❌ POS (品詞) で分岐したい

```toml
[[entries."上手".match]]
pos = "形容詞"      # ❌ pos field は alpha.11+ で削除
reading = "ジョウズ"
```

**理由**: Lindera 撤廃路線、 `pos` 系 matcher は新 format で不採用。 代替:

```toml
[[entries."上手".match]]
next_eq_any = ["な", "に", "だ", "です"]   # 形容動詞 / 形容詞活用形を literal 列挙
reading = "ジョウズ"
```

### ❌ 単漢字を `core/jukugo/` に書く

```toml
# core/jukugo/basic/general.toml
"土" = "ツチ"       # ❌ 1 字 surface は jukugo に置かない、 unihan / kanji 専用
```

**理由**: validate.py が cross-file 重複として CI fail させる、 lib も jukugo map と unihan map を分けて管理してる。 単漢字 default override は `core/kanji/<file>.toml` の `[[kanji]]` block で。

### ❌ 異体字を直接 entry にする

```toml
"髙橋" = "タカハシ"   # ❌ 「髙」 は compat で「高」 に正規化される
"高橋" = "タカハシ"   # ✅ 標準字で書く
```

**理由**: lib Step 1 で異体字は標準字に置換される (= dead 経路に entry を入れても hit しない)。 master push 時 CI の `dedup_compat.py` が自動削除する。

### ❌ regex / 任意 logic を表現したい

```toml
[[entries."X".match]]
prev_eq = "/^[A-Z]+$/"  # ❌ regex は受け付けない
```

**理由**: ReDoS 防御 + 保守性確保のため、 dict 側 vocabulary は **literal exact / prefix / suffix + char_type + bool 述語** に限定 (= proposal §3.3)。 regex 的な分岐が要る場合は:
- **literal 列挙** で代用 (例: 「英数の後」 → `prev_char_type = "英数"`)
- **lib 側 logic** に移譲 (例: 数字 + 助数詞 → `rules/numbers/counters/` で declarative)
- **新 role の lib 拡張** を proposal で立てる (= 0.2.0 の intonation のような大規模機能)

### ❌ inline match を simple form に混ぜる

```toml
[entries]
"灰桜" = "ハイザクラ"
"上手" = { reading = "ジョウズ" }   # ⚠️ 動くが、 match 多いと長く読みにくい
```

**推奨**: detailed entry は expanded form (`[entries."X"]`) で書く。 inline form は match 1〜2 件の短いケース限定。

```toml
[entries]
"灰桜" = "ハイザクラ"

# === 文脈分岐 entries (★A2 alpha.11) ===
[entries."上手"]
reading = "ジョウズ"

[[entries."上手".match]]
next_eq = "から"
reading = "カミテ"
```

---

## 困ったときの調べ方

1. **似た既存例を探す**: `git grep '[[entries."上手".match]]' core/` 等で同 pattern の entry が無いか
2. **STATS.md の category 説明を読む**: どの genre dir に置くべきかの方針
3. **validate.py を走らせる**: `python tools/validate.py` で構文 / 重複 / kana 形式 check (CI 同様)
4. **PR で質問する**: 適切 placement / matcher が判断付かない場合は 「こう書きたい、 どう?」 で OK、 maintainer が方針判定する

→ spec の正確な記述は [SCHEMA.md](SCHEMA.md)、 マイグレーション履歴は [CHANGELOG.md](../CHANGELOG.md)。
