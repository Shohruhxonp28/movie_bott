import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import BOT_TOKEN
from app.database import init_db
from app.handlers.admin import admin_router
from app.handlers.callback import callback_router
from app.handlers.user import user_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully.")

    # Initialize Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    # Admin first, then callback, then user router
    dp.include_router(admin_router)
    dp.include_router(callback_router)
    dp.include_router(user_router)

    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
