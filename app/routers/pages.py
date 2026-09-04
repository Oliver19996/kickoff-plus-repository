from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import re

from app.db import get_db
from app.config import get_settings
from app.leagues import CATEGORY_LABELS, LEAGUES
from app.models import Article, Match, MetaState, Standing, WeekendPick
from app.services.classify import heat_label
from app.services.ingest import ingest_all

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["leagues"] = LEAGUES
templates.env.globals["category_labels"] = CATEGORY_LABELS
templates.env.globals["heat_label"] = heat_label


def _last_ingest(db: Session) -> str:
    row = db.get(MetaState, "last_ingest_at")
    return row.value if row else "未取得"


def _placeholder(league_slug: str) -> str:
    meta = LEAGUES.get(league_slug) or LEAGUES["pl"]
    return meta["placeholder"]


def article_image(article: Article) -> str:
    return article.image_url


def article_placeholder(article: Article) -> str:
    return _placeholder(article.league_slug)


def article_has_image(article: Article) -> bool:
    return bool(article.image_url)


def league_placeholder(league_slug: str) -> str:
    return _placeholder(league_slug)


def article_is_japanese(article: Article) -> bool:
    japanese = len(re.findall(r"[ぁ-んァ-ン一-龥々ー]", article.title))
    latin = len(re.findall(r"[A-Za-z]", article.title))
    return japanese >= 2 and japanese >= latin


def article_japanese(article: Article, part: str = "heading") -> str:
    if article_is_japanese(article):
        return article.title if part == "heading" else article.summary
    if article.ai_summary.startswith("[JA]"):
        translated = article.ai_summary[4:].strip().splitlines()
        if part == "heading":
            return translated[0] if translated else article.title
        return " ".join(translated[1:]) or article.summary
    return article.title if part == "heading" else article.summary


def render(request: Request, name: str, context: dict):
    return templates.TemplateResponse(request, name, context)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    if get_settings().ingest_on_request:
        try:
            ingest_all()
        except Exception:
            pass
    articles = (
        db.query(Article)
        .filter(Article.category != "other")
        .order_by(Article.published_at.desc())
        .limit(40)
        .all()
    )
    hero = articles[0] if articles else None
    by_cat = {
        "match": [a for a in articles if a.category == "match"][:10],
        "transfer": [a for a in articles if a.category == "transfer"][:8],
        "insight": [a for a in articles if a.category in {"gossip", "niche"}][:10],
    }
    recent_matches = (
        db.query(Match).filter(Match.status == "FINISHED").order_by(Match.utc_date.desc()).limit(8).all()
    )
    picks = db.query(WeekendPick).order_by(WeekendPick.rank).all()
    pick_matches = []
    for pick in picks:
        match = db.get(Match, pick.match_id)
        if match:
            pick_matches.append((pick, match))
    return render(
        request,
        "home.html",
        {
            "hero": hero,
            "by_cat": by_cat,
            "recent_matches": recent_matches,
            "pick_matches": pick_matches,
            "last_ingest": _last_ingest(db),
            "article_image": article_image,
            "article_placeholder": article_placeholder,
            "article_has_image": article_has_image,
            "article_japanese": article_japanese,
            "league_placeholder": league_placeholder,
        },
    )


@router.get("/leagues/{slug}", response_class=HTMLResponse)
def league_hub(slug: str, request: Request, db: Session = Depends(get_db)):
    if slug not in LEAGUES:
        raise HTTPException(status_code=404)
    standings = db.query(Standing).filter(Standing.league_slug == slug).order_by(Standing.position).all()
    matches = db.query(Match).filter(Match.league_slug == slug).order_by(Match.utc_date.desc()).limit(12).all()
    news = (
        db.query(Article)
        .filter(Article.league_slug == slug)
        .order_by(Article.published_at.desc())
        .limit(16)
        .all()
    )
    return render(
        request,
        "league.html",
        {
            "league": LEAGUES[slug],
            "standings": standings,
            "matches": matches,
            "news": news,
            "last_ingest": _last_ingest(db),
            "article_image": article_image,
            "article_placeholder": article_placeholder,
            "article_has_image": article_has_image,
            "article_japanese": article_japanese,
        },
    )


@router.get("/matches/{match_id}", response_class=HTMLResponse)
def match_page(match_id: int, request: Request, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404)
    related = (
        db.query(Article)
        .filter(Article.league_slug == match.league_slug)
        .order_by(Article.published_at.desc())
        .limit(8)
        .all()
    )
    return render(
        request,
        "match.html",
        {
            "match": match,
            "league": LEAGUES.get(match.league_slug),
            "related": related,
            "last_ingest": _last_ingest(db),
            "article_image": article_image,
            "article_placeholder": article_placeholder,
            "article_has_image": article_has_image,
            "article_japanese": article_japanese,
        },
    )


def _category_page(category: str, request: Request, db: Session):
    query = db.query(Article)
    if category == "insight":
        query = query.filter(Article.category.in_(["gossip", "niche"]))
    else:
        query = query.filter(Article.category == category)
    rows = query.order_by(Article.published_at.desc()).limit(30).all()
    return render(
        request,
        "category.html",
        {
            "category": category,
            "title": CATEGORY_LABELS[category],
            "articles": rows,
            "last_ingest": _last_ingest(db),
            "article_image": article_image,
            "article_placeholder": article_placeholder,
            "article_has_image": article_has_image,
            "article_japanese": article_japanese,
        },
    )


@router.get("/transfers", response_class=HTMLResponse)
def transfers(request: Request, db: Session = Depends(get_db)):
    return _category_page("transfer", request, db)


@router.get("/gossip", response_class=HTMLResponse)
def gossip(request: Request, db: Session = Depends(get_db)):
    return _category_page("gossip", request, db)


@router.get("/deep-dives", response_class=HTMLResponse)
def deep_dives(request: Request, db: Session = Depends(get_db)):
    return _category_page("niche", request, db)


@router.get("/insights", response_class=HTMLResponse)
def insights(request: Request, db: Session = Depends(get_db)):
    return _category_page("insight", request, db)
