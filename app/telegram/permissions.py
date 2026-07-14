import logging
from collections.abc import Sequence

from telegram import Bot, Chat, Update
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

ADMIN_STATUSES = {"creator", "administrator"}
GROUP_TYPES = {Chat.GROUP, Chat.SUPERGROUP}


class PermissionCheckError(Exception):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


def is_group_chat(chat_type: str) -> bool:
    return chat_type in GROUP_TYPES


async def ensure_register_allowed(update: Update, bot: Bot, admin_ids: Sequence[int]) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        raise PermissionCheckError("Не удалось определить чат или пользователя.")

    if not is_group_chat(chat.type):
        raise PermissionCheckError("Эту команду необходимо выполнить внутри Telegram-группы.")

    if user.id not in admin_ids:
        try:
            member = await bot.get_chat_member(chat.id, user.id)
        except TelegramError as exc:
            logger.warning("Failed to check Telegram user permissions: chat_id=%s user_id=%s error=%s", chat.id, user.id, exc)
            raise PermissionCheckError("Не удалось проверить права пользователя в Telegram-группе.") from exc
        if member.status not in ADMIN_STATUSES:
            raise PermissionCheckError("Регистрация доступна только администратору группы или владельцу.")

    try:
        bot_member = await bot.get_chat_member(chat.id, bot.id)
    except TelegramError as exc:
        logger.warning("Failed to check bot permissions: chat_id=%s user_id=%s error=%s", chat.id, user.id, exc)
        raise PermissionCheckError("Не удалось проверить права бота в этой группе. Убедитесь, что бот добавлен в группу.") from exc

    if bot_member.status in {"left", "kicked"}:
        raise PermissionCheckError("Бот удалён из группы или заблокирован. Добавьте бота снова.")
    if bot_member.status == "restricted" and getattr(bot_member, "can_send_messages", True) is False:
        raise PermissionCheckError("Боту запрещено отправлять сообщения в этой группе.")


async def ensure_chat_info_allowed(update: Update, bot: Bot, admin_ids: Sequence[int]) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        raise PermissionCheckError("Не удалось определить чат или пользователя.")
    if not is_group_chat(chat.type):
        raise PermissionCheckError("Эту команду необходимо выполнить внутри Telegram-группы.")
    if user.id in admin_ids:
        return
    try:
        member = await bot.get_chat_member(chat.id, user.id)
    except TelegramError as exc:
        logger.warning("Failed to check /chatid permissions: chat_id=%s user_id=%s error=%s", chat.id, user.id, exc)
        raise PermissionCheckError("Не удалось проверить права пользователя в Telegram-группе.") from exc
    if member.status not in ADMIN_STATUSES:
        raise PermissionCheckError("Команда доступна только администратору группы или владельцу.")
