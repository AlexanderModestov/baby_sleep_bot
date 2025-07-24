import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import BOT_TOKEN
from handlers import start_handler, settings_handler
from services.notification_service import NotificationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Initialize notification service
    notification_service = NotificationService(bot)
    
    # Include routers
    dp.include_router(start_handler.router)
    dp.include_router(settings_handler.router)
    
    logger.info("Starting Baby Sleep Tracker Bot...")
    
    # Start notification scheduler
    notification_service.start_scheduler()
    
    # Start polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        notification_service.stop_scheduler()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")