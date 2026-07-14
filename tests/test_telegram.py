from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram import Chat

from app.config.settings import Config
from app.database.base import Base
from app.models.telegram_chat import TelegramChat
from app.services.telegram_chat_service import TelegramChatService
from app.telegram.handlers import chatid_command, register_command


class FakeMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeBot:
    id = 999

    def __init__(self, user_status: str = "administrator", bot_status: str = "member", can_send: bool = True) -> None:
        self.user_status = user_status
        self.bot_status = bot_status
        self.can_send = can_send
        self.get_chat_member = AsyncMock(side_effect=self._get_chat_member)

    async def _get_chat_member(self, chat_id: int, user_id: int):
        if user_id == self.id:
            return SimpleNamespace(status=self.bot_status, can_send_messages=self.can_send)
        return SimpleNamespace(status=self.user_status)


@pytest.fixture()
def config() -> Config:
    return Config.model_validate({"TELEGRAM_BOT_TOKEN": "123:test", "TELEGRAM_ADMIN_IDS": "111, 222"})


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


def make_update(*, chat_id=-1001, chat_type=Chat.SUPERGROUP, title="Test Group", user_id=111, username="admin"):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id, type=chat_type, title=title),
        effective_user=SimpleNamespace(id=user_id, username=username),
        effective_message=FakeMessage(),
    )


def make_context(config: Config, sessionmaker, bot: FakeBot):
    return SimpleNamespace(application=SimpleNamespace(bot_data={"config": config, "sessionmaker": sessionmaker}), bot=bot)


def test_parse_telegram_admin_ids() -> None:
    cfg = Config.model_validate({"TELEGRAM_BOT_TOKEN": "123:test", "TELEGRAM_ADMIN_IDS": "123, 456,789"})
    assert cfg.telegram_admin_ids == (123, 456, 789)


@pytest.mark.asyncio
async def test_register_forbidden_in_private_chat(config, sessionmaker) -> None:
    update = make_update(chat_type=Chat.PRIVATE, title=None)
    await register_command(update, make_context(config, sessionmaker, FakeBot()))
    assert update.effective_message.replies == ["Эту команду необходимо выполнить внутри Telegram-группы."]


@pytest.mark.asyncio
async def test_register_forbidden_for_regular_member(config, sessionmaker) -> None:
    update = make_update(user_id=333)
    await register_command(update, make_context(config, sessionmaker, FakeBot(user_status="member")))
    assert update.effective_message.replies == ["Регистрация доступна только администратору группы или владельцу."]


@pytest.mark.asyncio
async def test_successful_register_by_admin(config, sessionmaker) -> None:
    update = make_update(user_id=333)
    await register_command(update, make_context(config, sessionmaker, FakeBot(user_status="administrator")))
    assert "✅ Группа зарегистрирована" in update.effective_message.replies[0]
    async with sessionmaker() as session:
        chat = await TelegramChatService(session).get_by_chat_id(-1001)
    assert chat is not None
    assert chat.title == "Test Group"


@pytest.mark.asyncio
async def test_repeat_register_without_duplicate(config, sessionmaker) -> None:
    context = make_context(config, sessionmaker, FakeBot(user_status="administrator"))
    await register_command(make_update(user_id=333), context)
    update = make_update(user_id=333)
    await register_command(update, context)
    assert "✅ Группа уже зарегистрирована" in update.effective_message.replies[0]
    async with sessionmaker() as session:
        all_chats = (await session.execute(__import__("sqlalchemy").select(TelegramChat))).scalars().all()
    assert len(all_chats) == 1


@pytest.mark.asyncio
async def test_register_restores_inactive_chat(config, sessionmaker) -> None:
    async with sessionmaker() as session:
        session.add(TelegramChat(chat_id=-1001, title="Old", chat_type=Chat.SUPERGROUP, registered_by_user_id=1, is_active=False))
        await session.commit()
    await register_command(make_update(user_id=333, title="New"), make_context(config, sessionmaker, FakeBot(user_status="administrator")))
    async with sessionmaker() as session:
        chat = await TelegramChatService(session).get_by_chat_id(-1001)
    assert chat.is_active is True
    assert chat.title == "New"


@pytest.mark.asyncio
async def test_chatid_command(config, sessionmaker) -> None:
    async with sessionmaker() as session:
        await TelegramChatService(session).register_chat(chat_id=-1001, title="Test Group", chat_type=Chat.SUPERGROUP, registered_by_user_id=111, registered_by_username="admin")
    update = make_update()
    await chatid_command(update, make_context(config, sessionmaker, FakeBot()))
    assert "Chat ID: -1001" in update.effective_message.replies[0]
    assert "Зарегистрирована: да" in update.effective_message.replies[0]


@pytest.mark.asyncio
async def test_unique_chat_id_constraint(sessionmaker) -> None:
    async with sessionmaker() as session:
        session.add(TelegramChat(chat_id=-1001, title="One", chat_type=Chat.SUPERGROUP, registered_by_user_id=1))
        session.add(TelegramChat(chat_id=-1001, title="Two", chat_type=Chat.SUPERGROUP, registered_by_user_id=2))
        with pytest.raises(IntegrityError):
            await session.commit()
