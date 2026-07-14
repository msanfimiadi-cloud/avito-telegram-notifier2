import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_config
from app.database.session import dispose_engine
from app.logging.setup import configure_logging
from app.routers.health import router as health_router
from app.telegram.application import TelegramBotRunner

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = get_config()
    configure_logging(config.log_level)
    bot_runner = TelegramBotRunner(config)
    app.state.telegram_bot_runner = bot_runner
    await bot_runner.start()
    logger.info("Application startup completed")
    try:
        yield
    finally:
        await bot_runner.stop()
        await dispose_engine()
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
