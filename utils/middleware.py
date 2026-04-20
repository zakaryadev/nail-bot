import os
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from config import settings

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        bot = data["bot"]
        db_path = os.path.join(settings.BOTS_DATA_DIR, f"bot_{bot.id}.db")
        data["db_path"] = db_path
        return await handler(event, data)
