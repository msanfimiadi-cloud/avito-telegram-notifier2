import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.avito.client import AvitoAuthClient
from app.avito.token_cache import AvitoTokenCache
from app.config.settings import Config, get_config
from app.database.session import get_session
from app.security.encryption import SecretCipher
from app.services.avito_account_service import AvitoAccountService

_token_cache = AvitoTokenCache()
_auth_client = AvitoAuthClient()


def get_token_cache() -> AvitoTokenCache:
    return _token_cache


def get_secret_cipher(config: Config = Depends(get_config)) -> SecretCipher:
    return SecretCipher(config.app_encryption_key.get_secret_value())


async def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"), config: Config = Depends(get_config)) -> None:
    expected = config.admin_api_key.get_secret_value()
    if x_admin_key is None or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


def get_avito_account_service(
    session: AsyncSession = Depends(get_session),
    cipher: SecretCipher = Depends(get_secret_cipher),
    token_cache: AvitoTokenCache = Depends(get_token_cache),
) -> AvitoAccountService:
    return AvitoAccountService(session, cipher, token_cache, _auth_client)
