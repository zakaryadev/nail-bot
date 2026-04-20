from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from datetime import date, datetime, timedelta
import calendar as py_calendar
import re

from database import crud
from utils.locales import _t

def strip_html(text: str) -> str:
    """Удаляет HTML-теги из строки."""
    return re.sub(r'<[^>]*>', '', text)

def language_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Русский 🇷🇺", callback_data="lang_:ru")
    builder.button(text="O'zbek 🇺🇿", callback_data="lang_:uz")
    builder.button(text="Qaraqalpaq", callback_data="lang_:kaa")
    builder.adjust(1)
    return builder.as_markup()

def main_menu(lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_book'), callback_data="book")
    builder.button(text=_t(lang, 'btn_my_app'), callback_data="my_appointment")
    builder.button(text=_t(lang, 'btn_prices'), callback_data="prices")
    builder.button(text=_t(lang, 'btn_portfolio'), callback_data="portfolio")
    builder.button(text=_t(lang, 'btn_change_lang'), callback_data="change_lang")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def subscribe_menu(channel_link: str, lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_subscribe'), url=channel_link)
    builder.button(text=_t(lang, 'btn_check_sub'), callback_data="check_subscription")
    return builder.as_markup()

def portfolio_menu(portfolio_link: str, lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_portfolio_link'), url=portfolio_link)
    builder.button(text=_t(lang, 'btn_back'), callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()
    
def back_to_main_menu_kb(lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_back_menu'), callback_data="main_menu")
    return builder.as_markup()

async def calendar(year: int, month: int, lang='ru'):
    builder = InlineKeyboardBuilder()
    
    # Названия месяцев
    months_ru = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    months_uz = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]
    months_kaa = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]
    
    if lang == 'uz':
        months = months_uz
    elif lang == 'kaa':
        months = months_kaa
    else:
        months = months_ru
    
    # Кнопка с месяцем и годом
    builder.button(text=f"{months[month-1]} {year}", callback_data="calendar_:ignore:0:0:0")
    
    # Кнопки навигации
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    builder.button(text="«", callback_data=f"calendar_:prev:{prev_year}:{prev_month}:0")
    builder.button(text="»", callback_data=f"calendar_:next:{next_year}:{next_month}:0")
    
    # Дни недели
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    days_uz = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    days_kaa = ["Dú", "Si", "Sá", "Pi", "Ju", "Sh", "Ek"]
    
    if lang == 'uz':
        days = days_uz
    elif lang == 'kaa':
        days = days_kaa
    else:
        days = days_ru
    
    for day in days:
        builder.button(text=day, callback_data="calendar_:ignore:0:0:0")
    
    # Даты
    cal = py_calendar.monthcalendar(year, month)
    today = date.today()
    
    # Получаем даты со свободными слотами
    free_dates_db = await crud.get_free_dates(today)
    free_dates = {datetime.strptime(d, "%Y-%m-%d").date() for d in free_dates_db}

    for week in cal:
        for day in week:
            if day == 0:
                builder.button(text=" ", callback_data="calendar_:ignore:0:0:0")
            else:
                current_date = date(year, month, day)
                if current_date < today:
                    # Прошедшие дни неактивны
                    builder.button(text=f"~{day}~", callback_data="calendar_:ignore:0:0:0")
                elif current_date in free_dates:
                    # Дни со свободными слотами
                    builder.button(text=f"✅ {day}", callback_data=f"calendar_:day:{year}:{month}:{day}")
                else:
                    # Дни без слотов
                    builder.button(text=str(day), callback_data="calendar_:ignore:0:0:0")

    builder.adjust(3, 7, 7, 7, 7, 7, 7, 1) # Гибкая настройка сетки
    builder.row(back_to_main_menu_kb(lang).inline_keyboard[0][0])
    return builder.as_markup()


def time_slots(slots: list, lang='ru'):
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot, callback_data=f"time_:{slot}")
    builder.adjust(3)
    # Кнопка "назад" для возврата к выбору даты
    builder.row(InlineKeyboardButton(text=_t(lang, 'btn_choose_other_date'), callback_data="book"))
    return builder.as_markup()

def cancel_appointment_kb(appointment_id: int, lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_cancel_app'), callback_data=f"cancel_:{appointment_id}")
    builder.button(text=_t(lang, 'btn_back'), callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def admin_menu(user_id: int, lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_admin_add_slots'), callback_data="add_slots")
    builder.button(text=_t(lang, 'btn_admin_delete_slots'), callback_data="delete_slots")
    builder.button(text=_t(lang, 'btn_admin_view_schedule'), callback_data="view_schedule")
    builder.button(text=_t(lang, 'btn_admin_cancel_app'), callback_data="admin_cancel_start")
    builder.button(text=_t(lang, 'btn_admin_settings'), callback_data="bot_settings")
    
    # Только для главного администратора
    from config import settings
    if user_id == settings.ADMIN_ID:
        builder.button(text=_t(lang, 'btn_admin_manage_admins'), callback_data="manage_admins")
        
    builder.adjust(1)
    return builder.as_markup()

def admin_manage_admins_kb(lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_admin_add_admin'), callback_data="add_admin")
    builder.button(text=_t(lang, 'btn_admin_remove_admin'), callback_data="remove_admin")
    builder.button(text=_t(lang, 'btn_admin_back'), callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

async def admin_remove_admins_kb(admin_ids: list[int], lang='ru'):
    builder = InlineKeyboardBuilder()
    for admin_id in admin_ids:
        # Можно добавить получение имени из БД, но пока просто ID
        builder.button(text=f"❌ {admin_id}", callback_data=f"del_admin:{admin_id}")
    builder.button(text=_t(lang, 'btn_admin_back'), callback_data="manage_admins")
    builder.adjust(1)
    return builder.as_markup()

def admin_settings_menu(lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_admin_edit_price'), callback_data="edit_price")
    builder.button(text=_t(lang, 'btn_admin_edit_portfolio'), callback_data="edit_portfolio")
    builder.button(text=_t(lang, 'btn_admin_edit_channel_id'), callback_data="edit_channel_id")
    builder.button(text=_t(lang, 'btn_admin_edit_channel_link'), callback_data="edit_channel_link")
    builder.button(text=_t(lang, 'btn_admin_back'), callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def back_to_admin_settings_kb(lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_admin_back_settings'), callback_data="bot_settings")
    return builder.as_markup()

def back_to_admin_menu_kb(lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text=_t(lang, 'btn_admin_back_menu'), callback_data="admin_menu")
    return builder.as_markup()

def admin_calendar(year: int, month: int, lang='ru'):
    builder = InlineKeyboardBuilder()
    
    # Названия месяцев
    months_ru = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    months_uz = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]
    months_kaa = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]
    
    if lang == 'uz':
        months = months_uz
    elif lang == 'kaa':
        months = months_kaa
    else:
        months = months_ru
    
    # Кнопка с месяцем и годом
    builder.button(text=f"{months[month-1]} {year}", callback_data="admin_cal_:ignore:0:0:0")
    
    # Кнопки навигации
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    builder.button(text="«", callback_data=f"admin_cal_:prev:{prev_year}:{prev_month}:0")
    builder.button(text="»", callback_data=f"admin_cal_:next:{next_year}:{next_month}:0")
    
    # Дни недели
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    days_uz = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    days_kaa = ["Dú", "Si", "Sá", "Pi", "Ju", "Sh", "Ek"]
    
    if lang == 'uz':
        days = days_uz
    elif lang == 'kaa':
        days = days_kaa
    else:
        days = days_ru
        
    for day in days:
        builder.button(text=day, callback_data="admin_cal_:ignore:0:0:0")
    
    # Даты
    cal = py_calendar.monthcalendar(year, month)
    today = date.today()
    
    for week in cal:
        for day in week:
            if day == 0:
                builder.button(text=" ", callback_data="admin_cal_:ignore:0:0:0")
            else:
                current_date = date(year, month, day)
                if current_date < today:
                    # Прошедшие дни неактивны
                    builder.button(text=f"~{day}~", callback_data="admin_cal_:ignore:0:0:0")
                else:
                    # Все будущие дни активны для админа
                    builder.button(text=str(day), callback_data=f"admin_cal_:day:{year}:{month}:{day}")

    builder.adjust(3, 7, 7, 7, 7, 7, 7, 1) # Гибкая настройка сетки
    builder.row(back_to_admin_menu_kb(lang).inline_keyboard[0][0])
    return builder.as_markup()

    builder.row(back_to_admin_menu_kb(lang).inline_keyboard[0][0])
    return builder.as_markup()

def admin_schedule_kb(schedule_data: list, lang='ru', date=''):
    """Клавиатура для просмотра расписания с возможностью отмены записей."""
    builder = InlineKeyboardBuilder()
    
    for time_val, is_booked, name, phone, app_id in schedule_data:
        if is_booked:
            label = _t(lang, 'admin_slot_booked', time=time_val, name=name, phone='').split('(')[0].strip()
            builder.button(text=strip_html(label), callback_data=f"confirm_cancel:{app_id}")
        else:
            label = _t(lang, 'admin_slot_free', time=time_val)
            builder.button(text=strip_html(label), callback_data="ignore")
            
    builder.adjust(2)
    builder.row(back_to_admin_menu_kb(lang).inline_keyboard[0][0])
    return builder.as_markup()

def admin_confirm_cancel_kb(app_id: int, lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ " + _t(lang, 'btn_yes_cancel'), callback_data=f"admin_cancel_app:{app_id}")
    builder.button(text="❌ " + _t(lang, 'btn_no_stay'), callback_data="admin_menu")
    builder.adjust(2)
    return builder.as_markup()

def admin_delete_slots_kb(slots: list[tuple[int, str]], lang='ru', date_str=''):
    """Клавиатура для удаления свободных слотов."""
    builder = InlineKeyboardBuilder()
    for slot_id, time_val in slots:
        builder.button(text=f"❌ {time_val}", callback_data=f"del_slot:{slot_id}")
    
    # Кнопка для очистки всего дня
    builder.row(InlineKeyboardButton(text=_t(lang, 'btn_admin_clear_day'), callback_data=f"clear_day:{date_str}"))
    builder.row(back_to_admin_menu_kb(lang).inline_keyboard[0][0])
    builder.adjust(3)
    return builder.as_markup()
