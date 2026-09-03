from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import ensure_db
from app.jobs.scheduler import scheduler, start_scheduler
from app.routers import api, internal, pages
from app.services.ingest import ingest_all

ROBOTS = """User-agent: *
Allow: /
Disallow: /internal/
"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_db()
    settings = get_settings()
    if settings.ingest_on_startup:
        ingest_all()
    if settings.start_scheduler:
        start_scheduler()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Kickoff Pulse", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(internal.router)


@app.get("/robots.txt")
def robots():
    return Response(ROBOTS, media_type="text/plain")


@app.get("/favicon.ico")
def favicon():
    path = Path("app/static/img/placeholders/pl.svg")
    return FileResponse(path)
