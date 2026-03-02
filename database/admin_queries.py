from database.db import get_db


async def get_all_services():
    async with get_db() as db:
        async with db.execute("SELECT id, name, price, duration_min, is_active FROM services ORDER BY name") as cur:
            rows = await cur.fetchall()
            return [{"id": r[0], "name": r[1], "price": r[2], "duration_min": r[3], "is_active": r[4]} for r in rows]


async def add_service(name: str, price: int, duration_min: int):
    async with get_db() as db:
        await db.execute("INSERT INTO services (name, price, duration_min) VALUES (?,?,?)", (name, price, duration_min))
        await db.commit()


async def toggle_service(service_id: int):
    async with get_db() as db:
        await db.execute("UPDATE services SET is_active = NOT is_active WHERE id=?", (service_id,))
        await db.commit()


async def delete_service(service_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM master_services WHERE service_id=?", (service_id,))
        await db.execute("DELETE FROM services WHERE id=?", (service_id,))
        await db.commit()


async def get_all_masters():
    async with get_db() as db:
        async with db.execute("SELECT id, name, is_active FROM masters ORDER BY name") as cur:
            rows = await cur.fetchall()
            return [{"id": r[0], "name": r[1], "is_active": r[2]} for r in rows]


async def get_master_full(master_id: int):
    async with get_db() as db:
        async with db.execute("SELECT id, name, is_active FROM masters WHERE id=?", (master_id,)) as cur:
            r = await cur.fetchone()
            return {"id": r[0], "name": r[1], "is_active": r[2]} if r else None


async def add_master(name: str):
    async with get_db() as db:
        await db.execute("INSERT INTO masters (name) VALUES (?)", (name,))
        await db.commit()


async def toggle_master(master_id: int):
    async with get_db() as db:
        await db.execute("UPDATE masters SET is_active = NOT is_active WHERE id=?", (master_id,))
        await db.commit()


async def get_master_schedule(master_id: int) -> dict:
    async with get_db() as db:
        async with db.execute(
            "SELECT weekday, start_time, end_time FROM master_schedule WHERE master_id=?", (master_id,)
        ) as cur:
            rows = await cur.fetchall()
            return {r[0]: (r[1], r[2]) for r in rows}


async def set_master_day(master_id: int, weekday: int, start: str, end: str):
    async with get_db() as db:
        await db.execute(
            "DELETE FROM master_schedule WHERE master_id=? AND weekday=?", (master_id, weekday)
        )
        await db.execute(
            "INSERT INTO master_schedule (master_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
            (master_id, weekday, start, end)
        )
        await db.commit()


async def remove_master_day(master_id: int, weekday: int):
    async with get_db() as db:
        await db.execute(
            "DELETE FROM master_schedule WHERE master_id=? AND weekday=?", (master_id, weekday)
        )
        await db.commit()


async def get_master_service_ids(master_id: int) -> list:
    async with get_db() as db:
        async with db.execute(
            "SELECT service_id FROM master_services WHERE master_id=?", (master_id,)
        ) as cur:
            return [r[0] for r in await cur.fetchall()]


async def toggle_master_service(master_id: int, service_id: int):
    async with get_db() as db:
        async with db.execute(
            "SELECT 1 FROM master_services WHERE master_id=? AND service_id=?", (master_id, service_id)
        ) as cur:
            exists = await cur.fetchone()
        if exists:
            await db.execute(
                "DELETE FROM master_services WHERE master_id=? AND service_id=?", (master_id, service_id)
            )
        else:
            await db.execute("INSERT INTO master_services VALUES (?,?)", (master_id, service_id))
        await db.commit()


async def add_master_photo(master_id: int, file_id: str):
    async with get_db() as db:
        await db.execute("INSERT INTO master_photos (master_id, file_id) VALUES (?,?)", (master_id, file_id))
        await db.commit()


async def get_master_photos(master_id: int) -> list:
    async with get_db() as db:
        async with db.execute(
            "SELECT id, file_id FROM master_photos WHERE master_id=? ORDER BY created_at", (master_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [{"id": r[0], "file_id": r[1]} for r in rows]


async def delete_master_photo(photo_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM master_photos WHERE id=?", (photo_id,))
        await db.commit()
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    return await get_appointments_for_date(today)


async def get_today_appointments():
    from datetime import date
    return await get_appointments_for_date(date.today().strftime("%Y-%m-%d"))


async def get_appointments_for_date(date_str: str):
    async with get_db() as db:
        async with db.execute("""
            SELECT a.time, u.name, u.phone, s.name, m.name, a.comment
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            JOIN services s ON a.service_id = s.id
            JOIN masters m ON a.master_id = m.id
            WHERE a.date=? AND a.status='active'
            ORDER BY a.time
        """, (date_str,)) as cur:
            rows = await cur.fetchall()
            return [
                {"time": r[0], "client": r[1], "phone": r[2],
                 "service": r[3], "master": r[4], "comment": r[5]}
                for r in rows
            ]


async def get_appointments_14_days():
    from datetime import date, timedelta
    async with get_db() as db:
        today = date.today()
        start = today.strftime("%Y-%m-%d")
        end = (today + timedelta(days=14)).strftime("%Y-%m-%d")
        async with db.execute("""
            SELECT a.date, a.time, a.client_name, a.tg_username, s.name, m.name, u.phone
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            JOIN services s ON a.service_id = s.id
            JOIN masters m ON a.master_id = m.id
            WHERE a.date BETWEEN ? AND ? AND a.status='active'
            ORDER BY a.date, a.time
        """, (start, end)) as cur:
            rows = await cur.fetchall()
            from collections import defaultdict
            result = defaultdict(list)
            for r in rows:
                result[r[0]].append({
                    "time": r[1], "client_name": r[2],
                    "tg_username": r[3], "service": r[4], "master": r[5], "phone": r[6]
                })
            return dict(result)