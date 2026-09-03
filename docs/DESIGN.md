# Kickoff Pulse 設計詳細

画像主導のサッカーダイジェスト。対象リーグはプレミアリーグ、ラ・リーガ、ブンデスリーガ、Jリーグ。試合結果・ニッチ記事・大型移籍・選手ゴシップ（出典付き Rumor）を15分粒度で更新する。

## スタック

- Python 3.12 / FastAPI / Jinja2 / SQLite / APScheduler
- 公開: GitHub（ソース）+ Render（Web）
- 欧州結果: football-data.org（無料枠は遅延スコア、Jリーグなし）
- ニュース: RSS のタイトル・要約・URL・画像URLのみ保存

## ルート

- `/` ホーム（ヒーロー、速報レーン、移籍／ゴシップ／深掘り）
- `/leagues/{pl|laliga|bundesliga|j1}` リーグハブ
- `/matches/{id}` 試合
- `/transfers` `/gossip` `/deep-dives`
- `/api/health`
- `POST /internal/refresh` ヘッダ `X-Refresh-Token`

## AI（キー任意）

- 英語見出しの日本語3文要約
- キーワード分類の補助はルールが主、LLMは要約と週末おすすめ文
- 移籍・ゴシップの噂温度はタイトル語の重なり（High / Medium / Low）
- キーが無いときはタイトルとRSSリードだけで表示する

## 更新

起動時 ingest → 15分 APScheduler → GitHub Actions が Render を起こして refresh
