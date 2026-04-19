import aiosqlite
from datetime import date, datetime

DB_NAME = "nail_bot.db"

async def init_db():
    """Инициализирует базу данных и создает таблицы, если их нет."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT,
                language TEXT DEFAULT 'ru'
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                is_booked INTEGER DEFAULT 0,
                UNIQUE(date, time)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                schedule_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (schedule_id) REFERENCES schedule (id) ON DELETE CASCADE
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Migration: add language column if it doesn't exist
        try:
            await db.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru'")
        except aiosqlite.OperationalError:
            pass # Column already exists
            
        await db.commit()

async def get_setting(key: str, default: str = None) -> str:
    """Получает настройку из БД."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        if row:
            return row[0]
        return default

async def set_setting(key: str, value: str):
    """Сохраняет настройку в БД."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

# --- Функции для работы с пользователями ---
async def get_or_create_user(user_id: int, name: str = None, phone: str = None):
    """Получает или создает пользователя в БД."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
            await db.execute("INSERT INTO users (id, name, phone, language) VALUES (?, ?, ?, 'ru')", (user_id, name, phone))
            await db.commit()
            return user_id, name, phone, 'ru', True
        return (*user, False)

async def update_user_info(user_id: int, name: str, phone: str):
    """Обновляет имя и телефон пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, user_id))
        await db.commit()

async def get_user_language(user_id: int) -> str:
    """Возвращает язык пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT language FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 'ru'

async def set_user_language(user_id: int, language: str):
    """Устанавливает язык пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
        await db.commit()

# --- Функции для работы с расписанием ---
async def add_schedule_slots(slots: list[tuple[str, str]]):
    """Добавляет временные слоты в расписание. Игнорирует дубликаты."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executemany("INSERT OR IGNORE INTO schedule (date, time) VALUES (?, ?)", slots)
        await db.commit()

async def get_free_dates(start_date: date) -> list[str]:
    """Возвращает список дат с свободными слотами, начиная с указанной даты."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT DISTINCT date FROM schedule WHERE date >= ? AND is_booked = 0 ORDER BY date",
            (start_date.strftime("%Y-%m-%d"),)
        )
        return [row[0] for row in await cursor.fetchall()]

async def get_free_slots_for_date(selected_date: str) -> list[str]:
    """Возвращает свободные временные слоты для выбранной даты."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT time FROM schedule WHERE date = ? AND is_booked = 0 ORDER BY time",
            (selected_date,)
        )
        return [row[0] for row in await cursor.fetchall()]

async def get_free_slots_with_ids(selected_date: str) -> list[tuple[int, str]]:
    """Возвращает свободные слоты вместе с их ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, time FROM schedule WHERE date = ? AND is_booked = 0 ORDER BY time",
            (selected_date,)
        )
        return await cursor.fetchall()

async def delete_schedule_slot(schedule_id: int):
    """Удаляет конкретный свободный слот."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Убедимся, что слот не забронирован (на всякий случай)
        await db.execute("DELETE FROM schedule WHERE id = ? AND is_booked = 0", (schedule_id,))
        await db.commit()

async def delete_all_free_slots(selected_date: str):
    """Удаляет все свободные слоты на выбранную дату."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM schedule WHERE date = ? AND is_booked = 0", (selected_date,))
        await db.commit()

async def book_slot(user_id: int, selected_date: str, selected_time: str) -> tuple[int, int] | None:
    """Бронирует слот и создает запись. Возвращает (appointment_id, schedule_id) или None."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, есть ли у пользователя уже активная запись
        cursor = await db.execute("SELECT id FROM appointments WHERE user_id = ?", (user_id,))
        if await cursor.fetchone():
            return None

        # Находим ID слота и бронируем его
        cursor = await db.execute("SELECT id FROM schedule WHERE date = ? AND time = ? AND is_booked = 0", (selected_date, selected_time))
        schedule_slot = await cursor.fetchone()
        if not schedule_slot:
            return None
        
        schedule_id = schedule_slot[0]
        
        # Используем транзакцию
        await db.execute("BEGIN")
        try:
            await db.execute("UPDATE schedule SET is_booked = 1 WHERE id = ?", (schedule_id,))
            cursor = await db.execute(
                "INSERT INTO appointments (user_id, schedule_id, created_at) VALUES (?, ?, ?)",
                (user_id, schedule_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            await db.commit()
            appointment_id = cursor.lastrowid
            return appointment_id, schedule_id
        except Exception:
            await db.rollback()
            return None

async def get_user_appointment(user_id: int) -> tuple | None:
    """Возвращает активную запись пользователя (id, date, time)."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            SELECT a.id, s.date, s.time
            FROM appointments a
            JOIN schedule s ON a.schedule_id = s.id
            WHERE a.user_id = ?
        ''', (user_id,))
        return await cursor.fetchone()

async def cancel_appointment(appointment_id: int):
    """Отменяет запись, освобождая слот."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN")
        try:
            cursor = await db.execute("SELECT schedule_id FROM appointments WHERE id = ?", (appointment_id,))
            result = await cursor.fetchone()
            if not result:
                return
            
            schedule_id = result[0]
            await db.execute("UPDATE schedule SET is_booked = 0 WHERE id = ?", (schedule_id,))
            await db.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
            await db.commit()
        except Exception:
            await db.rollback()

async def get_all_active_appointments() -> list[tuple]:
    """Возвращает все активные записи для восстановления задач планировщика."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            SELECT a.id, a.user_id, s.date, s.time
            FROM appointments a
            JOIN schedule s ON a.schedule_id = s.id
        ''')
        return await cursor.fetchall()
