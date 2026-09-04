from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

from sqlalchemy import or_

from app.config import get_settings
from app.models import Article, Match, SessionLocal, Standing, WeekendPick


def summarize_new_articles(limit: int = 30) -> int:
    settings = get_settings()
    if not settings.openai_api_key:
        return 0
    db = SessionLocal()
    try:
        candidates = (
            db.query(Article)
            .filter(or_(Article.ai_summary == "", ~Article.ai_summary.startswith("[JA]")))
            .order_by(Article.published_at.desc())
            .limit(limit * 4)
            .all()
        )
        rows = [article for article in candidates if not _is_japanese(article.title)][:limit]
        if not rows:
            return 0
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        updated = 0
        for article in rows:
            prompt = (
                "次のサッカー記事を日本語に変換してください。必ず次の形式で出力してください。\n"
                "1行目: 見出しの日本語訳\n2行目以降: リードの日本語要約（3文以内）\n"
                "英語を残さず、固有名詞だけ原語表記を許可します。事実を足さず、噂を断定しないでください。"
                "出力の先頭に必ず [JA] を付けてください。\n"
                f"見出し: {article.title}\nリード: {article.summary[:600]}"
            )
            try:
                response = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=220,
                )
                text = (response.choices[0].message.content or "").strip()
                if text:
                    article.ai_summary = text if text.startswith("[JA]") else f"[JA] {text}"
                    updated += 1
            except Exception:
                continue
        db.commit()
        return updated
    finally:
        db.close()


def refresh_weekend_picks() -> None:
    db = SessionLocal()
    try:
        db.query(WeekendPick).delete()
        now = datetime.now(timezone.utc)
        upcoming = (
            db.query(Match)
            .filter(Match.status.in_(["SCHEDULED", "TIMED", ""]))
            .all()
        )
        scored: list[tuple[int, Match, str]] = []
        standings_by_league: dict[str, list[Standing]] = {}
        for match in upcoming:
            if not match.utc_date:
                continue
            try:
                kickoff = datetime.fromisoformat(match.utc_date.replace("Z", "+00:00"))
            except ValueError:
                continue
            if kickoff < now or kickoff > now + timedelta(days=8):
                continue
            if match.league_slug not in standings_by_league:
                standings_by_league[match.league_slug] = (
                    db.query(Standing).filter(Standing.league_slug == match.league_slug).all()
                )
            table = standings_by_league[match.league_slug]
            pos = {row.team_name: row.position for row in table}
            home_pos = pos.get(match.home_team, 10)
            away_pos = pos.get(match.away_team, 10)
            interest = 40 - min(home_pos, away_pos) * 2 + abs(home_pos - away_pos)
            blurb = _fallback_blurb(match, home_pos, away_pos)
            scored.append((interest, match, blurb))
        scored.sort(key=lambda item: item[0], reverse=True)
        settings = get_settings()
        for rank, (_, match, blurb) in enumerate(scored[:3], start=1):
            if settings.openai_api_key:
                generated = _ai_blurb(match, blurb)
                blurb = generated or blurb
            match.highlight = blurb
            db.add(WeekendPick(match_id=match.id, blurb=blurb, rank=rank))
        db.commit()
    finally:
        db.close()


def _is_japanese(title: str) -> bool:
    japanese = len(re.findall(r"[ぁ-んァ-ン一-龥々ー]", title))
    latin = len(re.findall(r"[A-Za-z]", title))
    return japanese >= 2 and japanese >= latin


def _fallback_blurb(match: Match, home_pos: int, away_pos: int) -> str:
    return (
        f"{match.home_team}（{home_pos}位）対 {match.away_team}（{away_pos}位）。"
        "順位と直近カードから見た今週末の注目一戦。"
    )


def _ai_blurb(match: Match, fallback: str) -> str:
    settings = get_settings()
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        prompt = (
            "次の対戦の見どころを日本語で2文。順位以外の未確認情報は書かない。"
            f"{match.home_team} vs {match.away_team} / {fallback}"
        )
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=160,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return ""
