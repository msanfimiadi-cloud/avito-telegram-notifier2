import logging
import sys


class LevelPrefixFormatter(logging.Formatter):
    LEVEL_PREFIXES = {
        "DEBUG": "🔎 DEBUG",
        "INFO": "✅ INFO",
        "WARNING": "⚠️ WARNING",
        "ERROR": "❌ ERROR",
        "CRITICAL": "🚨 CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.levelprefix = self.LEVEL_PREFIXES.get(record.levelname, record.levelname)
        return super().format(record)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        LevelPrefixFormatter(
            fmt="%(asctime)s | %(levelprefix)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.error").handlers.clear()
