import aiosqlite
import os
from datetime import date, datetime

from config import settings

async def init_db(db_path: str = None):
    """Инициализирует базу данных и создает таблицы, если их нет."""
    db_path = db_path or settings.DB_PATH
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        # 1. Создание базовых таблиц
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT
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
        await db.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at TEXT NOT NULL
            )
        ''')
        
        # 2. МИГРАЦИИ (Добавление новых колонок в существующие таблицы)
        
        # Список необходимых колонок: (table_name, column_definition)
        migrations = [
            ("users", "language TEXT DEFAULT 'ru'"),
            # Kelajakda yangi ustunlar qo'shilsa, shunchaki shu yerga yozasiz:
            # ("users", "is_blocked INTEGER DEFAULT 0"),
        ]

        for table, column_def in migrations:
            column_name = column_def.split()[0]
            # Проверяем, существует ли колонка
            cursor = await db.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if column_name not in columns:
                try:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
                    print(f"[DB MIGRATION] Added column {column_name} to table {table}")
                except aiosqlite.OperationalError as e:
                    print(f"[DB MIGRATION] Error adding column {column_name}: {e}")

        await db.commit()

async def get_setting(key: str, default: str = None, db_path: str = None) -> str:
    """Получает настройку из БД."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        if row:
            return row[0]
        return default

async def set_setting(key: str, value: str, db_path: str = None):
    """Сохраняет настройку в БД."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

# --- Функции для работы с пользователями ---
async def get_or_create_user(user_id: int, name: str = None, phone: str = None, db_path: str = None):
    """Получает или создает пользователя в БД."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
            await db.execute("INSERT INTO users (id, name, phone, language) VALUES (?, ?, ?, 'ru')", (user_id, name, phone))
            await db.commit()
            return user_id, name, phone, 'ru', True
        return (*user, False)

async def update_user_info(user_id: int, name: str, phone: str, db_path: str = None):
    """Обновляет имя и телефон пользователя."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, user_id))
        await db.commit()

async def get_user_language(user_id: int, db_path: str = None) -> str:
    """Возвращает язык пользователя."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT language FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 'ru'

async def set_user_language(user_id: int, language: str, db_path: str = None):
    """Устанавливает язык пользователя."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
        await db.commit()

# --- Функции для работы с администраторами ---
async def add_admin(user_id: int, added_by: int, db_path: str = None):
    """Добавляет нового администратора."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (id, added_by, added_at) VALUES (?, ?, ?)",
            (user_id, added_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        await db.commit()

async def remove_admin(user_id: int, db_path: str = None):
    """Удаляет администратора."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM admins WHERE id = ?", (user_id,))
        await db.commit()

async def get_admins(db_path: str = None) -> list[int]:
    """Возвращает список ID всех администраторов."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT id FROM admins")
        return [row[0] for row in await cursor.fetchall()]

async def is_admin(user_id: int, db_path: str = None) -> bool:
    """Проверяет, является ли пользователь администратором."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT id FROM admins WHERE id = ?", (user_id,))
        return await cursor.fetchone() is not None

# --- Функции для работы с расписанием ---
async def add_schedule_slots(slots: list[tuple[str, str]], db_path: str = None):
    """Добавляет временные слоты в расписание. Игнорирует дубликаты."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.executemany("INSERT OR IGNORE INTO schedule (date, time) VALUES (?, ?)", slots)
        await db.commit()

async def get_free_dates(start_date: date, db_path: str = None) -> list[str]:
    """Возвращает список дат с свободными слотами, начиная с указанной даты."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT DISTINCT date FROM schedule WHERE date >= ? AND is_booked = 0 ORDER BY date",
            (start_date.strftime("%Y-%m-%d"),)
        )
        return [row[0] for row in await cursor.fetchall()]

async def get_free_slots_for_date(selected_date: str, db_path: str = None) -> list[str]:
    """Возвращает свободные временные слоты для выбранной даты."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT time FROM schedule WHERE date = ? AND is_booked = 0 ORDER BY time",
            (selected_date,)
        )
        return [row[0] for row in await cursor.fetchall()]

async def get_free_slots_with_ids(selected_date: str, db_path: str = None) -> list[tuple[int, str]]:
    """Возвращает свободные слоты вместе с их ID."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT id, time FROM schedule WHERE date = ? AND is_booked = 0 ORDER BY time",
            (selected_date,)
        )
        return await cursor.fetchall()

async def delete_schedule_slot(schedule_id: int, db_path: str = None):
    """Удаляет конкретный свободный слот."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        # Убедимся, что слот не забронирован (на всякий случай)
        await db.execute("DELETE FROM schedule WHERE id = ? AND is_booked = 0", (schedule_id,))
        await db.commit()

async def delete_all_free_slots(selected_date: str, db_path: str = None):
    """Удаляет все свободные слоты на выбранную дату."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM schedule WHERE date = ? AND is_booked = 0", (selected_date,))
        await db.commit()

async def book_slot(user_id: int, selected_date: str, selected_time: str, db_path: str = None) -> tuple[int, int] | None:
    """Бронирует слот и создает запись. Возвращает (appointment_id, schedule_id) или None."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
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

async def get_user_appointment(user_id: int, db_path: str = None) -> tuple | None:
    """Возвращает активную запись пользователя (id, date, time)."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute('''
            SELECT a.id, s.date, s.time
            FROM appointments a
            JOIN schedule s ON a.schedule_id = s.id
            WHERE a.user_id = ?
        ''', (user_id,))
        return await cursor.fetchone()

async def cancel_appointment(appointment_id: int, db_path: str = None):
    """Отменяет запись, освобождая слот."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
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

async def get_all_active_appointments(db_path: str = None) -> list[tuple]:
    """Возвращает все активные записи для восстановления задач планировщика."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute('''
            SELECT a.id, a.user_id, s.date, s.time
            FROM appointments a
            JOIN schedule s ON a.schedule_id = s.id
        ''')
        return await cursor.fetchall()

async def get_appointment_details(appointment_id: int, db_path: str = None) -> tuple | None:
    """Возвращает подробную информацию о записи (id, user_id, date, time)."""
    db_path = db_path or settings.DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute('''
            SELECT a.id, a.user_id, s.date, s.time
            FROM appointments a
            JOIN schedule s ON a.schedule_id = s.id
            WHERE a.id = ?
        ''', (appointment_id,))
        return await cursor.fetchone()
