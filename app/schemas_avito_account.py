from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class AvitoAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    profile_id: int
    client_id: str = Field(min_length=1, max_length=255)
    client_secret: SecretStr = Field(repr=False)


class AvitoAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    profile_id: int | None = None
    client_id: str | None = Field(default=None, min_length=1, max_length=255)
    client_secret: SecretStr | None = Field(default=None, repr=False)


class AvitoAccountRead(BaseModel):
    id: int
    name: str
    profile_id: int
    client_id: str
    is_active: bool
    token_status: str
    last_token_check_at: datetime | None
    last_token_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AvitoVerifyResponse(BaseModel):
    success: bool
    status: str
    message: str
