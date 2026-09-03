# Kickoff Pulse

プレミアリーグ、ラ・リーガ、ブンデスリーガ、Jリーグの試合結果・移籍・深掘り記事・ゴシップ（出典付き）を、画像多めのマガジンUIで見せる Python Web アプリです。ライブ秒速報ではなく、15分ごとのダイジェストです。

## ローカル起動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

[http://127.0.0.1:8000](http://127.0.0.1:8000) を開きます。

`FOOTBALL_DATA_TOKEN` が空でもサンプルの順位・試合で画面を確認できます。[football-data.org](https://www.football-data.org/client/register) でトークンを取ると欧州3リーグが実データになります。`OPENAI_API_KEY` は任意です。

## テスト

```bash
INGEST_ON_STARTUP=false DATABASE_URL=sqlite:///./data/test.sqlite3 pytest -q
```

## GitHub と Render で公開

1. GitHub に public リポジトリ `kickoff-pulse` を作り、このフォルダを push する。
2. [Render](https://render.com) で Blueprint として `render.yaml` を読み込むか、Web Service を手動作成する。
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Environment に `FOOTBALL_DATA_TOKEN`、`REFRESH_TOKEN`、任意で `OPENAI_API_KEY` と `APP_BASE_URL` を入れる。
4. GitHub Actions の Secrets に同じ `REFRESH_TOKEN` と公開 URL の `APP_BASE_URL` を入れ、15分ごとの起こし打ちをする。

コードは GitHub、公開URLは Render です。GitHub Pages では動きません。

## 注意

記事本文は保存・転載しません。ゴシップは Rumor ラベル付きです。各メディアの利用条件を守ってください。
