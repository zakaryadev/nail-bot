from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID"))
    CHANNEL_ID: int = int(os.getenv("CHANNEL_ID"))
    CHANNEL_LINK: str = os.getenv("CHANNEL_LINK")
    ADMIN_CHANNEL_ID: int = int(os.getenv("ADMIN_CHANNEL_ID"))


settings = Settings()
