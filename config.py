from dataclasses import dataclass
from dotenv import load_dotenv
import os
import sys

load_dotenv()


def _require(key: str) -> str:
    """Get required env variable or exit with a clear error message."""
    value = os.getenv(key)
    if not value:
        print(f"[FATAL] Missing required environment variable: {key}", file=sys.stderr)
        print(f"[FATAL] Copy .env.example to .env and fill in all values.", file=sys.stderr)
        sys.exit(1)
    return value


def _require_int(key: str) -> int:
    """Get required env variable as int or exit with a clear error message."""
    raw = _require(key)
    try:
        return int(raw)
    except ValueError:
        print(f"[FATAL] Environment variable {key}={raw!r} must be an integer.", file=sys.stderr)
        sys.exit(1)


@dataclass
class Settings:
    BOT_TOKEN: str
    ADMIN_ID: int
    CHANNEL_ID: int
    CHANNEL_LINK: str
    ADMIN_CHANNEL_ID: int

    # SQLite DB path — use /data volume in Docker, local file otherwise
    DB_PATH: str = os.getenv("DB_PATH", "data/nail_bot.db")
    MASTER_DB_PATH: str = os.getenv("MASTER_DB_PATH", "data/master.db")
    BOTS_DATA_DIR: str = os.getenv("BOTS_DATA_DIR", "data/bots")


def _load_settings() -> Settings:
    return Settings(
        BOT_TOKEN=_require("BOT_TOKEN"),
        ADMIN_ID=_require_int("ADMIN_ID"),
        CHANNEL_ID=_require_int("CHANNEL_ID"),
        CHANNEL_LINK=_require("CHANNEL_LINK"),
        ADMIN_CHANNEL_ID=_require_int("ADMIN_CHANNEL_ID"),
    )


settings = _load_settings()
