from datetime import datetime, timezone

from app.models import Article, MetaState, SessionLocal
from app.services.ai import refresh_weekend_picks, summarize_new_articles
from app.services.football import upsert_european_leagues
from app.services.news import ingest_feeds

SAMPLE_ARTICLES = [
    {
        "url": "https://example.com/transfer-mbappe-watch",
        "title": "Real Madrid monitor Premier League target as transfer window talk heats up",
        "source": "Kickoff Pulse Desk",
        "summary": "Multiple desks report interest but no club confirmation yet.",
        "category": "transfer",
        "league_slug": "laliga",
        "is_rumor": 1,
        "image_url": "/static/img/placeholders/laliga.svg",
    },
    {
        "url": "https://example.com/gossip-training-ground",
        "title": "選手の私生活を巡る噂が再燃、クラブはノーコメント",
        "source": "Kickoff Pulse Desk",
        "summary": "タブロイド報道。公式発表はなく、Rumor 扱い。",
        "category": "gossip",
        "league_slug": "pl",
        "is_rumor": 1,
        "image_url": "/static/img/placeholders/pl.svg",
    },
    {
        "url": "https://example.com/niche-gegenpress",
        "title": "戦術特集: ハイプレスの距離感をデータで深掘り",
        "source": "Kickoff Pulse Desk",
        "summary": "xG とプレス成功地点から見た今季の変化。",
        "category": "niche",
        "league_slug": "bundesliga",
        "is_rumor": 0,
        "image_url": "/static/img/placeholders/bundesliga.svg",
    },
    {
        "url": "https://example.com/j1-result",
        "title": "Jリーグ速報: 首位攻防は引き分け、優勝争いはまだ混戦",
        "source": "Kickoff Pulse Desk",
        "summary": "公式結果の見出しダイジェスト。本文は出典へ。",
        "category": "match",
        "league_slug": "j1",
        "is_rumor": 0,
        "image_url": "/static/img/placeholders/j1.svg",
    },
]


def ingest_all() -> dict[str, int | str]:
    upsert_european_leagues()
    created = ingest_feeds()
    seeded = _seed_if_empty()
    summarized = summarize_new_articles()
    refresh_weekend_picks()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    db = SessionLocal()
    try:
        db.merge(MetaState(key="last_ingest_at", value=stamp))
        db.commit()
    finally:
        db.close()
    return {
        "articles_created": created + seeded,
        "summarized": summarized,
        "last_ingest_at": stamp,
    }


def _seed_if_empty() -> int:
    db = SessionLocal()
    try:
        if db.query(Article).count() > 0:
            return 0
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for item in SAMPLE_ARTICLES:
            db.add(Article(published_at=now, rumor_heat=0.55 if item["is_rumor"] else 0.0, **item))
        db.commit()
        return len(SAMPLE_ARTICLES)
    finally:
        db.close()
