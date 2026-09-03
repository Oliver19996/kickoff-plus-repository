from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.config import get_settings
from app.leagues import LEAGUES
from app.models import Match, SessionLocal, Standing

FOOTBALL_URL = "https://api.football-data.org/v4"
SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_football.json"


def _headers() -> dict[str, str]:
    token = get_settings().football_data_token
    return {"X-Auth-Token": token} if token else {}


def load_sample() -> dict:
    if SAMPLE_PATH.exists():
        return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    return {"standings": {}, "matches": {}}


def fetch_competition(code: str, path: str) -> dict | None:
    settings = get_settings()
    if not settings.football_data_token:
        return None
    url = f"{FOOTBALL_URL}/competitions/{code}/{path}"
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, headers=_headers())
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        return None


def upsert_european_leagues() -> None:
    sample = load_sample()
    db = SessionLocal()
    try:
        for slug, meta in LEAGUES.items():
            code = meta["code"]
            if not code:
                continue
            standings_payload = fetch_competition(code, "standings")
            matches_payload = fetch_competition(code, "matches")
            if standings_payload is None:
                standings_payload = {"standings": [{"table": sample.get("standings", {}).get(slug, [])}]}
            if matches_payload is None:
                matches_payload = {"matches": sample.get("matches", {}).get(slug, [])}
            _store_standings(db, slug, standings_payload)
            _store_matches(db, slug, matches_payload)
        db.commit()
    finally:
        db.close()


def _store_standings(db, league_slug: str, payload: dict) -> None:
    db.query(Standing).filter(Standing.league_slug == league_slug).delete()
    tables = payload.get("standings") or []
    rows = []
    for block in tables:
        if block.get("type") in (None, "TOTAL") or "table" in block:
            rows = block.get("table") or rows
            if block.get("type") == "TOTAL":
                break
    if not rows and tables:
        rows = tables[0].get("table") or []
    for row in rows:
        team = row.get("team") or {}
        db.add(
            Standing(
                league_slug=league_slug,
                position=int(row.get("position") or 0),
                team_name=team.get("name") or row.get("team_name") or "",
                team_crest=team.get("crest") or row.get("team_crest") or "",
                played=int(row.get("playedGames") or row.get("played") or 0),
                won=int(row.get("won") or 0),
                draw=int(row.get("draw") or 0),
                lost=int(row.get("lost") or 0),
                points=int(row.get("points") or 0),
                goal_diff=int(row.get("goalDifference") or row.get("goal_diff") or 0),
            )
        )


def _store_matches(db, league_slug: str, payload: dict) -> None:
    existing_ids = {
        row[0]
        for row in db.query(Match.id).filter(Match.league_slug == league_slug).all()
    }
    for item in payload.get("matches") or []:
        match_id = int(item.get("id") or 0)
        if not match_id:
            continue
        score = item.get("score") or {}
        full = score.get("fullTime") or {}
        home = item.get("homeTeam") or {}
        away = item.get("awayTeam") or {}
        values = dict(
            league_slug=league_slug,
            utc_date=item.get("utcDate") or item.get("utc_date") or "",
            status=item.get("status") or "",
            home_team=home.get("name") or item.get("home_team") or "",
            away_team=away.get("name") or item.get("away_team") or "",
            home_crest=home.get("crest") or item.get("home_crest") or "",
            away_crest=away.get("crest") or item.get("away_crest") or "",
            home_score=full.get("home") if full.get("home") is not None else item.get("home_score"),
            away_score=full.get("away") if full.get("away") is not None else item.get("away_score"),
            matchday=item.get("matchday"),
        )
        row = db.get(Match, match_id)
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            db.add(Match(id=match_id, **values))
        existing_ids.discard(match_id)
