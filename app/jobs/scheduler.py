from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.ingest import ingest_all

scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(ingest_all, IntervalTrigger(minutes=15), id="ingest", replace_existing=True)
    scheduler.start()
