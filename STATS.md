# Stats — `ja-furigana-dict`

辞書ボリュームのスナップショット。配布時の中身を一覧で把握する用。
git に commit されている master HEAD の状態を基準にする。

> 最終更新: 2026-05-06 (`v0.1.1` 時点)
> 自動更新ではないので、release ごとに手動でメンテナーが更新する想定。
> 再計測コマンドは末尾の [更新方法](#更新方法) を参照。

## サマリ

| カテゴリ | エントリ数 | ファイルサイズ |
|---|---:|---:|
| **語彙辞書** (`core/`) | **45,194** | **~860 KB** |
| **エンジンルール** (`rules/`) | **~260** | **~19 KB** |
| **合計** | **~45,455** | **~880 KB** |

配布物 (`furigana-dict-vX.Y.Z.tar.gz`) は約 226 KB (gzip 圧縮後)。

## 内訳

### `core/` — 語彙辞書

| ファイル | エントリ数 | サイズ | 用途 |
|---|---:|---:|---|
| `unihan.toml` | 43,749 | 815 KB | 単漢字フォールバック (本番 ryuuneko.com 由来 + override 14 件) |
| `jukugo/general.toml` | 594 | ~18 KB | 二字・三字の一般熟語 (季節 / 行事 / 慣用句 含む) |
| `jukugo/four_char.toml` | 58 | 3 KB | 四字熟語 (4 字 + 全 CJK 漢字) |
| `jukugo/place_names.toml` | 109 | 4 KB | 地名 (47 都道府県 / 主要都市 / 駅 / 寺社仏閣 / 観光地) |
| `jukugo/personal_names.toml` | 71 | 3 KB | 人名 (戦国 / 平安 / 古典文学 / 啓蒙期 + 異体字姓、**PR 募集中**) |
| `jukugo/proper_nouns.toml` | 67 | 2.5 KB | 固有名詞 (大学 / 中央官庁 / 元号 / 歴史的事象、**PR 募集中**) |
| `jukugo/animals.toml` | 36 | 1 KB | 動植物 / 魚介の難読 (蝙蝠 / 椿 / 躑躅 / 鰯 / 牡蠣 等) |
| `jukugo/foods.toml` | 26 | 0.8 KB | 食べ物 / 料理の難読 (餃子 / 焼売 / 大福 / 抹茶 等) |
| `jukugo/specialized.toml` | 35 | 1.2 KB | 専門用語 (医学 / 軍事 / 法学 / 哲学 / 経済) の難読 |
| `jukugo/body_parts.toml` | 24 | 0.8 KB | 体の部位 / 内臓 / 医学呼称 (鳩尾 / 踝 / 喉仏 等) |
| `compat.toml` | 436 | 6 KB | 異体字 → 標準字 (髙→高 等) |
| **小計** | **45,194** | **~860 KB** | |

### `rules/` — エンジンルール

| ファイル | エントリ数 | サイズ | 内容 |
|---|---:|---:|---|
| `days.toml` | 31 | 1 KB | 1〜31 日の特殊読み (1→ツイタチ 等) |
| `scales.toml` | ~10 | 1 KB | 万 / 億 / 兆 / 京 等の大数スケール |
| `units.toml` | ~30 | 1 KB | SI 単位 (km / kg / mL …、`v0.1.1` 以降は case-insensitive) |
| `symbols.toml` | ~10 | 0.2 KB | 記号読み (+ / − / % / ‰ …) |
| `latin.toml` | ~26 | 0.6 KB | ラテン文字読み (A→エー …) |
| `numeric_phrases.toml` | ~10 | 0.6 KB | 数字を含む例外語句 (二十歳→ハタチ 等) |
| `counters/*.toml` (7 ファイル) | ~80 | ~7 KB | 助数詞ルール (本/匹/個/年/月/日 …、連濁・促音化・kana 末尾置換) |
| `context/*.toml` (3 ファイル) | ~30 | ~7 KB | 文脈依存読み (一日→ツイタチ/イチニチ 等) |
| **小計** | **~227** | **~19 KB** | |

(rules はエントリ数より「ルールパターン数」の方が意味的に正しいが、ここでは
TOML の top-level エントリ数を概数として表記)

## 利用側 (`ja-furigana`) でのメモリ寄与

`ja-furigana-cli` 起動時のプロセス全体は **~70 MB** だが、その内訳:

| 構成要素 | メモリ寄与 |
|---|---:|
| Lindera + IPADIC (形態素解析の辞書) | **~50 MB** ← 支配的 |
| 本リポジトリの語彙辞書 + ルール | **~3 MB** (TOML を `HashMap` 等に展開後) |
| その他 (Rust runtime / Tokio / etc) | ~17 MB |

10 万件規模の辞書になっても、本リポジトリ側の寄与は ~10 MB 程度に収まる試算。
Lindera が支配的なので、辞書増加によるメモリ圧迫は当面気にしなくて良い。

## カバレッジの偏り

- **単漢字 (unihan)** はほぼ全 CJK 漢字をカバー (43k 字)
- **熟語 (jukugo)** は本番 ryuuneko.com 実用 1.7k 件 → 整理 + seed 拡充で 1,000 件超え
  - 一般 / 季節 / 行事 / 慣用句: 594 件
  - 四字熟語: 58 件
  - 地名 (47 都道府県 + 主要都市 + 駅 + 寺社仏閣 + 観光地): 109 件
  - 人名 (戦国 / 平安 / 古典文学 + 異体字姓): 71 件
  - 固有名詞 (大学 / 中央官庁 / 元号 / 歴史的事象): 67 件
  - 動植物 / 魚介の難読 (熟字訓): 36 件
  - 食べ物 / 料理の難読: 26 件
  - 専門用語 (医学 / 軍事 / 法学 / 学術): 35 件
  - 体の部位 / 内臓 / 医学呼称: 24 件
- **現代の私人 / 私企業 / アニメ作品 / 商標** は seed していない (誤読リスク回避方針)。
  公式読みが定まっていれば PR 単位で個別判断。

→ 体感では「**著名な漢字熟語 / 単漢字 / 古典 / 学術 / 自然物は読める、現代私人 / 商標 / 私企業は手薄**」。
PR 大歓迎。

## 更新方法

サイズ・件数を再計測するときは:

```sh
# core 全体のエントリ数 (TOML を python で parse)
python3 -c "
import tomllib, glob
for path in sorted(glob.glob('core/**/*.toml', recursive=True)):
    with open(path, 'rb') as f:
        data = tomllib.load(f)
    n = len(data.get('entries', data.get('map', {})))
    print(f'{n:>8}  {path}')
"

# 全 toml の line / size カウント
wc -l core/**/*.toml rules/**/*.toml
```

`tools/validate.py` の最終行にも total 件数が出るので参考に。
