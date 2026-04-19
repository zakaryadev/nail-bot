from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

async def set_bot_commands(bot: Bot):
    """Устанавливает команды, видимые в меню Telegram."""
    commands = [
        BotCommand(command="start", description="🚀 Перезапустить бота"),
        BotCommand(command="admin", description="⚙️ Панель администратора"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
