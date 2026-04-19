from aiogram.fsm.state import StatesGroup, State

class Booking(StatesGroup):
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
