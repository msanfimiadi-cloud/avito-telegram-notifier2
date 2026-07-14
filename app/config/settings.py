from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class Config(BaseModel):
    app_name: str = Field(default="Avito Telegram Notifier", alias="APP_NAME")
    app_env: str = Field(default="production", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    avito_accounts_config_path: Path = Field(
        default=Path("config/avito_accounts.yml"),
        alias="AVITO_ACCOUNTS_CONFIG_PATH",
    )

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        allowed_values = {"development", "staging", "production"}
        if value not in allowed_values:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(allowed_values))}")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed_values = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed_values:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed_values))}")
        return normalized

    model_config = ConfigDict(populate_by_name=True, frozen=True)


@lru_cache(maxsize=1)
def get_config() -> Config:
    load_dotenv(override=False)
    try:
        return Config.model_validate(os.environ)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid application configuration: {exc}") from exc
