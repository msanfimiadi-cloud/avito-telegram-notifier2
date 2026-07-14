from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator


class Config(BaseModel):
    app_name: str = Field(default="Avito Telegram Notifier", alias="APP_NAME")
    app_env: str = Field(default="production", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_ids: tuple[int, ...] = Field(default=(), alias="TELEGRAM_ADMIN_IDS")
    database_url: str = Field(default="sqlite+aiosqlite:///./data/app.db", alias="DATABASE_URL")
    app_encryption_key: SecretStr = Field(alias="APP_ENCRYPTION_KEY", repr=False)
    admin_api_key: SecretStr = Field(alias="ADMIN_API_KEY", repr=False)

    @field_validator("telegram_admin_ids", mode="before")
    @classmethod
    def parse_telegram_admin_ids(cls, value: object) -> tuple[int, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            ids: list[int] = []
            for item in value.split(","):
                stripped = item.strip()
                if not stripped:
                    continue
                if not stripped.isdigit():
                    raise ValueError("TELEGRAM_ADMIN_IDS must contain comma-separated integer user IDs")
                ids.append(int(stripped))
            return tuple(ids)
        if isinstance(value, (list, tuple, set)):
            return tuple(int(item) for item in value)
        raise ValueError("TELEGRAM_ADMIN_IDS must be a comma-separated list")

    @field_validator("telegram_bot_token", "app_encryption_key", "admin_api_key")
    @classmethod
    def validate_required_secret(cls, value: str | SecretStr) -> str | SecretStr:
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else value
        if not raw_value.strip():
            raise ValueError("required secret setting must not be empty")
        return value

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
