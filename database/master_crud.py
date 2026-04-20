import aiosqlite
import os
from config import settings

async def init_master_db():
    # Ensure directory exists
    os.makedirs(os.path.dirname(settings.MASTER_DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(settings.MASTER_DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                owner_id INTEGER NOT NULL,
                status TEXT DEFAULT 'active'
            )
        ''')
        await db.commit()

async def get_active_bots():
    async with aiosqlite.connect(settings.MASTER_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM bots WHERE status = 'active'")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def add_bot(token: str, owner_id: int):
    async with aiosqlite.connect(settings.MASTER_DB_PATH) as db:
        await db.execute(
            "INSERT INTO bots (token, owner_id) VALUES (?, ?)",
            (token, owner_id)
        )
        await db.commit()
