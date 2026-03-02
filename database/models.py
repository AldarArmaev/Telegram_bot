from database.db import get_db

async def create_tables():
    async with get_db() as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE NOT NULL,
            name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            duration_min INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS master_services (
            master_id INTEGER REFERENCES masters(id),
            service_id INTEGER REFERENCES services(id),
            PRIMARY KEY (master_id, service_id)
        );

        CREATE TABLE IF NOT EXISTS master_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER REFERENCES masters(id),
            weekday INTEGER NOT NULL,  -- 0=Mon, 6=Sun
            start_time TEXT NOT NULL,  -- "09:00"
            end_time TEXT NOT NULL     -- "18:00"
        );

        CREATE TABLE IF NOT EXISTS master_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER REFERENCES masters(id),
            file_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            master_id INTEGER REFERENCES masters(id),
            service_id INTEGER REFERENCES services(id),
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            comment TEXT,
            client_name TEXT,
            photo_file_ids TEXT,
            tg_username TEXT,
            status TEXT DEFAULT 'active',
            reminder_24h INTEGER DEFAULT 0,
            reminder_2h INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.commit()
        print("✅ Таблицы созданы")