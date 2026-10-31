import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (from root .env or app/.env)
load_dotenv()
load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/kinobot")

# Force SQLAlchemy async driver for PostgreSQL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Parse list of admins from comma-separated string
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]

# Storage channel ID (where files are uploaded and from which copyMessage is used)
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")
