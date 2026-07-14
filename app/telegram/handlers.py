import logging
from html import escape

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from telegram import Update
from telegram.ext import ContextTypes

from app.config.settings import Config
from app.services.telegram_chat_service import TelegramChatService
from app.telegram.permissions import PermissionCheckError, ensure_chat_info_allowed, ensure_register_allowed, is_group_chat

logger = logging.getLogger(__name__)


def _message(update: Update):
    return update.effective_message


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = _message(update)
    if chat is not None and is_group_chat(chat.type):
        await message.reply_text("Для регистрации этой группы выполните /register.")
        return
    await message.reply_text(
        "Бот предназначен для отправки уведомлений о новых сообщениях Avito.\n\n"
        "Чтобы зарегистрировать Telegram-группу:\n\n"
        "1. Добавьте бота в группу.\n"
        "2. Разрешите ему отправлять сообщения.\n"
        "3. Выполните в группе команду /register."
    )


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    sessionmaker: async_sessionmaker[AsyncSession] = context.application.bot_data["sessionmaker"]
    message = _message(update)
    try:
        await ensure_register_allowed(update, context.bot, config.telegram_admin_ids)
    except PermissionCheckError as exc:
        await message.reply_text(exc.user_message)
        return

    chat = update.effective_chat
    user = update.effective_user
    async with sessionmaker() as session:
        result = await TelegramChatService(session).register_chat(
            chat_id=chat.id,
            title=chat.title,
            chat_type=chat.type,
            registered_by_user_id=user.id,
            registered_by_username=user.username,
        )
    if result.already_active:
        await message.reply_text(f"✅ Группа уже зарегистрирована\n\nНазвание: {chat.title}\nChat ID: {chat.id}")
        return
    await message.reply_text(
        f"✅ Группа зарегистрирована\n\nНазвание: {chat.title}\nChat ID: {chat.id}\n\n"
        "Теперь эту группу можно связать с аккаунтом Avito."
    )


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    sessionmaker: async_sessionmaker[AsyncSession] = context.application.bot_data["sessionmaker"]
    message = _message(update)
    try:
        await ensure_chat_info_allowed(update, context.bot, config.telegram_admin_ids)
    except PermissionCheckError as exc:
        await message.reply_text(exc.user_message)
        return
    chat = update.effective_chat
    async with sessionmaker() as session:
        registered = await TelegramChatService(session).is_registered(chat.id)
    await message.reply_text(
        f"Название: {chat.title}\nChat ID: {chat.id}\nТип чата: {chat.type}\n"
        f"Зарегистрирована: {'да' if registered else 'нет'}"
    )


async def telegram_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
    user_id = getattr(getattr(update, "effective_user", None), "id", None)
    logger.exception("Telegram handler error: event_type=%s chat_id=%s user_id=%s error=%s", type(update).__name__, chat_id, user_id, context.error)
