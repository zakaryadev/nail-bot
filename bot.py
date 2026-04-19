import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database import crud
from handlers import admin, user
from utils import commands, scheduler

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    Основная функция для запуска бота.
    """
    # Инициализация бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Инициализация планировщика
    apscheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Включение роутеров
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Инициализация базы данных
    await crud.init_db()
    logger.info("База данных инициализирована.")

    # Установка команд бота
    await commands.set_bot_commands(bot)
    logger.info("Команды бота установлены.")

    # Восстановление задач планировщика
    await scheduler.restore_scheduled_jobs(apscheduler, bot)
    logger.info("Задачи планировщика восстановлены.")
    apscheduler.start()

    # Удаление вебхука и запуск поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен и готов к работе.")
    await dp.start_polling(bot, apscheduler=apscheduler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
