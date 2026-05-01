# 浅草インフルエンサー候補リスト自動収集

浅草で投稿している海外マイクロインフルエンサー (Instagram 3000+ フォロワー、非日本語ユーザー) を抽出し、**Excel ファイル (.xlsx) に追記** するスクリプト。

DM 送信は **行わない**。リスト化までを自動化し、DM は人間が手動で送る運用です。

## なぜ DM 自動送信をしないか

- Instagram ToS で自動 DM は禁止 → アカウント BAN リスク
- 日本の特定電子メール法・EU の GDPR でスパム判定の対象
- 候補抽出までに留めれば規約・法律上ほぼ問題なく運用可能

## 出力

- 既定パス: `output/asakusa_leads.xlsx`
- 2 シート構成
  - **`leads`**: 抽出した候補ユーザー (毎回追記)
  - **`seen_users`**: 重複排除用 (過去 7 日以内に出した user は再追記しない)

毎回上書きではなく **追記** されるので、過去ログが残ります。Excel/Numbers/Google スプレッドシート(取り込み) どれでも開けます。

## セットアップ

### 1. Apify アカウント

1. https://apify.com で無料登録
2. Settings → Integrations → API token をコピー
3. 使用 Actor: `apify/instagram-hashtag-scraper` と `apify/instagram-profile-scraper` (Pay-as-you-go)

### 2. ローカル設定

```bash
cp .env.example .env
# .env を編集して APIFY_TOKEN を貼る
```

### 3. 動作確認

```bash
uv sync
uv run pytest                              # 全テスト
uv run python -m src.main --dry-run        # Apify を呼ばず fixture で確認
                                           # → output/asakusa_leads.dry-run.xlsx に書き出し
uv run python -m src.main                  # 本番実行 (Apify 課金 ~$0.20/日)
                                           # → output/asakusa_leads.xlsx に追記
```

### 4. 定期実行 (任意)

毎朝自動で走らせたい場合は **macOS の cron / launchd** が一番手軽:

```bash
crontab -e
# 毎朝 8:00 JST に実行 (出力は ~/Desktop/insta/output/asakusa_leads.xlsx に追記される)
0 8 * * * cd /Users/koukikaida/Desktop/insta && /Users/koukikaida/.local/bin/uv run python -m src.main >> output/run.log 2>&1
```

PC が起動していないと走らないので、毎日 8:00 に Mac が立ち上がっているなら十分。常時稼働が必要なら別途 VPS 等を検討。

## ファイル構成

```
src/
  main.py        # エントリ
  config.py      # YAML + 環境変数読込
  scraper.py     # Apify hashtag/location 取得
  profile.py     # Apify profile 取得
  filter.py      # 言語 + フォロワー範囲 + dedup フィルタ
  excel.py       # openpyxl で .xlsx を読み書き
  lang.py        # lingua wrapper (ja 判定)
tests/
  test_lang.py
  test_filter.py
  test_scraper.py
  test_excel.py
  fixtures/
    apify_hashtag_sample.json
    apify_profile_sample.json
config.yml       # ハッシュタグ・閾値・出力パスの設定
```

## コスト

Apify Pay-as-you-go で **月 $5–10** 程度を想定。
- 1日: ハッシュタグ12 × 投稿100 = 1200 posts → unique users ~300 → profile fetch
- Apify ダッシュボードで月次 usage を確認、$10 超えたら閾値見直し

## 規約・法律上の注意

- DM 自動送信は絶対にしない
- 取得は公開プロフィール情報のみ
- Excel 上の bio 等は社内利用のみ、外部公開しない
- EU 圏フォロワーから削除依頼があれば該当行を即削除
