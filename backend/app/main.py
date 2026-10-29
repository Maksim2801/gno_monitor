import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.seed import seed_database
from app.db.session import SessionLocal
from app.tasks.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            stats = seed_database(db)
            logger.info("Seed completed: %s", stats)
            # Run initial analytics if predictions empty
            from app.models import PredictionResult
            from app.analytics.pipeline import AnalyticsPipeline

            if db.query(PredictionResult).count() == 0:
                logger.info("Running initial analytics pass...")
                AnalyticsPipeline(db).run()
        except Exception:
            logger.exception("Startup seed/analytics failed")
            db.rollback()
        finally:
            db.close()
    try:
        start_scheduler()
    except Exception:
        logger.exception("Failed to start scheduler")
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Веб-приложение мониторинга и предиктивной аналитики "
            "глубинно-насосного оборудования нефтяных скважин"
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
