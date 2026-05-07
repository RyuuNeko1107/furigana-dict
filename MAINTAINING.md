# Maintaining ja-furigana-dict

メンテナー向けの運用ガイド。

## Release を打つ

`ja-furigana-cli` は `ja-furigana-dict` の latest release tag を見て自動取得するので、
辞書を更新したら release を出す (ただし通常は手動不要、下記参照)。

### 通常運用: daily auto-release で自動

`.github/workflows/daily-release.yml` が JST 03:00 に走り、core/ または rules/ への
変更が前回 tag 以降にあれば **`v<YYYY.MM.DD>` (CalVer) tag を自動で打つ**。
そのまま `release.yml` が catch して tar.gz + sha256 を GitHub Releases に upload。

つまり TOML 編集 → master push → 翌 JST 03:00 → 利用者が `furigana dict pull` で取得、
の流れで maintainer の手動操作は不要。

### 手動で release を打ちたい場合

緊急 release / 修正 release を即時に出したいときのみ:

```sh
# 今日の date で tag を打つ (CalVer 形式)
TODAY=$(date +%Y.%m.%d)
git tag -a "v$TODAY" -m "v$TODAY - <要約>"
git push origin "v$TODAY"

# CI 完了を待つ (~30 秒、tarball + sha256 が GitHub Releases に上がる)
gh run watch --repo RyuuNeko1107/ja-furigana-dict --workflow=release.yml

# 確認
gh release view "v$TODAY" --repo RyuuNeko1107/ja-furigana-dict
```

同日に既に release があれば suffix を付ける (`v2026.05.08.1`, `.2` …)。
daily-release workflow も自動で衝突回避するので、衝突は起きないはず。

## upstream (ryuuneko.com production DB) から seed を再投入

upstream で新熟語が追加された場合:

```sh
# 1. upstream から TSV を export
ssh debian "docker exec kuroneko-postgres psql -U zunda -d kuroneko_cms \
  -t -A -F$'\t' -c \"COPY (SELECT character, reading FROM furigana_unihan \
  ORDER BY character) TO STDOUT\"" > tools/seed/unihan.tsv
# (jukugo / compat も同様、tools/import_from_production.py のコメント参照)

# 2. import script を回す
python3 tools/import_from_production.py
# → core/unihan.toml / core/jukugo/general.toml / core/compat.toml が更新される

# 3. 振り分け再実行 (単漢字 → unihan、四字熟語 → four_char、地名 → place_names)
python3 tools/classify_jukugo.py --apply

# 4. validate
python3 tools/validate.py

# 5. commit + release
git add core/
git commit -m "data: upstream から seed 再投入 (unihan X / jukugo Y / compat Z)"
git push origin master
echo "v0.1.X" > VERSION && git add VERSION && git commit -m "chore: bump"
git tag -a v0.1.X && git push origin v0.1.X
```

## CI

### Validate (`validate.yml`)
- PR で `tools/validate.py` (taplo + scheme + kana 検証 + cross-file 重複検出) が走る。
- 失敗時は PR コメントに詳細が出るのでそれに従って修正。

### Release (`release.yml`)
- `v*` tag push で `furigana-dict-vX.Y.Z.tar.gz` + `.sha256` を GitHub Releases に upload。
- 中身は `core/` + `rules/` の 2 階層 (利用側 CLI で `data/` 1 階層に flatten 展開)。

### Dependabot (`.github/dependabot.yml`)
- GitHub Actions のみ (Cargo / npm 依存無し)。
- 週次の actions 更新 PR が来るので CI 緑なら merge。

## PR のレビュー方針

`CONTRIBUTING.md` 末尾の「レビュー方針」に集約:
> 「正しい読み」 vs 「自然な読み」で意見が割れた場合は、TTS 読み上げで
> 実用上自然な方を採用する。

人名・固有名詞の追加 PR は出典を必須にしないが、判断付かない時は merge を保留して
PR 上で議論するのが無難。

## Bug / Security

- 一般 bug: GitHub Issues (`bug_report.yml` テンプレ)。
- 「この読みは間違ってる」: `reading_request.yml` テンプレ (PR でも OK)。
- 辞書由来の挙動バグは ja-furigana 本体ではなくこちらの repo に来てもらう。
- security 系の脆弱性はこの repo の対象範囲外 (純データ)。CLI / lib 側に飛ばす。
