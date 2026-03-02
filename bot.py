import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.models import create_tables
from handlers.client.start import router as start_router
from handlers.client.booking import router as booking_router
from handlers.client.my_appointments import router as appointments_router
from handlers.client.masters import router as masters_router
from handlers.admin.admin import router as admin_router
from schedulers.reminders import setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(appointments_router)
    dp.include_router(masters_router)

    await create_tables()

    scheduler = setup_scheduler(bot)
    scheduler.start()

    logger.info("🤖 Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())