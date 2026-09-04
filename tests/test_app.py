from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db import ensure_db
from app.services.classify import classify_article, heat_label, rumor_heat
from app.services.football import upsert_european_leagues
from app.services.ingest import ingest_all


def test_classify_categories():
    assert classify_article("Arsenal complete transfer signing")[0] == "transfer"
    assert classify_article("選手の熱愛スキャンダルの噂")[0] == "gossip"
    assert classify_article("戦術特集: プレスの分析")[0] == "niche"
    assert classify_article("試合速報 2-1 勝利")[0] == "match"


def test_rumor_heat_and_label():
    peers = [
        "Mbappe transfer to Real Madrid rumours",
        "Real Madrid Mbappe talks continue",
        "Unrelated Premier League preview notes",
    ]
    score = rumor_heat(peers[0], peers)
    assert score >= 0.45
    assert heat_label(0.9) == "High"


def test_sample_football_and_pages(tmp_path, monkeypatch):
    Path("data").mkdir(exist_ok=True)
    ensure_db()
    upsert_european_leagues()
    ingest_all()
    from app.main import app

    client = TestClient(app)
    home = client.get("/")
    assert home.status_code == 200
    assert "Kickoff Pulse" in home.text
    assert "home_crest" not in home.text
    assert "今週末のおすすめ" in home.text
    assert "x-dock" not in home.text
    assert "match-score" in home.text
    assert "日本語訳を取得中です。" in home.text or "[JA]" not in home.text
    league = client.get("/leagues/pl")
    assert league.status_code == 200
    assert "プレミアリーグ" in league.text
    assert "team-crest" in league.text
    assert "league-page__backdrop" in league.text
    assert "league-hero__image" in league.text
    assert "score-divider" in home.text
    assert "<h2 class=\"mb-4 font-display text-2xl\">速報</h2>" in home.text
    j1 = client.get("/leagues/j1")
    assert j1.status_code == 200
    insights = client.get("/insights")
    assert insights.status_code == 200
    assert "INSIDE EDGE" in insights.text
    match = client.get("/matches/401001")
    assert match.status_code == 200
    health = client.get("/api/health")
    assert health.status_code == 200
    denied = client.post("/internal/refresh")
    assert denied.status_code == 401
    ok = client.post("/internal/refresh", headers={"X-Refresh-Token": "test-token"})
    assert ok.status_code == 200
    robots = client.get("/robots.txt")
    assert "Disallow: /internal/" in robots.text


def test_home_ingests_on_request(monkeypatch):
    from app.routers import pages

    calls = []
    monkeypatch.setattr(pages, "get_settings", lambda: SimpleNamespace(ingest_on_request=True))
    monkeypatch.setattr(pages, "ingest_all", lambda: calls.append(True))

    from app.main import app

    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert calls == [True]
