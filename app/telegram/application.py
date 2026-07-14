import logging

from telegram.ext import Application, ApplicationBuilder, CommandHandler

from app.config.settings import Config
from app.database.session import get_sessionmaker
from app.telegram.handlers import chatid_command, register_command, start_command, telegram_error_handler

logger = logging.getLogger(__name__)


def build_telegram_application(config: Config) -> Application:
    application = ApplicationBuilder().token(config.telegram_bot_token).build()
    application.bot_data["config"] = config
    application.bot_data["sessionmaker"] = get_sessionmaker()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("register", register_command))
    application.add_handler(CommandHandler("chatid", chatid_command))
    application.add_error_handler(telegram_error_handler)
    return application


class TelegramBotRunner:
    def __init__(self, config: Config) -> None:
        self.application = build_telegram_application(config)

    async def start(self) -> None:
        try:
            await self.application.initialize()
            await self.application.start()
            if self.application.updater is None:
                raise RuntimeError("Telegram updater is not available")
            await self.application.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot polling started")
        except Exception:
            logger.exception("Failed to start Telegram bot. Check TELEGRAM_BOT_TOKEN and network access; token is not logged.")
            await self.stop()
            raise

    async def stop(self) -> None:
        updater = self.application.updater
        if updater is not None and updater.running:
            await updater.stop()
        if self.application.running:
            await self.application.stop()
        await self.application.shutdown()
        logger.info("Telegram bot stopped")
