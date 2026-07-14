from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import ValidationError

from app.avito.exceptions import (
    AvitoInvalidCredentialsError,
    AvitoRateLimitError,
    AvitoResponseValidationError,
    AvitoTemporaryError,
)
from app.avito.schemas import AvitoTokenResponse

AVITO_TOKEN_URL = "https://api.avito.ru/token"


class AvitoAuthClient:
    def __init__(self, token_url: str = AVITO_TOKEN_URL, timeout: float = 10.0) -> None:
        self.token_url = token_url
        self.timeout = httpx.Timeout(timeout)

    async def fetch_access_token(self, *, client_id: str, client_secret: str) -> AvitoTokenResponse:
        data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        received_at = datetime.now(timezone.utc)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.token_url, data=data, headers=headers)
        except httpx.TimeoutException as exc:
            raise AvitoTemporaryError("Avito token request timed out") from exc
        except httpx.RequestError as exc:
            raise AvitoTemporaryError("Avito token endpoint is unavailable") from exc

        if response.status_code in {400, 401, 403}:
            raise AvitoInvalidCredentialsError("Avito rejected the provided credentials")
        if response.status_code == 429:
            raise AvitoRateLimitError("Avito token rate limit exceeded")
        if 500 <= response.status_code <= 599:
            raise AvitoTemporaryError("Avito token endpoint returned a temporary server error")
        if response.status_code >= 400:
            raise AvitoTemporaryError("Avito token endpoint returned an unexpected HTTP error")

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise AvitoResponseValidationError("Avito token response is not valid JSON") from exc
        try:
            return AvitoTokenResponse.model_validate(payload).with_expires_at(received_at)
        except ValidationError as exc:
            raise AvitoResponseValidationError("Avito token response is missing required fields") from exc
