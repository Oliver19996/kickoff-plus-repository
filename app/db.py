from collections.abc import Generator

from sqlalchemy.orm import Session

from app.models import SessionLocal, init_db


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_db() -> None:
    init_db()
