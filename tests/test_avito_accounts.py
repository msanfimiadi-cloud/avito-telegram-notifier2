import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.avito.client import AvitoAuthClient
from app.avito.exceptions import AvitoInvalidCredentialsError, AvitoRateLimitError, AvitoResponseValidationError, AvitoTemporaryError
from app.avito.token_cache import AvitoTokenCache, CachedAccessToken
from app.config.settings import Config
from app.database.base import Base
from app.database.session import get_session
from app.dependencies import get_avito_account_service
from app.models.avito_account import AvitoAccount
from app.routers.admin_avito_accounts import router
from app.schemas_avito_account import AvitoAccountCreate, AvitoAccountUpdate
from app.security.encryption import EncryptionError, SecretCipher
from app.services.avito_account_service import AvitoAccountConflictError, AvitoAccountService

TEST_KEY = "wC704B5NND5bAoho95Lsqv_sAtVfJ_lLgfHzG4YQrHs="
OTHER_KEY = "xGyJVtKRQHb2eTqWm81mjy11fMRxFWrU_RosZrrdoyA="


@pytest.fixture()
async def sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield maker
    finally:
        await engine.dispose()


@pytest.fixture()
def cipher():
    return SecretCipher(TEST_KEY)


@pytest.fixture()
def token_cache():
    return AvitoTokenCache()


class FakeAuthClient:
    def __init__(self, *, fail=None):
        self.calls = 0
        self.fail = fail
    async def fetch_access_token(self, *, client_id, client_secret):
        self.calls += 1
        if self.fail:
            raise self.fail
        return SimpleNamespace(token_value=f"token-{self.calls}", expires_at=datetime.now(timezone.utc) + timedelta(hours=1))


async def make_service(sessionmaker, cipher, token_cache, auth_client=None):
    session = sessionmaker()
    return AvitoAccountService(session, cipher, token_cache, auth_client or FakeAuthClient()), session


def payload(profile_id=436756553, client_id="test-client"):
    return AvitoAccountCreate(name="Авито 2 Ликвидация", profile_id=profile_id, client_id=client_id, client_secret="test-secret")


def test_encrypt_decrypt(cipher):
    encrypted = cipher.encrypt("test-secret")
    assert encrypted != "test-secret"
    assert cipher.decrypt(encrypted) == "test-secret"


def test_decrypt_with_wrong_key_fails(cipher):
    encrypted = cipher.encrypt("test-secret")
    with pytest.raises(EncryptionError):
        SecretCipher(OTHER_KEY).decrypt(encrypted)


@pytest.mark.asyncio
async def test_create_account_secret_encrypted(sessionmaker, cipher, token_cache):
    service, session = await make_service(sessionmaker, cipher, token_cache)
    account = await service.create_account(payload())
    assert account.id == 1
    assert account.client_secret_encrypted != "test-secret"
    db_account = await session.get(AvitoAccount, account.id)
    assert "test-secret" not in db_account.client_secret_encrypted
    await session.close()


@pytest.mark.asyncio
async def test_unique_profile_and_client_id(sessionmaker, cipher, token_cache):
    service, session = await make_service(sessionmaker, cipher, token_cache)
    await service.create_account(payload())
    with pytest.raises(AvitoAccountConflictError):
        await service.create_account(payload(client_id="other"))
    with pytest.raises(AvitoAccountConflictError):
        await service.create_account(payload(profile_id=2))
    await session.close()


@pytest.mark.asyncio
async def test_activate_deactivate(sessionmaker, cipher, token_cache):
    service, session = await make_service(sessionmaker, cipher, token_cache)
    account = await service.create_account(payload())
    assert (await service.deactivate_account(account.id)).is_active is False
    assert (await service.activate_account(account.id)).is_active is True
    await session.close()


@pytest.mark.asyncio
async def test_verify_success_and_invalid(sessionmaker, cipher, token_cache):
    service, session = await make_service(sessionmaker, cipher, token_cache, FakeAuthClient())
    account = await service.create_account(payload())
    assert await service.verify_credentials(account.id) == (True, "valid", "Подключение к Avito успешно проверено")
    service.auth_client = FakeAuthClient(fail=AvitoInvalidCredentialsError("safe"))
    success, status, _ = await service.verify_credentials(account.id)
    assert success is False and status == "invalid"
    await session.close()


@pytest.mark.asyncio
async def test_token_cache_behaviour_and_invalidation(sessionmaker, cipher, token_cache):
    fake = FakeAuthClient()
    service, session = await make_service(sessionmaker, cipher, token_cache, fake)
    account = await service.create_account(payload())
    assert await service.get_access_token(account.id) == "token-1"
    assert await service.get_access_token(account.id) == "token-1"
    assert fake.calls == 1
    token_cache._tokens[account.id] = CachedAccessToken("old", datetime.now(timezone.utc) + timedelta(seconds=30))
    assert await service.get_access_token(account.id) == "token-2"
    await service.update_account(account.id, AvitoAccountUpdate(client_secret="new-secret"))
    assert account.id not in token_cache._tokens
    await session.close()


@pytest.mark.asyncio
async def test_parallel_refresh_single_call():
    cache = AvitoTokenCache()
    calls = 0
    async def refresh():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return CachedAccessToken("token", datetime.now(timezone.utc) + timedelta(hours=1))
    results = await asyncio.gather(*(cache.get_or_refresh(1, refresh) for _ in range(10)))
    assert {r.access_token for r in results} == {"token"}
    assert calls == 1


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=False):
        self.status_code = status_code; self.payload = payload or {}; self.json_error = json_error
    def json(self):
        if self.json_error: raise ValueError("bad json")
        return self.payload


class FakeAsyncClient:
    response = FakeResponse(payload={"access_token":"tok","token_type":"Bearer","expires_in":86400})
    error = None
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def post(self, *args, **kwargs):
        if self.error: raise self.error
        return self.response


@pytest.mark.asyncio
@pytest.mark.parametrize("response,exc", [
    (FakeResponse(400, {}), AvitoInvalidCredentialsError),
    (FakeResponse(429, {}), AvitoRateLimitError),
    (FakeResponse(500, {}), AvitoTemporaryError),
    (FakeResponse(200, {}, True), AvitoResponseValidationError),
    (FakeResponse(200, {"access_token":"tok"}), AvitoResponseValidationError),
])
async def test_avito_auth_client_errors(monkeypatch, response, exc):
    FakeAsyncClient.response = response; FakeAsyncClient.error = None
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    with pytest.raises(exc):
        await AvitoAuthClient().fetch_access_token(client_id="id", client_secret="secret")


@pytest.mark.asyncio
async def test_avito_auth_timeout(monkeypatch):
    FakeAsyncClient.error = httpx.TimeoutException("timeout")
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    with pytest.raises(AvitoTemporaryError):
        await AvitoAuthClient().fetch_access_token(client_id="id", client_secret="secret")
    FakeAsyncClient.error = None


@pytest.fixture()
async def admin_app(sessionmaker, cipher, token_cache):
    app = FastAPI()
    app.include_router(router)
    async def override_session():
        async with sessionmaker() as session:
            yield session
    def override_service(session=pytest.MonkeyPatch):
        raise AssertionError
    app.dependency_overrides[get_session] = override_session
    from app.config.settings import get_config
    app.dependency_overrides[get_config] = lambda: Config.model_validate({"TELEGRAM_BOT_TOKEN":"123:test","APP_ENCRYPTION_KEY":TEST_KEY,"ADMIN_API_KEY":"admin-key"})
    return app


@pytest.mark.asyncio
async def test_admin_key_and_response_hides_secret(admin_app):
    transport = ASGITransport(app=admin_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        data = {"name":"Авито 2 Ликвидация","profile_id":436756553,"client_id":"client","client_secret":"secret"}
        assert (await client.get("/api/v1/admin/avito-accounts")).status_code == 401
        assert (await client.get("/api/v1/admin/avito-accounts", headers={"X-Admin-Key":"bad"})).status_code == 401
        response = await client.post("/api/v1/admin/avito-accounts", json=data, headers={"X-Admin-Key":"admin-key"})
        assert response.status_code == 201
        body = response.json()
        assert "client_secret" not in body and "access_token" not in body
        assert body["client_id"] == "client"


@pytest.mark.asyncio
async def test_alembic_unique_constraints(sessionmaker, cipher):
    async with sessionmaker() as session:
        encrypted = cipher.encrypt("secret")
        session.add_all([
            AvitoAccount(name="one", profile_id=1, client_id="same", client_secret_encrypted=encrypted),
            AvitoAccount(name="two", profile_id=2, client_id="same", client_secret_encrypted=encrypted),
        ])
        with pytest.raises(IntegrityError):
            await session.commit()
