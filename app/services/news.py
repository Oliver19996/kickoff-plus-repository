from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from time import mktime

import feedparser
import httpx

from app.models import Article, FeedState, SessionLocal
from app.services.classify import classify_article, detect_league, is_football_article, rumor_heat

FEEDS = [
    {
        "source": "BBC Sport",
        "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "league": "world",
    },
    {
        "source": "The Guardian",
        "url": "https://www.theguardian.com/football/rss",
        "league": "world",
    },
    {
        "source": "Sky Sports",
        "url": "https://www.skysports.com/rss/12040",
        "league": "pl",
    },
    {
        "source": "サッカーキング",
        "url": "https://www.soccer-king.jp/feed",
        "league": "j1",
    },
    {
        "source": "ゲキサカ",
        "url": "https://web.gekisaka.jp/feed",
        "league": "j1",
    },
]


def ingest_feeds() -> int:
    created = 0
    db = SessionLocal()
    try:
        for feed in FEEDS:
            created += _ingest_one(db, feed)
        _apply_rumor_heat(db)
        db.commit()
    finally:
        db.close()
    return created


def _ingest_one(db, feed: dict) -> int:
    state = db.get(FeedState, feed["url"]) or FeedState(url=feed["url"])
    headers = {}
    if state.etag:
        headers["If-None-Match"] = state.etag
    if state.last_modified:
        headers["If-Modified-Since"] = state.last_modified
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(feed["url"], headers=headers)
            if response.status_code == 304:
                return 0
            response.raise_for_status()
            raw = response.content
            state.etag = response.headers.get("etag") or state.etag
            state.last_modified = response.headers.get("last-modified") or state.last_modified
    except httpx.HTTPError:
        return 0

    parsed = feedparser.parse(raw)
    db.merge(state)
    added = 0
    for entry in parsed.entries[:25]:
        url = entry.get("link") or ""
        title = (entry.get("title") or "").strip()
        if not url or not title:
            continue
        if not is_football_article(title, entry.get("summary") or entry.get("description") or ""):
            continue
        if db.query(Article).filter(Article.url == url).first():
            continue
        summary = _plain(entry.get("summary") or entry.get("description") or "")
        category, is_rumor = classify_article(title, summary)
        if category == "other":
            continue
        league = detect_league(title, summary)
        if league == "world" and feed.get("league") != "world":
            league = feed["league"]
        db.add(
            Article(
                url=url,
                title=title,
                source=feed["source"],
                published_at=_published(entry),
                summary=summary[:800],
                image_url=_image(entry),
                category=category,
                league_slug=league,
                is_rumor=1 if is_rumor or category == "gossip" else 0,
            )
        )
        added += 1
    return added


def _apply_rumor_heat(db) -> None:
    articles = db.query(Article).filter(Article.category.in_(["transfer", "gossip"])).all()
    titles = [a.title for a in articles]
    for article in articles:
        article.rumor_heat = rumor_heat(article.title, titles)


def _plain(html: str) -> str:
    return " ".join(html.replace("<", " <").split())[:1000]


def _image(entry: dict) -> str:
    media = entry.get("media_content") or []
    if media and media[0].get("url"):
        return media[0]["url"]
    thumbs = entry.get("media_thumbnail") or []
    if thumbs and thumbs[0].get("url"):
        return thumbs[0]["url"]
    if entry.get("enclosures"):
        href = entry.enclosures[0].get("href")
        if href:
            return href
    for field in ("summary", "description", "content"):
        value = entry.get(field) or ""
        values = value if isinstance(value, list) else [value]
        for item in values:
            html = item.get("value", "") if isinstance(item, dict) else item
            parser = _ImageParser()
            parser.feed(html)
            if parser.url:
                return parser.url
    return ""


class _ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.url = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img" or self.url:
            return
        self.url = dict(attrs).get("src") or ""


def _published(entry: dict) -> datetime | None:
    if entry.get("published_parsed"):
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc).replace(tzinfo=None)
    if entry.get("published"):
        try:
            return parsedate_to_datetime(entry.published).replace(tzinfo=None)
        except (TypeError, ValueError):
            return None
    return None
