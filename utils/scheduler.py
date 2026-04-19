from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from datetime import datetime, timedelta
import logging

from database import crud

logger = logging.getLogger(__name__)

async def send_reminder(bot: Bot, user_id: int, time: str):
    """Отправляет напоминание пользователю."""
    try:
        await bot.send_message(
            user_id,
            f"💅 Напоминаем, что вы записаны на маникюр завтра в <b>{time}</b>. Ждём вас! ✨"
        )
        logger.info(f"Отправлено напоминание пользователю {user_id}.")
    except Exception as e:
        logger.error(f"Не удалось отправить напоминание пользователю {user_id}: {e}")

async def schedule_reminder_job(scheduler: AsyncIOScheduler, bot: Bot, user_id: int, appointment_id: int, appointment_datetime: datetime):
    """Планирует отправку напоминания за 24 часа."""
    reminder_time = appointment_datetime - timedelta(hours=24)
    
    if reminder_time > datetime.now():
        job_id = f"reminder_{user_id}_{appointment_id}"
        scheduler.add_job(
            send_reminder,
            'date',
            run_date=reminder_time,
            args=[bot, user_id, appointment_datetime.strftime('%H:%M')],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Запланировано напоминание (ID: {job_id}) на {reminder_time}")
    else:
        logger.info(f"Запись на {appointment_datetime} менее чем за 24 часа, напоминание не запланировано.")

async def remove_reminder_job(scheduler: AsyncIOScheduler, job_id: str):
    """Удаляет задачу из планировщика."""
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"Задача {job_id} успешно удалена.")
    except Exception as e:
        logger.error(f"Ошибка при удалении задачи {job_id}: {e}")

async def restore_scheduled_jobs(scheduler: AsyncIOScheduler, bot: Bot):
    """Восстанавливает задачи из БД при перезапуске бота."""
    logger.info("Начинаем восстановление задач из БД...")
    active_appointments = await crud.get_all_active_appointments()
    count = 0
    for app_id, user_id, app_date, app_time in active_appointments:
        try:
            appointment_datetime = datetime.strptime(f"{app_date} {app_time}", "%Y-%m-%d %H:%M")
            await schedule_reminder_job(scheduler, bot, user_id, app_id, appointment_datetime)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при восстановлении задачи для записи {app_id}: {e}")
    logger.info(f"Восстановлено {count} задач.")
