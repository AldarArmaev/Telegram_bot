from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database.db import get_db


async def send_reminders(bot: Bot):
    async with get_db() as db:
        async with db.execute("""
            SELECT a.id, a.date, a.time, u.tg_id,
                   s.name as service, m.name as master,
                   a.reminder_24h, a.reminder_2h
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            JOIN services s ON a.service_id = s.id
            JOIN masters m ON a.master_id = m.id
            WHERE a.status = 'active'
        """) as cur:
            rows = await cur.fetchall()

    from datetime import datetime
    now = datetime.now()

    for row in rows:
        appt_id, date, time, tg_id, service, master, r24, r2 = row
        try:
            appt_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            continue

        diff_hours = (appt_dt - now).total_seconds() / 3600

        if not r24 and 23 <= diff_hours <= 25:
            try:
                await bot.send_message(
                    tg_id,
                    f"🔔 Напоминание!\n\nЗавтра в <b>{time}</b> у вас запись:\n"
                    f"💇 {service}\n👤 Мастер: {master}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            async with get_db() as db:
                await db.execute("UPDATE appointments SET reminder_24h=1 WHERE id=?", (appt_id,))
                await db.commit()

        elif not r2 and 1 <= diff_hours <= 3:
            try:
                await bot.send_message(
                    tg_id,
                    f"🔔 Напоминание!\n\nЧерез ~2 часа в <b>{time}</b> у вас запись:\n"
                    f"💇 {service}\n👤 Мастер: {master}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            async with get_db() as db:
                await db.execute("UPDATE appointments SET reminder_2h=1 WHERE id=?", (appt_id,))
                await db.commit()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_reminders, "interval", minutes=15, args=[bot])
    return scheduler
