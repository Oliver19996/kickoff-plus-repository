from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.services.ingest import ingest_all

router = APIRouter(prefix="/internal")


@router.post("/refresh")
def refresh(x_refresh_token: str | None = Header(default=None, alias="X-Refresh-Token")):
    settings = get_settings()
    if not x_refresh_token or x_refresh_token != settings.refresh_token:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    return ingest_all()
