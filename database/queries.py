from database.db import get_db
from datetime import datetime


async def get_or_create_user(tg_id: int, name: str):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, name) VALUES (?, ?)", (tg_id, name)
        )
        await db.commit()
        async with db.execute("SELECT id FROM users WHERE tg_id=?", (tg_id,)) as cur:
            row = await cur.fetchone()
            return row[0]


async def get_services():
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, price, duration_min FROM services WHERE is_active=1 ORDER BY name"
        ) as cur:
            rows = await cur.fetchall()
            return [{"id": r[0], "name": r[1], "price": r[2], "duration_min": r[3]} for r in rows]


async def get_service(service_id: int):
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, price, duration_min FROM services WHERE id=?", (service_id,)
        ) as cur:
            r = await cur.fetchone()
            return {"id": r[0], "name": r[1], "price": r[2], "duration_min": r[3]} if r else None


async def get_masters_for_services(service_ids: list):
    """Мастера, которые умеют делать ВСЕ выбранные услуги."""
    if not service_ids:
        return []
    async with get_db() as db:
        placeholders = ",".join("?" * len(service_ids))
        async with db.execute(f"""
            SELECT m.id, m.name FROM masters m
            JOIN master_services ms ON m.id = ms.master_id
            WHERE ms.service_id IN ({placeholders}) AND m.is_active=1
            GROUP BY m.id
            HAVING COUNT(DISTINCT ms.service_id) = ?
        """, (*service_ids, len(service_ids))) as cur:
            rows = await cur.fetchall()
            return [{"id": r[0], "name": r[1]} for r in rows]


async def get_master(master_id: int):
    async with get_db() as db:
        async with db.execute("SELECT id, name FROM masters WHERE id=?", (master_id,)) as cur:
            r = await cur.fetchone()
            return {"id": r[0], "name": r[1]} if r else None


async def get_available_slots(master_id: int, date: str):
    """Возвращает список свободных слотов времени для мастера на дату."""
    from datetime import datetime
    async with get_db() as db:
        # Получаем расписание мастера на этот день недели
        weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
        async with db.execute(
            "SELECT start_time, end_time FROM master_schedule WHERE master_id=? AND weekday=?",
            (master_id, weekday)
        ) as cur:
            schedule = await cur.fetchone()

        if not schedule:
            return []

        start_h, start_m = map(int, schedule[0].split(":"))
        end_h, end_m = map(int, schedule[1].split(":"))

        # Все занятые слоты на эту дату
        async with db.execute(
            "SELECT time FROM appointments WHERE master_id=? AND date=? AND status='active'",
            (master_id, date)
        ) as cur:
            booked = {r[0] for r in await cur.fetchall()}

        # Генерируем слоты по 30 минут
        slots = []
        current = start_h * 60 + start_m
        end = end_h * 60 + end_m
        now = datetime.now()
        is_today = date == now.strftime("%Y-%m-%d")
        now_minutes = now.hour * 60 + now.minute

        while current < end:
            slot = f"{current // 60:02d}:{current % 60:02d}"
            if slot not in booked:
                # Для сегодня — пропускаем прошедшее время
                if not is_today or current > now_minutes:
                    slots.append(slot)
            current += 30

        return slots


async def create_appointment(user_id, master_id, service_id, date, time, comment, phone,
                             client_name='', tg_username='', photo_file_ids=''):
    async with get_db() as db:
        await db.execute("""
            INSERT INTO appointments
            (user_id, master_id, service_id, date, time, comment, client_name, tg_username, photo_file_ids, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (user_id, master_id, service_id, date, time, comment, client_name, tg_username, photo_file_ids))
        await db.execute("UPDATE users SET phone=? WHERE id=?", (phone, user_id))
        await db.commit()


async def get_user_appointments(user_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT a.id, a.date, a.time, s.name as service_name, m.name as master_name, a.comment
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN masters m ON a.master_id = m.id
            WHERE a.user_id=? AND a.status='active'
            ORDER BY a.date, a.time
        """, (user_id,)) as cur:
            rows = await cur.fetchall()
            return [
                {"id": r[0], "date": r[1], "time": r[2], "service_name": r[3],
                 "master_name": r[4], "comment": r[5]}
                for r in rows
            ]


async def get_appointment(appt_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT a.id, a.date, a.time, s.name, m.name, a.comment, a.user_id
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN masters m ON a.master_id = m.id
            WHERE a.id=?
        """, (appt_id,)) as cur:
            r = await cur.fetchone()
            return {"id": r[0], "date": r[1], "time": r[2], "service_name": r[3],
                    "master_name": r[4], "comment": r[5], "user_id": r[6]} if r else None


async def get_masters_with_services():
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name FROM masters WHERE is_active=1 ORDER BY name"
        ) as cur:
            masters = [{"id": r[0], "name": r[1]} for r in await cur.fetchall()]

        for m in masters:
            async with db.execute("""
                SELECT s.name, s.price FROM services s
                JOIN master_services ms ON s.id = ms.service_id
                WHERE ms.master_id=? AND s.is_active=1
            """, (m['id'],)) as cur:
                m['services'] = [{"name": r[0], "price": r[1]} for r in await cur.fetchall()]

            async with db.execute(
                "SELECT file_id FROM master_photos WHERE master_id=? ORDER BY created_at", (m['id'],)
            ) as cur:
                m['photos'] = [r[0] for r in await cur.fetchall()]

        return masters


async def cancel_appointment(appt_id: int):
    async with get_db() as db:
        await db.execute(
            "UPDATE appointments SET status='cancelled' WHERE id=?", (appt_id,)
        )
        await db.commit()