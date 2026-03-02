import asyncio
from database.db import get_db
from database.models import create_tables


async def seed():
    # Сначала создаем таблицы, если их еще нет
    await create_tables()

    async with get_db() as db:
        # 1. Заполняем услуги (Услуга 1, 2, 3)
        services_data = [
            ("Услуга 1", 1000, 60),
            ("Услуга 2", 1500, 90),
            ("Услуга 3", 2000, 120),
        ]

        for name, price, duration in services_data:
            await db.execute(
                "INSERT OR IGNORE INTO services (name, price, duration_min) VALUES (?,?,?)",
                (name, price, duration)
            )

        # 2. Заполняем мастеров (Мастер 1, Мастер 2)
        masters_names = ["Мастер 1", "Мастер 2"]
        for name in masters_names:
            await db.execute("INSERT OR IGNORE INTO masters (name) VALUES (?)", (name,))

        await db.commit()

        # --- ТЕОРЕТИЧЕСКАЯ СПРАВКА: СЛОВАРИ (MAPPING) ---
        # Чтобы связать мастера с услугой, нам нужны их ID из базы данных.
        # Алгоритм ниже выкачивает все ID и создает "карту" (dictionary),
        # где ключ — это имя, а значение — это ID.

        # Получаем ID услуг: {'Услуга 1': 1, 'Услуга 2': 2, ...}
        async with db.execute("SELECT id, name FROM services") as cur:
            svc_map = {row[1]: row[0] for row in await cur.fetchall()}

        # Получаем ID мастеров: {'Мастер 1': 1, 'Мастер 2': 2}
        async with db.execute("SELECT id, name FROM masters") as cur:
            mst_map = {row[1]: row[0] for row in await cur.fetchall()}

        # 3. Привязка услуг к мастерам по вашему условию
        # Мастер 1: Услуга 1, Услуга 2
        # Мастер 2: Услуга 1, Услуга 2, Услуга 3
        relations = {
            "Мастер 1": ["Услуга 1", "Услуга 2"],
            "Мастер 2": ["Услуга 1", "Услуга 2", "Услуга 3"],
        }

        for m_name, s_list in relations.items():
            mid = mst_map[m_name]
            for s_name in s_list:
                sid = svc_map[s_name]
                await db.execute(
                    "INSERT OR IGNORE INTO master_services (master_id, service_id) VALUES (?,?)",
                    (mid, sid)
                )

        # 4. Расписание (сделаем стандартное: пн-пт с 10:00 до 20:00)
        for m_id in mst_map.values():
            for day in range(5):  # 0=Пн, 4=Пт
                await db.execute(
                    "INSERT OR IGNORE INTO master_schedule (master_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
                    (m_id, day, "10:00", "20:00")
                )

        await db.commit()
        print("✅ База данных успешно наполнена вашими данными!")
        print(f"   Добавлено мастеров: {len(mst_map)}")
        print(f"   Добавлено услуг: {len(svc_map)}")


if __name__ == "__main__":
    asyncio.run(seed())