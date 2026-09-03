from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Article, Match, MetaState, Standing

router = APIRouter(prefix="/api")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    last = db.get(MetaState, "last_ingest_at")
    return {
        "ok": True,
        "articles": db.query(Article).count(),
        "matches": db.query(Match).count(),
        "standings": db.query(Standing).count(),
        "last_ingest_at": last.value if last else None,
    }
