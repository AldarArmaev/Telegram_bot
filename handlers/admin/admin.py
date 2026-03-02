from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_TG_ID
from database.db import get_db
from keyboards.admin_kb import (
    admin_menu_kb, services_list_kb, service_detail_kb,
    masters_list_kb, master_detail_kb, weekdays_kb,
    master_services_kb, cancel_kb
)
from database.admin_queries import (
    get_all_services, add_service, toggle_service, delete_service,
    get_all_masters, get_master_full, add_master, toggle_master,
    get_master_schedule, set_master_day, remove_master_day,
    get_master_service_ids, toggle_master_service,
    get_today_appointments, get_appointments_14_days,
    add_master_photo, get_master_photos, delete_master_photo
)
from database.queries import get_services

router = Router()


def admin_only(func):
    from functools import wraps
    @wraps(func)
    async def wrapper(event, *args, **kwargs):
        uid = event.from_user.id if hasattr(event, 'from_user') else None
        if uid != ADMIN_TG_ID:
            return
        return await func(event, *args, **kwargs)
    return wrapper


class AdminState(StatesGroup):
    add_service_name = State()
    add_service_price = State()
    add_service_duration = State()
    edit_service_price = State()
    edit_service_duration = State()
    add_master_name = State()
    set_day_time = State()
    add_photo = State()


# --- Меню ---
@router.message(Command("admin"))
@admin_only
async def admin_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔧 Панель администратора", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin_menu")
@admin_only
async def admin_menu_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔧 Панель администратора", reply_markup=admin_menu_kb())


# --- Записи на сегодня ---
@router.callback_query(F.data == "admin_today")
@admin_only
async def admin_today(callback: CallbackQuery):
    appointments = await get_today_appointments()
    if not appointments:
        text = "📅 Сегодня записей нет."
    else:
        lines = ["📅 <b>Записи на сегодня:</b>\n"]
        for a in appointments:
            lines.append(
                f"🕐 {a['time']} — {a['client']} ({a['phone']})\n"
                f"   💇 {a['service']} у {a['master']}\n"
                f"   💬 {a['comment'] or '—'}"
            )
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin_14days")
@admin_only
async def admin_14days(callback: CallbackQuery):
    data = await get_appointments_14_days()
    if not data:
        text = "🗓 На ближайшие 14 дней записей нет."
    else:
        from datetime import datetime
        weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
        lines = ["🗓 <b>Записи на 14 дней:</b>\n"]
        for date_str, appts in sorted(data.items()):
            d = datetime.strptime(date_str, "%Y-%m-%d")
            lines.append(f"\n<b>{d.strftime('%d.%m')} ({weekdays[d.weekday()]}):</b>")
            for a in appts:
                    name = a['client_name'] or '—'
                    username = a['tg_username'] or ''
                    phone = a['phone'] or '—'
                    if username.startswith('@'):
                        client_str = f"<a href='https://t.me/{username[1:]}'>{name}</a>"
                    elif username.startswith('tg://'):
                        client_str = f"<a href='{username}'>{name}</a>"
                    else:
                        client_str = name
                    lines.append(f"  🕐 {a['time']} — {client_str}, {phone}\n        💇 {a['service']} ({a['master']})")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")


# --- Услуги ---
@router.callback_query(F.data == "admin_services")
@admin_only
async def admin_services(callback: CallbackQuery):
    services = await get_all_services()
    await callback.message.edit_text("💇 Управление услугами:", reply_markup=services_list_kb(services))


@router.callback_query(F.data.regexp(r"^admin_service_\d+$"))
@admin_only
async def admin_service_detail(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[2])
    services = await get_all_services()
    s = next((x for x in services if x['id'] == service_id), None)
    if not s:
        await callback.answer("Не найдено")
        return
    text = f"💇 <b>{s['name']}</b>\nЦена: {s['price']}₽\nДлительность: {s['duration_min']} мин\nСтатус: {'активна' if s['is_active'] else 'неактивна'}"
    await callback.message.edit_text(text, reply_markup=service_detail_kb(service_id, s['is_active']), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_toggle_service_"))
@admin_only
async def admin_toggle_service(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[3])
    await toggle_service(service_id)
    services = await get_all_services()
    s = next((x for x in services if x['id'] == service_id), None)
    if not s:
        await callback.answer("Не найдено")
        return
    text = f"💇 <b>{s['name']}</b>\nЦена: {s['price']}₽\nДлительность: {s['duration_min']} мин\nСтатус: {'активна' if s['is_active'] else 'неактивна'}"
    await callback.message.edit_text(text, reply_markup=service_detail_kb(service_id, s['is_active']), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_edit_price_"))
@admin_only
async def admin_edit_price_start(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[3])
    await state.set_state(AdminState.edit_service_price)
    await state.update_data(service_id=service_id, prompt_msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите новую цену (₽):", reply_markup=cancel_kb(f"admin_service_{service_id}"))


@router.message(AdminState.edit_service_price)
async def admin_edit_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.delete()
        await message.answer("⚠️ Введите число:")
        return
    data = await state.get_data()
    async with get_db() as db:
        await db.execute("UPDATE services SET price=? WHERE id=?", (int(message.text), data['service_id']))
        await db.commit()
    await message.delete()
    # Удаляем сообщение бота с просьбой ввести цену
    try:
        await message.bot.delete_message(message.chat.id, data['prompt_msg_id'])
    except Exception:
        pass
    await state.clear()
    services = await get_all_services()
    s = next((x for x in services if x['id'] == data['service_id']), None)
    text = f"💇 <b>{s['name']}</b>\nЦена: {s['price']}₽\nДлительность: {s['duration_min']} мин\nСтатус: {'активна' if s['is_active'] else 'неактивна'}"
    await message.answer(text, reply_markup=service_detail_kb(s['id'], s['is_active']), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_edit_dur_"))
@admin_only
async def admin_edit_duration_start(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[3])
    await state.set_state(AdminState.edit_service_duration)
    await state.update_data(service_id=service_id, prompt_msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите новую длительность (мин):", reply_markup=cancel_kb(f"admin_service_{service_id}"))


@router.message(AdminState.edit_service_duration)
async def admin_edit_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.delete()
        await message.answer("⚠️ Введите число:")
        return
    data = await state.get_data()
    async with get_db() as db:
        await db.execute("UPDATE services SET duration_min=? WHERE id=?", (int(message.text), data['service_id']))
        await db.commit()
    await message.delete()
    try:
        await message.bot.delete_message(message.chat.id, data['prompt_msg_id'])
    except Exception:
        pass
    await state.clear()
    services = await get_all_services()
    s = next((x for x in services if x['id'] == data['service_id']), None)
    text = f"💇 <b>{s['name']}</b>\nЦена: {s['price']}₽\nДлительность: {s['duration_min']} мин\nСтатус: {'активна' if s['is_active'] else 'неактивна'}"
    await message.answer(text, reply_markup=service_detail_kb(s['id'], s['is_active']), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_delete_service_"))
@admin_only
async def admin_delete_service(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[3])
    await delete_service(service_id)
    services = await get_all_services()
    await callback.message.edit_text("✅ Услуга удалена.", reply_markup=services_list_kb(services))


@router.callback_query(F.data == "admin_add_service")
@admin_only
async def admin_add_service_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.add_service_name)
    await state.update_data(prompt_msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите название услуги:", reply_markup=cancel_kb("admin_services"))


@router.message(AdminState.add_service_name)
async def admin_add_service_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminState.add_service_price)
    await message.delete()
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data['prompt_msg_id'])
    except Exception:
        pass
    msg = await message.answer("Введите цену (₽):")
    await state.update_data(prompt_msg_id=msg.message_id)


@router.message(AdminState.add_service_price)
async def admin_add_service_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.delete()
        await message.answer("⚠️ Введите число:")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AdminState.add_service_duration)
    await message.delete()
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data['prompt_msg_id'])
    except Exception:
        pass
    msg = await message.answer("Введите длительность в минутах:")
    await state.update_data(prompt_msg_id=msg.message_id)


@router.message(AdminState.add_service_duration)
async def admin_add_service_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.delete()
        await message.answer("⚠️ Введите число:")
        return
    data = await state.get_data()
    await add_service(data['name'], data['price'], int(message.text))
    await message.delete()
    try:
        await message.bot.delete_message(message.chat.id, data['prompt_msg_id'])
    except Exception:
        pass
    await state.clear()
    services = await get_all_services()
    await message.answer(f"✅ Услуга «{data['name']}» добавлена!", reply_markup=services_list_kb(services))


# --- Мастера ---
@router.callback_query(F.data == "admin_masters")
@admin_only
async def admin_masters(callback: CallbackQuery):
    masters = await get_all_masters()
    await callback.message.edit_text("👤 Управление мастерами:", reply_markup=masters_list_kb(masters))


@router.callback_query(F.data.regexp(r"^admin_master_\d+$"))
@admin_only
async def admin_master_detail(callback: CallbackQuery):
    master_id = int(callback.data.split("_")[2])
    m = await get_master_full(master_id)
    if not m:
        await callback.answer("Не найдено")
        return
    text = f"👤 <b>{m['name']}</b>\nСтатус: {'активен' if m['is_active'] else 'неактивен'}"
    await callback.message.edit_text(text, reply_markup=master_detail_kb(master_id, m['is_active']), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_toggle_master_"))
@admin_only
async def admin_toggle_master(callback: CallbackQuery):
    master_id = int(callback.data.split("_")[3])
    await toggle_master(master_id)
    m = await get_master_full(master_id)
    if not m:
        await callback.answer("Не найдено")
        return
    text = f"👤 <b>{m['name']}</b>\nСтатус: {'активен' if m['is_active'] else 'неактивен'}"
    await callback.message.edit_text(text, reply_markup=master_detail_kb(master_id, m['is_active']), parse_mode="HTML")


@router.callback_query(F.data == "admin_add_master")
@admin_only
async def admin_add_master_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.add_master_name)
    await callback.message.edit_text("Введите имя мастера:", reply_markup=cancel_kb("admin_masters"))


@router.message(AdminState.add_master_name)
async def admin_add_master_name(message: Message, state: FSMContext):
    await add_master(message.text)
    await state.clear()
    masters = await get_all_masters()
    await message.answer(f"✅ Мастер «{message.text}» добавлен!", reply_markup=masters_list_kb(masters))


# --- Расписание ---
@router.callback_query(F.data.startswith("admin_schedule_"))
@admin_only
async def admin_schedule(callback: CallbackQuery):
    master_id = int(callback.data.split("_")[2])
    schedule = await get_master_schedule(master_id)
    await callback.message.edit_text(
        "🗓 Расписание мастера (нажмите день для изменения):",
        reply_markup=weekdays_kb(master_id, schedule)
    )


@router.callback_query(F.data.startswith("admin_day_"))
@admin_only
async def admin_day_toggle(callback: CallbackQuery, state: FSMContext):
    _, _, master_id, weekday = callback.data.split("_")
    master_id, weekday = int(master_id), int(weekday)
    schedule = await get_master_schedule(master_id)

    if weekday in schedule:
        await remove_master_day(master_id, weekday)
        schedule = await get_master_schedule(master_id)
        await callback.message.edit_reply_markup(reply_markup=weekdays_kb(master_id, schedule))
        await callback.answer("День удалён")
    else:
        await state.set_state(AdminState.set_day_time)
        await state.update_data(master_id=master_id, weekday=weekday)
        days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
        await callback.message.edit_text(
            f"Введите время работы в {days[weekday]} в формате <b>09:00-18:00</b>:",
            reply_markup=cancel_kb(f"admin_schedule_{master_id}"),
            parse_mode="HTML"
        )


@router.message(AdminState.set_day_time)
async def admin_set_day_time(message: Message, state: FSMContext):
    import re
    if not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", message.text):
        await message.answer("Формат: 09:00-18:00")
        return
    start, end = message.text.split("-")
    data = await state.get_data()
    await set_master_day(data['master_id'], data['weekday'], start, end)
    await state.clear()
    schedule = await get_master_schedule(data['master_id'])
    await message.answer("✅ Расписание обновлено!", reply_markup=weekdays_kb(data['master_id'], schedule))


# --- Фото мастера ---
@router.callback_query(F.data.startswith("admin_photos_"))
@admin_only
async def admin_photos(callback: CallbackQuery):
    master_id = int(callback.data.split("_")[2])
    photos = await get_master_photos(master_id)
    m = await get_master_full(master_id)
    text = f"🖼 Фото работ — <b>{m['name']}</b>\nВсего фото: {len(photos)}"
    from keyboards.admin_kb import photos_manage_kb
    await callback.message.edit_text(text, reply_markup=photos_manage_kb(master_id, photos), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_add_photo_"))
@admin_only
async def admin_add_photo_start(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[3])
    await state.set_state(AdminState.add_photo)
    await state.update_data(master_id=master_id)
    await callback.message.edit_text(
        "📷 Отправьте фото работы:",
        reply_markup=cancel_kb(f"admin_photos_{master_id}")
    )


@router.message(AdminState.add_photo, F.photo)
async def admin_receive_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    master_id = data['master_id']
    file_id = message.photo[-1].file_id
    await add_master_photo(master_id, file_id)
    await state.clear()
    photos = await get_master_photos(master_id)
    m = await get_master_full(master_id)
    from keyboards.admin_kb import photos_manage_kb
    await message.answer(
        f"✅ Фото добавлено!\n🖼 Фото работ — <b>{m['name']}</b>\nВсего фото: {len(photos)}",
        reply_markup=photos_manage_kb(master_id, photos),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_del_photo_"))
@admin_only
async def admin_delete_photo(callback: CallbackQuery):
    parts = callback.data.split("_")
    photo_id, master_id = int(parts[3]), int(parts[4])
    await delete_master_photo(photo_id)
    photos = await get_master_photos(master_id)
    m = await get_master_full(master_id)
    from keyboards.admin_kb import photos_manage_kb
    await callback.message.edit_text(
        f"🖼 Фото работ — <b>{m['name']}</b>\nВсего фото: {len(photos)}",
        reply_markup=photos_manage_kb(master_id, photos),
        parse_mode="HTML"
    )


# --- Услуги мастера ---
@router.callback_query(F.data.startswith("admin_master_services_"))
@admin_only
async def admin_master_services(callback: CallbackQuery):
    master_id = int(callback.data.split("_")[3])
    all_services = await get_all_services()
    linked_ids = await get_master_service_ids(master_id)
    await callback.message.edit_text(
        "💇 Услуги мастера (нажмите для переключения):",
        reply_markup=master_services_kb(master_id, all_services, linked_ids)
    )


@router.callback_query(F.data.startswith("admin_toggle_ms_"))
@admin_only
async def admin_toggle_ms(callback: CallbackQuery):
    parts = callback.data.split("_")
    master_id, service_id = int(parts[3]), int(parts[4])
    await toggle_master_service(master_id, service_id)
    all_services = await get_all_services()
    linked_ids = await get_master_service_ids(master_id)
    await callback.message.edit_reply_markup(
        reply_markup=master_services_kb(master_id, all_services, linked_ids)
    )
    await callback.answer()