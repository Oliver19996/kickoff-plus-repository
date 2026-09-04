from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class MetaState(Base):
    __tablename__ = "meta_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class Standing(Base):
    __tablename__ = "standings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league_slug: Mapped[str] = mapped_column(String(32), index=True)
    position: Mapped[int] = mapped_column(Integer)
    team_name: Mapped[str] = mapped_column(String(128))
    team_crest: Mapped[str] = mapped_column(String(512), default="")
    played: Mapped[int] = mapped_column(Integer, default=0)
    won: Mapped[int] = mapped_column(Integer, default=0)
    draw: Mapped[int] = mapped_column(Integer, default=0)
    lost: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    goal_diff: Mapped[int] = mapped_column(Integer, default=0)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_slug: Mapped[str] = mapped_column(String(32), index=True)
    utc_date: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(32), default="")
    home_team: Mapped[str] = mapped_column(String(128))
    away_team: Mapped[str] = mapped_column(String(128))
    home_crest: Mapped[str] = mapped_column(String(512), default="")
    away_crest: Mapped[str] = mapped_column(String(512), default="")
    home_score: Mapped[int] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int] = mapped_column(Integer, nullable=True)
    matchday: Mapped[int] = mapped_column(Integer, nullable=True)
    highlight: Mapped[str] = mapped_column(Text, default="")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(768), unique=True)
    title: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(128), default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(768), default="")
    category: Mapped[str] = mapped_column(String(32), index=True, default="other")
    league_slug: Mapped[str] = mapped_column(String(32), default="world")
    rumor_heat: Mapped[float] = mapped_column(Float, default=0.0)
    is_rumor: Mapped[int] = mapped_column(Integer, default=0)


class FeedState(Base):
    __tablename__ = "feed_state"

    url: Mapped[str] = mapped_column(String(768), primary_key=True)
    etag: Mapped[str] = mapped_column(String(256), default="")
    last_modified: Mapped[str] = mapped_column(String(128), default="")


class WeekendPick(Base):
    __tablename__ = "weekend_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(Integer)
    blurb: Mapped[str] = mapped_column(Text, default="")
    rank: Mapped[int] = mapped_column(Integer, default=0)


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from pathlib import Path

    if settings.database_url.startswith("sqlite:///./"):
        Path("data").mkdir(exist_ok=True)
    Base.metadata.create_all(engine)
