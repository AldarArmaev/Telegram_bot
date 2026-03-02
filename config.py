from dotenv import load_dotenv
import os

load_dotenv()


BOT_TOKEN  = os.getenv("API_TOKEN")

if not BOT_TOKEN :
    raise ValueError("ОШИБКА: Токен бота не найден ни в .env, ни в системных переменных!")
ADMIN_TG_ID = os.getenv("ADMIN_TG_ID")
if not ADMIN_TG_ID:
    raise ValueError("ОШИБКА: Id администратора не найден ни в .env, ни в системных переменных!")
DB_PATH = "beauty_bot.db"
