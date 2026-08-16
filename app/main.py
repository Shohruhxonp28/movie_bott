import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
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

async def handle_ping(request):
    """Simple ping handler for Render health checks."""
    return web.Response(text="Bot is active and running!")

async def main():
    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully.")

    # Initialize Bot and Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(protect_content=True)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(admin_router)
    dp.include_router(callback_router)
    dp.include_router(user_router)

    # Start dummy web server on $PORT to satisfy Render's Web Service requirements
    port = int(os.getenv("PORT", "8080"))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check web server started on port {port}")

    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
