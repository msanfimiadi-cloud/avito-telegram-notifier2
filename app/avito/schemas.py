from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, SecretStr, field_validator


class AvitoTokenResponse(BaseModel):
    access_token: SecretStr = Field(repr=False)
    token_type: str
    expires_in: int
    expires_at: datetime | None = None

    @field_validator("expires_in")
    @classmethod
    def validate_expires_in(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("expires_in must be positive")
        return value

    def with_expires_at(self, received_at: datetime | None = None) -> "AvitoTokenResponse":
        base = received_at or datetime.now(timezone.utc)
        return self.model_copy(update={"expires_at": base + timedelta(seconds=self.expires_in)})

    @property
    def token_value(self) -> str:
        return self.access_token.get_secret_value()
