from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from datetime import date, datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database import crud
from keyboards import builders
from states.user_states import Booking
from utils.filters import ChatMemberFilter
from utils.scheduler import schedule_reminder_job, remove_reminder_job
from utils.locales import _t

router = Router()

async def get_channel_id() -> int:
    channel_id_str = await crud.get_setting("channel_id", str(settings.CHANNEL_ID))
    try:
        return int(channel_id_str)
    except ValueError:
        return settings.CHANNEL_ID

async def get_channel_link() -> str:
    return await crud.get_setting("channel_link", settings.CHANNEL_LINK)

# --- Обработка команды /start и проверка подписки ---

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Обработчик команды /start."""
    user_info = await crud.get_or_create_user(message.from_user.id)
    # unpack tuple based on length to be safe, but we know it returns 5 elements now
    is_new = user_info[-1]
    lang = user_info[3] if len(user_info) > 3 else 'ru'
    
    # If the user is new, ask for language first and stop here.
    if is_new:
        await message.answer(
            _t(lang, 'choose_lang'),
            reply_markup=builders.language_menu()
        )
        return
    
    channel_id = await get_channel_id()
    channel_link = await get_channel_link()
    
    # Проверка подписки
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=message.from_user.id)
        is_subscribed = member.status in ["member", "administrator", "creator"]
    except Exception:
        # Если бот не админ или ID неверный, пускаем
        is_subscribed = True

    if is_subscribed:
        await message.answer(
            _t(lang, 'welcome'),
            reply_markup=builders.main_menu(lang)
        )
    else:
        await message.answer(
            _t(lang, 'subscribe_prompt'),
            reply_markup=builders.subscribe_menu(channel_link, lang)
        )

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    """Обработчик кнопки проверки подписки."""
    channel_id = await get_channel_id()
    channel_link = await get_channel_link()
    
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=callback.from_user.id)
        is_subscribed = member.status in ["member", "administrator", "creator"]
    except Exception:
        is_subscribed = True

    lang = await crud.get_user_language(callback.from_user.id)

    if is_subscribed:
        await callback.message.edit_text(
            _t(lang, 'subscribed_success'),
            reply_markup=builders.main_menu(lang)
        )
    else:
        await callback.answer(_t(lang, 'not_subscribed'), show_alert=True)


# Блокировка сообщений от неподписанных пользователей
@router.message(ChatMemberFilter())
@router.callback_query(ChatMemberFilter())
async def handle_blocked_user(update: Message | CallbackQuery):
    """Обработчик для пользователей без подписки."""
    message = update if isinstance(update, Message) else update.message
    channel_link = await get_channel_link()
    lang = await crud.get_user_language(message.from_user.id)
    
    await message.answer(
        _t(lang, 'subscribe_prompt'),
        reply_markup=builders.subscribe_menu(channel_link, lang)
    )


# --- Основное меню ---

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        _t(lang, 'main_menu_title'),
        reply_markup=builders.main_menu(lang)
    )

@router.callback_query(F.data == "change_lang")
async def change_lang_menu(callback: CallbackQuery):
    """Меню выбора языка."""
    lang = await crud.get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        _t(lang, 'choose_lang'),
        reply_markup=builders.language_menu()
    )

@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    """Обработчик выбора языка."""
    lang = callback.data.split(":")[1]
    await crud.set_user_language(callback.from_user.id, lang)
    
    channel_id = await get_channel_id()
    channel_link = await get_channel_link()
    
    try:
        member = await callback.bot.get_chat_member(chat_id=channel_id, user_id=callback.from_user.id)
        is_subscribed = member.status in ["member", "administrator", "creator"]
    except Exception:
        is_subscribed = True

    if is_subscribed:
        await callback.message.edit_text(
            _t(lang, 'lang_changed') + "\n\n" + _t(lang, 'main_menu_title'),
            reply_markup=builders.main_menu(lang)
        )
    else:
        await callback.message.edit_text(
            _t(lang, 'lang_changed') + "\n\n" + _t(lang, 'subscribe_prompt'),
            reply_markup=builders.subscribe_menu(channel_link, lang)
        )

@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery):
    """Показывает прайс-лист."""
    lang = await crud.get_user_language(callback.from_user.id)
    # The default price is stored in settings, but we might want to localize it if we didn't customize it.
    # We will use the translation for default, but if it's customized, it might be in Russian.
    default_price = _t(lang, 'price_text')
    text = await crud.get_setting("price_text", default_price)
    if text == "<b>✨ Прайс-лист</b>\n\n💅 <i>Маникюр + гель-лак</i> — <b>1500₽</b>\n💅 <i>Наращивание</i> — <b>2500₽</b>\n💅 <i>Френч / Дизайн</i> — <b>+300₽</b>\n💅 <i>Снятие чужой работы</i> — <b>200₽</b>":
        text = default_price
        
    await callback.message.edit_text(text, reply_markup=builders.back_to_main_menu_kb(lang))

@router.callback_query(F.data == "portfolio")
async def show_portfolio(callback: CallbackQuery):
    """Показывает ссылку на портфолио."""
    lang = await crud.get_user_language(callback.from_user.id)
    portfolio_link = await crud.get_setting("portfolio_link", "https://ru.pinterest.com/crystalwithluv/_created/")
    await callback.message.edit_text(
        _t(lang, 'portfolio_text'),
        reply_markup=builders.portfolio_menu(portfolio_link, lang)
    )


# --- Процесс записи (FSM) ---

@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начало процесса записи. Проверка на существующую запись."""
    lang = await crud.get_user_language(callback.from_user.id)
    appointment = await crud.get_user_appointment(callback.from_user.id)
    if appointment:
        await callback.answer(_t(lang, 'already_booked'), show_alert=True)
        return

    await state.set_state(Booking.choosing_date)
    today = date.today()
    calendar_kb = await builders.calendar(today.year, today.month, lang)
    await callback.message.edit_text(_t(lang, 'choose_date'), reply_markup=calendar_kb)

@router.callback_query(Booking.choosing_date, F.data.startswith("calendar_"))
async def process_calendar(callback: CallbackQuery, state: FSMContext):
    """Обработка навигации по календарю и выбора даты."""
    lang = await crud.get_user_language(callback.from_user.id)
    action, year, month, day = callback.data.split(":")[1:]
    year, month, day = int(year), int(month), int(day)
    
    if action == "ignore":
        await callback.answer()
        return

    if action == "prev" or action == "next":
        calendar_kb = await builders.calendar(year, month, lang)
        await callback.message.edit_text(_t(lang, 'choose_date'), reply_markup=calendar_kb)
        return

    if action == "day":
        selected_date = date(year, month, day)
        if selected_date < date.today():
            await callback.answer(_t(lang, 'past_date'), show_alert=True)
            return
        
        free_slots = await crud.get_free_slots_for_date(selected_date.strftime("%Y-%m-%d"))
        if not free_slots:
            await callback.answer(_t(lang, 'no_slots'), show_alert=True)
            return

        await state.update_data(selected_date=selected_date.strftime("%Y-%m-%d"))
        await state.set_state(Booking.choosing_time)
        text = _t(lang, 'date_selected', date=selected_date.strftime('%d.%m.%Y'))
        await callback.message.edit_text(text, reply_markup=builders.time_slots(free_slots, lang))

@router.callback_query(Booking.choosing_time, F.data.startswith("time_"))
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени."""
    lang = await crud.get_user_language(callback.from_user.id)
    selected_time = callback.data.replace("time_:", "")
    await state.update_data(selected_time=selected_time)
    await state.set_state(Booking.entering_name)
    await callback.message.edit_text(_t(lang, 'enter_name'))

@router.message(Booking.entering_name, F.text)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени."""
    lang = await crud.get_user_language(message.from_user.id)
    await state.update_data(name=message.text)
    await state.set_state(Booking.entering_phone)
    await message.answer(_t(lang, 'enter_phone'))

@router.message(Booking.entering_phone, F.text)
async def process_phone(message: Message, state: FSMContext, bot: Bot, apscheduler: AsyncIOScheduler):
    """Обработка ввода телефона и завершение записи."""
    lang = await crud.get_user_language(message.from_user.id)
    user_data = await state.get_data()
    name = user_data["name"]
    phone = message.text
    selected_date = user_data["selected_date"]
    selected_time = user_data["selected_time"]

    await crud.update_user_info(message.from_user.id, name, phone)
    
    result = await crud.book_slot(message.from_user.id, selected_date, selected_time)
    if not result:
        await message.answer(_t(lang, 'slot_taken'), reply_markup=builders.back_to_main_menu_kb(lang))
        await state.clear()
        return
        
    appointment_id, _ = result
    
    await state.clear()

    user_text = _t(lang, 'booking_success', name=name, date=selected_date, time=selected_time)
    await message.answer(user_text, reply_markup=builders.main_menu(lang))

    admin_lang = await crud.get_user_language(settings.ADMIN_ID)
    
    admin_text = _t(admin_lang, 'admin_notif_new', name=name, phone=phone, date=selected_date, time=selected_time, user_id=message.from_user.id)
    await bot.send_message(settings.ADMIN_ID, admin_text)
    
    admin_channel_text = _t(admin_lang, 'admin_notif_slot_taken', date=selected_date, time=selected_time)
    await bot.send_message(settings.ADMIN_CHANNEL_ID, admin_channel_text)
    
    appointment_datetime = datetime.strptime(f"{selected_date} {selected_time}", "%Y-%m-%d %H:%M")
    await schedule_reminder_job(apscheduler, bot, message.from_user.id, appointment_id, appointment_datetime)


# --- Просмотр и отмена записи ---

@router.callback_query(F.data == "my_appointment")
async def show_my_appointment(callback: CallbackQuery):
    """Показывает активную запись пользователя."""
    lang = await crud.get_user_language(callback.from_user.id)
    appointment = await crud.get_user_appointment(callback.from_user.id)
    if appointment:
        appointment_id, app_date, app_time = appointment
        text = _t(lang, 'my_app_info', date=app_date, time=app_time)
        await callback.message.edit_text(text, reply_markup=builders.cancel_appointment_kb(appointment_id, lang))
    else:
        await callback.message.edit_text(_t(lang, 'no_apps'), reply_markup=builders.back_to_main_menu_kb(lang))

@router.callback_query(F.data.startswith("cancel_"))
async def cancel_my_appointment(callback: CallbackQuery, apscheduler: AsyncIOScheduler, bot: Bot):
    """Отмена записи пользователем."""
    lang = await crud.get_user_language(callback.from_user.id)
    appointment_id = int(callback.data.split(":")[1])
    
    app_info = "???"
    appointment = await crud.get_user_appointment(callback.from_user.id)
    if appointment:
        _, app_date, app_time = appointment
        app_info = f"{app_date} {app_time}"
        
    await crud.cancel_appointment(appointment_id)
    
    await remove_reminder_job(apscheduler, f"reminder_{callback.from_user.id}_{appointment_id}")
    
    await callback.message.edit_text(_t(lang, 'app_canceled'), reply_markup=builders.back_to_main_menu_kb(lang))
    
    try:
        admin_lang = await crud.get_user_language(settings.ADMIN_ID)
        admin_notif = _t(admin_lang, 'admin_notif_canceled', date=app_date, time=app_time) if appointment else _t(admin_lang, 'admin_notif_canceled', date="???", time="???")
        await bot.send_message(settings.ADMIN_CHANNEL_ID, admin_notif)
    except Exception:
        pass
