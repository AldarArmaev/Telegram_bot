from dotenv import load_dotenv
import os

load_dotenv()


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("ОШИБКА: Токен бота не найден ни в .env, ни в системных переменных!")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID"))
DB_PATH = "beauty_bot.db"
