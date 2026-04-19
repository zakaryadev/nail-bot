from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import date, datetime, timedelta
import os
import re
import html

from config import settings
from database import crud
from keyboards import builders
from utils.filters import AdminFilter
from utils.locales import _t
from states.admin_states import AdminSchedule, AdminSettings

router = Router()
router.message.filter(AdminFilter())

@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    """Отображает админ-панель."""
    await state.clear()
    lang = await crud.get_user_language(message.from_user.id)
    await message.answer(_t(lang, 'admin_welcome'), reply_markup=builders.admin_menu(lang))

@router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню администратора."""
    await state.clear()
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(_t(lang, 'admin_panel_title'), reply_markup=builders.admin_menu(lang))

# === НАСТРОЙКИ БОТА ===

@router.callback_query(F.data == "bot_settings")
async def bot_settings_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(_t(lang, 'admin_settings_title'), reply_markup=builders.admin_settings_menu(lang))

@router.callback_query(F.data == "edit_price")
async def edit_price_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSettings.entering_price)
    lang = await crud.get_user_language(callback.from_user.id)
    default_price = _t(lang, 'price_text')
    current_price = await crud.get_setting("price_text", default_price)
    escaped_price = html.escape(current_price)
    text = _t(lang, 'admin_edit_price_prompt', escaped_price=escaped_price)
    await callback.message.edit_text(text, reply_markup=builders.back_to_admin_settings_kb(lang))

@router.message(AdminSettings.entering_price, F.text)
async def process_new_price(message: Message, state: FSMContext):
    await crud.set_setting("price_text", message.text)
    await state.clear()
    lang = await crud.get_user_language(message.from_user.id)
    await message.answer(_t(lang, 'admin_price_updated'), reply_markup=builders.admin_settings_menu(lang))

@router.callback_query(F.data == "edit_portfolio")
async def edit_portfolio_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSettings.entering_portfolio)
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(_t(lang, 'admin_edit_portfolio_prompt'), reply_markup=builders.back_to_admin_settings_kb(lang))

@router.message(AdminSettings.entering_portfolio, F.text)
async def process_new_portfolio(message: Message, state: FSMContext):
    await crud.set_setting("portfolio_link", message.text)
    await state.clear()
    lang = await crud.get_user_language(message.from_user.id)
    await message.answer(_t(lang, 'admin_portfolio_updated'), reply_markup=builders.admin_settings_menu(lang))

@router.callback_query(F.data == "edit_channel_id")
async def edit_channel_id_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSettings.entering_channel_id)
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(_t(lang, 'admin_edit_channel_id_prompt'), reply_markup=builders.back_to_admin_settings_kb(lang))

@router.message(AdminSettings.entering_channel_id, F.text)
async def process_new_channel_id(message: Message, state: FSMContext):
    await crud.set_setting("channel_id", message.text)
    await state.clear()
    lang = await crud.get_user_language(message.from_user.id)
    await message.answer(_t(lang, 'admin_channel_id_updated'), reply_markup=builders.admin_settings_menu(lang))

@router.callback_query(F.data == "edit_channel_link")
async def edit_channel_link_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSettings.entering_channel_link)
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(_t(lang, 'admin_edit_channel_link_prompt'), reply_markup=builders.back_to_admin_settings_kb(lang))

@router.message(AdminSettings.entering_channel_link, F.text)
async def process_new_channel_link(message: Message, state: FSMContext):
    await crud.set_setting("channel_link", message.text)
    await state.clear()
    lang = await crud.get_user_language(message.from_user.id)
    await message.answer(_t(lang, 'admin_channel_link_updated'), reply_markup=builders.admin_settings_menu(lang))

# === РАСПИСАНИЕ ===

@router.callback_query(F.data == "add_slots")
async def add_slots_handler(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс добавления слотов с выбора даты."""
    await state.set_state(AdminSchedule.choosing_date_for_add)
    today = date.today()
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        _t(lang, 'admin_choose_date_add'),
        reply_markup=builders.admin_calendar(today.year, today.month, lang)
    )

@router.callback_query(F.data == "view_schedule")
async def view_schedule_handler(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс просмотра расписания с выбора даты."""
    await state.set_state(AdminSchedule.choosing_date_for_view)
    today = date.today()
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        _t(lang, 'admin_choose_date_view'),
        reply_markup=builders.admin_calendar(today.year, today.month, lang)
    )

@router.callback_query(F.data == "delete_slots")
async def delete_slots_handler(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс удаления слотов с выбора даты."""
    await state.set_state(AdminSchedule.choosing_date_for_delete)
    today = date.today()
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        _t(lang, 'admin_choose_date_del'),
        reply_markup=builders.admin_calendar(today.year, today.month, lang)
    )

@router.callback_query(F.data.startswith("admin_cal_"))
async def process_admin_calendar(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатия на календарь администратора."""
    action, year, month, day = callback.data.split(":")[1:]
    year, month, day = int(year), int(month), int(day)
    lang = await crud.get_user_language(callback.from_user.id)
    
    if action == "ignore":
        await callback.answer()
        return

    if action == "prev" or action == "next":
        await callback.message.edit_text(
            _t(lang, 'admin_choose_date'),
            reply_markup=builders.admin_calendar(year, month, lang)
        )
        return

    if action == "day":
        selected_date = date(year, month, day)
        if selected_date < date.today():
            await callback.answer(_t(lang, 'admin_past_date'), show_alert=True)
            return
            
        current_state = await state.get_state()
        
        if current_state == AdminSchedule.choosing_date_for_add.state:
            # Переходим к вводу времени
            await state.update_data(selected_date=selected_date.strftime("%Y-%m-%d"))
            await state.set_state(AdminSchedule.entering_slots)
            
            text = _t(lang, 'admin_enter_slots_prompt', date=selected_date.strftime('%d.%m.%Y'))
            await callback.message.edit_text(text, reply_markup=builders.back_to_admin_menu_kb(lang))
            
        elif current_state == AdminSchedule.choosing_date_for_view.state:
            # Показываем расписание на выбранный день
            today_str = selected_date.strftime("%Y-%m-%d")
            async with crud.aiosqlite.connect(crud.DB_NAME) as db:
                cursor = await db.execute("""
                    SELECT s.time, s.is_booked, u.name, u.phone
                    FROM schedule s
                    LEFT JOIN appointments a ON s.id = a.schedule_id
                    LEFT JOIN users u ON a.user_id = u.id
                    WHERE s.date = ?
                    ORDER BY s.time
                """, (today_str,))
                schedule_data = await cursor.fetchall()

            if not schedule_data:
                text = _t(lang, 'admin_schedule_empty', date=today_str)
            else:
                header = _t(lang, 'admin_schedule_header', date=today_str)
                schedule_lines = []
                for time_val, is_booked, name, phone in schedule_data:
                    if is_booked:
                        schedule_lines.append(_t(lang, 'admin_slot_booked', time=time_val, name=name, phone=phone))
                    else:
                        schedule_lines.append(_t(lang, 'admin_slot_free', time=time_val))
                
                body = os.linesep.join(schedule_lines)
                text = header + os.linesep + os.linesep + body
            
            await state.clear()
            await callback.message.edit_text(text, reply_markup=builders.back_to_admin_menu_kb(lang))
            
        elif current_state == AdminSchedule.choosing_date_for_delete.state:
            # Показываем список свободных слотов для удаления
            today_str = selected_date.strftime("%Y-%m-%d")
            free_slots = await crud.get_free_slots_with_ids(today_str)
            
            if not free_slots:
                await callback.answer(_t(lang, 'admin_no_free_slots_to_delete', date=today_str), show_alert=True)
                return
                
            text = _t(lang, 'admin_delete_slots_prompt', date=today_str)
            await callback.message.edit_text(
                text,
                reply_markup=builders.admin_delete_slots_kb(free_slots, lang, today_str)
            )

@router.message(AdminSchedule.entering_slots, F.text)
async def process_slots_input(message: Message, state: FSMContext):
    """Парсит введенный текст и добавляет слоты в базу данных."""
    user_data = await state.get_data()
    selected_date = user_data["selected_date"]
    lang = await crud.get_user_language(message.from_user.id)
    
    # Регулярное выражение для поиска времени в формате ЧЧ:ММ
    times = re.findall(r'\b(?:[01]?\d|2[0-3]):[0-5]\d\b', message.text)
    
    if not times:
        await message.answer(
            _t(lang, 'admin_invalid_slots'),
            reply_markup=builders.back_to_admin_menu_kb(lang)
        )
        return
    
    # Форматируем слоты, добавляя ведущий ноль (9:00 -> 09:00)
    formatted_times = []
    for t in times:
        h, m = t.split(":")
        formatted_times.append(f"{int(h):02d}:{m}")
        
    # Удаляем дубликаты и привязываем к дате
    unique_times = sorted(list(set(formatted_times)))
    slots_to_add = [(selected_date, t) for t in unique_times]
    
    # Записываем в БД
    await crud.add_schedule_slots(slots_to_add)
    await state.clear()
    
    added_slots_str = ", ".join(unique_times)
    await message.answer(
        _t(lang, 'admin_slots_added', count=len(slots_to_add), date=selected_date, slots=added_slots_str),
        reply_markup=builders.admin_menu(lang)
    )

@router.callback_query(F.data.startswith("del_slot:"))
async def process_delete_slot(callback: CallbackQuery):
    """Удаляет конкретный слот."""
    slot_id = int(callback.data.split(":")[1])
    lang = await crud.get_user_language(callback.from_user.id)
    
    # Сначала найдем время слота для сообщения
    async with crud.aiosqlite.connect(crud.DB_NAME) as db:
        cursor = await db.execute("SELECT date, time FROM schedule WHERE id = ?", (slot_id,))
        result = await cursor.fetchone()
        
    if not result:
        await callback.answer("Слот не найден или уже удален.", show_alert=True)
        return
        
    date_str, time_str = result
    await crud.delete_schedule_slot(slot_id)
    
    # Обновляем клавиатуру
    free_slots = await crud.get_free_slots_with_ids(date_str)
    
    await callback.answer(_t(lang, 'admin_slot_deleted', time=time_str))
    
    text = _t(lang, 'admin_delete_slots_prompt', date=date_str)
    if not free_slots:
        text = _t(lang, 'admin_no_free_slots_to_delete', date=date_str)
        
    await callback.message.edit_text(
        text,
        reply_markup=builders.admin_delete_slots_kb(free_slots, lang, date_str)
    )

@router.callback_query(F.data.startswith("clear_day:"))
async def process_clear_day(callback: CallbackQuery):
    """Очищает все свободные слоты на день."""
    date_str = callback.data.split(":")[1]
    lang = await crud.get_user_language(callback.from_user.id)
    
    await crud.delete_all_free_slots(date_str)
    
    await callback.answer(_t(lang, 'admin_day_cleared', date=date_str), show_alert=True)
    
    text = _t(lang, 'admin_no_free_slots_to_delete', date=date_str)
    await callback.message.edit_text(
        text,
        reply_markup=builders.admin_delete_slots_kb([], lang, date_str)
    )
