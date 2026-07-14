from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.avito.client import AvitoAuthClient
from app.avito.exceptions import AvitoAuthError, AvitoInvalidCredentialsError, AvitoRateLimitError, AvitoTemporaryError
from app.avito.token_cache import AvitoTokenCache, CachedAccessToken
from app.models.avito_account import AvitoAccount
from app.schemas_avito_account import AvitoAccountCreate, AvitoAccountUpdate
from app.security.encryption import SecretCipher


class AvitoAccountError(ValueError):
    pass


class AvitoAccountNotFoundError(AvitoAccountError):
    pass


class AvitoAccountConflictError(AvitoAccountError):
    pass


class AvitoAccountService:
    def __init__(self, session: AsyncSession, cipher: SecretCipher, token_cache: AvitoTokenCache, auth_client: AvitoAuthClient | None = None) -> None:
        self.session = session
        self.cipher = cipher
        self.token_cache = token_cache
        self.auth_client = auth_client or AvitoAuthClient()

    async def create_account(self, payload: AvitoAccountCreate) -> AvitoAccount:
        account = AvitoAccount(
            name=payload.name,
            profile_id=payload.profile_id,
            client_id=payload.client_id,
            client_secret_encrypted=self.cipher.encrypt(payload.client_secret.get_secret_value()),
        )
        self.session.add(account)
        await self._commit_or_conflict()
        await self.session.refresh(account)
        return account

    async def get_account(self, account_id: int) -> AvitoAccount:
        account = await self.session.get(AvitoAccount, account_id)
        if account is None:
            raise AvitoAccountNotFoundError("Avito account not found")
        return account

    async def get_account_by_profile_id(self, profile_id: int) -> AvitoAccount | None:
        return (await self.session.execute(select(AvitoAccount).where(AvitoAccount.profile_id == profile_id))).scalar_one_or_none()

    async def list_accounts(self) -> list[AvitoAccount]:
        return list((await self.session.execute(select(AvitoAccount).order_by(AvitoAccount.id))).scalars().all())

    async def update_account(self, account_id: int, payload: AvitoAccountUpdate) -> AvitoAccount:
        account = await self.get_account(account_id)
        changed_credentials = False
        for field in ("name", "profile_id", "client_id"):
            value = getattr(payload, field)
            if value is not None:
                setattr(account, field, value)
                changed_credentials = changed_credentials or field in {"client_id", "profile_id"}
        if payload.client_secret is not None:
            account.client_secret_encrypted = self.cipher.encrypt(payload.client_secret.get_secret_value())
            changed_credentials = True
        if changed_credentials:
            account.token_status = "unknown"
            account.last_token_error = None
            self.token_cache.invalidate(account.id)
        await self._commit_or_conflict()
        await self.session.refresh(account)
        return account

    async def activate_account(self, account_id: int) -> AvitoAccount:
        account = await self.get_account(account_id)
        account.is_active = True
        await self.session.commit(); await self.session.refresh(account); return account

    async def deactivate_account(self, account_id: int) -> AvitoAccount:
        account = await self.get_account(account_id)
        account.is_active = False
        self.token_cache.invalidate(account.id)
        await self.session.commit(); await self.session.refresh(account); return account

    async def delete_account(self, account_id: int) -> None:
        account = await self.get_account(account_id)
        await self.session.delete(account)
        self.token_cache.invalidate(account.id)
        await self.session.commit()

    async def verify_credentials(self, account_id: int) -> tuple[bool, str, str]:
        account = await self.get_account(account_id)
        now = datetime.now(timezone.utc)
        try:
            secret = self.cipher.decrypt(account.client_secret_encrypted)
            token = await self.auth_client.fetch_access_token(client_id=account.client_id, client_secret=secret)
            self.token_cache.invalidate(account.id)
            self.token_cache._tokens[account.id] = CachedAccessToken(token.token_value, token.expires_at)  # nosec internal cache
            account.token_status = "valid"; account.last_token_error = None
            result = (True, "valid", "Подключение к Avito успешно проверено")
        except AvitoInvalidCredentialsError:
            account.token_status = "invalid"; account.last_token_error = "Avito rejected the provided credentials"
            result = (False, "invalid", "Avito отклонил указанные credentials")
        except (AvitoRateLimitError, AvitoTemporaryError, AvitoAuthError) as exc:
            account.token_status = "error"; account.last_token_error = str(exc)
            result = (False, "error", "Временная ошибка проверки Avito")
        account.last_token_check_at = now
        await self.session.commit(); await self.session.refresh(account)
        return result

    async def get_access_token(self, account_id: int) -> str:
        account = await self.get_account(account_id)
        if not account.is_active:
            raise AvitoAccountError("Avito account is inactive")
        async def refresh() -> CachedAccessToken:
            secret = self.cipher.decrypt(account.client_secret_encrypted)
            token = await self.auth_client.fetch_access_token(client_id=account.client_id, client_secret=secret)
            return CachedAccessToken(token.token_value, token.expires_at)
        return (await self.token_cache.get_or_refresh(account.id, refresh)).access_token

    async def _commit_or_conflict(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AvitoAccountConflictError("Avito account with this profile_id or client_id already exists") from exc
