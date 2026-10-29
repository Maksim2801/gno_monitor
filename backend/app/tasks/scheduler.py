import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.analytics.pipeline import AnalyticsPipeline
from app.core.config import get_settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def run_scheduled_analytics() -> None:
    db = SessionLocal()
    try:
        stats = AnalyticsPipeline(db).run()
        logger.info("Scheduled analytics finished: %s", stats)
    except Exception:
        logger.exception("Scheduled analytics failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return
    scheduler.add_job(
        run_scheduled_analytics,
        "interval",
        minutes=max(settings.analytics_interval_minutes, 5),
        id="analytics_job",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "APScheduler started, interval=%s min", settings.analytics_interval_minutes
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
