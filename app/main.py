import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.config.settings import get_config
from app.logging.setup import configure_logging
from app.routers.health import router as health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = get_config()
    configure_logging(config.log_level)
    logger.info("Application startup completed")
    yield
    logger.info("Application shutdown completed")


def create_app() -> FastAPI:
    config = get_config()
    application = FastAPI(
        title=config.app_name,
        version="0.1.0",
        docs_url="/docs" if config.app_env != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.include_router(health_router)
    return application


app = create_app()
