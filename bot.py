import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database import crud, master_crud
from handlers import admin, user
from utils import commands, scheduler, middleware

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    Основная функция для запуска бота.
    """
    # Инициализация диспетчера
    dp = Dispatcher()

    # Регистрация мидлварей
    dp.update.middleware(middleware.DbSessionMiddleware())

    # Инициализация планировщика
    apscheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Включение роутеров
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Инициализация мастер-БД и получение активных ботов
    await master_crud.init_master_db()
    active_bots_data = await master_crud.get_active_bots()
    logger.info(f"Найдено {len(active_bots_data)} активных ботов в мастер-БД.")

    bots = []
    
    # Инициализация "Мастер-бота" (по умолчанию из настроек)
    master_bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    master_bot_info = await master_bot.get_me()
    master_db_path = os.path.join(settings.BOTS_DATA_DIR, f"bot_{master_bot_info.id}.db")
    
    await crud.init_db(master_db_path)
    await scheduler.restore_scheduled_jobs(apscheduler, master_bot, db_path=master_db_path)
    await commands.set_bot_commands(master_bot)
    await master_bot.delete_webhook(drop_pending_updates=True)
    
    bots.append(master_bot)
    logger.info(f"Мастер-бот @{master_bot_info.username} инициализирован.")

    # Инициализация дополнительных ботов
    for bot_data in active_bots_data:
        if bot_data['token'] == settings.BOT_TOKEN:
            continue
            
        try:
            bot = Bot(token=bot_data['token'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            bot_info = await bot.get_me()
            db_path = os.path.join(settings.BOTS_DATA_DIR, f"bot_{bot_info.id}.db")
            
            await crud.init_db(db_path)
            await scheduler.restore_scheduled_jobs(apscheduler, bot, db_path=db_path)
            await commands.set_bot_commands(bot)
            await bot.delete_webhook(drop_pending_updates=True)
            
            bots.append(bot)
            logger.info(f"Бот @{bot_info.username} (ID: {bot_data['id']}) инициализирован.")
        except Exception as e:
            logger.error(f"Ошибка при инициализации бота {bot_data['id']}: {e}")

    apscheduler.start()
    logger.info("Планировщик запущен.")

    # Запуск поллинга для всех ботов
    logger.info(f"Запуск поллинга для {len(bots)} ботов.")
    await dp.start_polling(*bots, apscheduler=apscheduler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
