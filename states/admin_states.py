from aiogram.fsm.state import StatesGroup, State

class AdminSchedule(StatesGroup):
    choosing_date_for_add = State()
    choosing_date_for_view = State()
    choosing_date_for_delete = State()
    choosing_date_for_cancel_app = State()
    entering_slots = State()

class AdminSettings(StatesGroup):
    entering_price = State()
    entering_portfolio = State()
    entering_channel_id = State()
    entering_channel_link = State()

class AdminManagement(StatesGroup):
    adding_admin = State()
