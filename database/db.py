import aiosqlite
from config import DB_PATH

def get_db():
    return aiosqlite.connect(DB_PATH)