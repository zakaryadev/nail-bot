from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from typing import Union
from aiogram import Bot

from config import settings
from database import crud

class AdminFilter(Filter):
    """Фильтр для проверки, является ли пользователь администратором."""
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id == settings.ADMIN_ID


class ChatMemberFilter(Filter):
    """
    Фильтр для блокировки пользователей, не подписанных на канал.
    """
    def __init__(self, chat_id: int = None):
        self.chat_id = chat_id

    async def __call__(self, update: Union[Message, CallbackQuery, ChatMemberUpdated], bot: Bot) -> bool:
        user_id = update.from_user.id
        
        # Получаем ID канала из БД, если нет - берем из конфига
        channel_id_str = await crud.get_setting("channel_id", str(settings.CHANNEL_ID))
        try:
            target_chat_id = int(channel_id_str)
        except ValueError:
            target_chat_id = settings.CHANNEL_ID
        
        try:
            member = await bot.get_chat_member(chat_id=target_chat_id, user_id=user_id)
            # Возвращаем True, если пользователь НЕ подписан (чтобы заблокировать)
            return member.status not in ["member", "administrator", "creator"]
        except Exception:
            # Если бот не админ в канале или другая ошибка - считаем, что проверки нет
            return False
