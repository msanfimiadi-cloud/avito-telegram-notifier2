from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_chat import TelegramChat


@dataclass(frozen=True)
class RegistrationResult:
    chat: TelegramChat
    created: bool
    reactivated: bool
    already_active: bool


class TelegramChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_chat_id(self, chat_id: int) -> TelegramChat | None:
        result = await self.session.execute(select(TelegramChat).where(TelegramChat.chat_id == chat_id))
        return result.scalar_one_or_none()

    async def is_registered(self, chat_id: int) -> bool:
        chat = await self.get_by_chat_id(chat_id)
        return bool(chat and chat.is_active)

    async def register_chat(
        self,
        *,
        chat_id: int,
        title: str | None,
        chat_type: str,
        registered_by_user_id: int,
        registered_by_username: str | None,
    ) -> RegistrationResult:
        chat = await self.get_by_chat_id(chat_id)
        if chat is None:
            chat = TelegramChat(
                chat_id=chat_id,
                title=title,
                chat_type=chat_type,
                registered_by_user_id=registered_by_user_id,
                registered_by_username=registered_by_username,
                is_active=True,
            )
            self.session.add(chat)
            await self.session.commit()
            await self.session.refresh(chat)
            return RegistrationResult(chat=chat, created=True, reactivated=False, already_active=False)

        was_active = chat.is_active
        chat.title = title
        chat.chat_type = chat_type
        chat.registered_by_user_id = registered_by_user_id
        chat.registered_by_username = registered_by_username
        chat.is_active = True
        chat.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(chat)
        return RegistrationResult(chat=chat, created=False, reactivated=not was_active, already_active=was_active)
