import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable


@dataclass(frozen=True)
class CachedAccessToken:
    access_token: str
    expires_at: datetime


class AvitoTokenCache:
    def __init__(self, safety_window_seconds: int = 60) -> None:
        self._tokens: dict[int, CachedAccessToken] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._safety_window = timedelta(seconds=safety_window_seconds)

    def invalidate(self, account_id: int) -> None:
        self._tokens.pop(account_id, None)

    def _is_valid(self, token: CachedAccessToken) -> bool:
        return token.expires_at - self._safety_window > datetime.now(timezone.utc)

    async def get_or_refresh(self, account_id: int, refresh: Callable[[], Awaitable[CachedAccessToken]]) -> CachedAccessToken:
        token = self._tokens.get(account_id)
        if token and self._is_valid(token):
            return token
        lock = self._locks.setdefault(account_id, asyncio.Lock())
        async with lock:
            token = self._tokens.get(account_id)
            if token and self._is_valid(token):
                return token
            token = await refresh()
            self._tokens[account_id] = token
            return token
