from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from keyboards.client_kb import (
    services_kb, masters_kb, dates_kb, times_kb,
    skip_comment_kb, comment_photos_kb, confirm_kb,
    share_phone_kb, remove_kb
)
from database.queries import (
    get_services, get_masters_for_services,
    get_master, get_available_slots, create_appointment, get_or_create_user
)
from config import ADMIN_TG_ID

router = Router()


class BookingState(StatesGroup):
    service = State()
    master = State()
    date = State()
    time = State()
    comment = State()
    phone = State()
    name = State()
    confirm = State()


def get_dates():
    """Сегодня + 14 дней."""
    dates = []
    today = datetime.now().date()
    weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    for i in range(0, 15):
        d = today + timedelta(days=i)
        label = d.strftime('%d.%m')
        if i == 0:
            label += " (сегодня)"
        elif i == 1:
            label += " (завтра)"
        else:
            label += f" ({weekdays[d.weekday()]})"
        dates.append({"value": d.strftime("%Y-%m-%d"), "label": label})
    return dates


async def delete_draft(bot, chat_id: int, state: FSMContext, key: str):
    data = await state.get_data()
    msg_id = data.get(key)
    if msg_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
        await state.update_data(**{key: None})


async def delete_all_drafts(bot, chat_id: int, state: FSMContext):
    for key in ('draft_service', 'draft_master', 'draft_date', 'draft_time'):
        await delete_draft(bot, chat_id, state, key)


# --- Шаг 1: Выбор услуг (мульти) ---
@router.callback_query(F.data == "book")
async def step_service(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    services = await get_services()
    if not services:
        await callback.answer("Услуги не найдены. Обратитесь к администратору.", show_alert=True)
        return
    await state.set_state(BookingState.service)
    await state.update_data(selected_service_ids=[])
    await callback.message.edit_text(
        "Выберите услуги (можно несколько), затем нажмите «Далее»:",
        reply_markup=services_kb(services, [])
    )


@router.callback_query(BookingState.service, F.data.startswith("service_"))
async def toggle_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    selected = data.get('selected_service_ids', [])

    if service_id in selected:
        selected.remove(service_id)
    else:
        selected.append(service_id)

    await state.update_data(selected_service_ids=selected)
    services = await get_services()
    await callback.message.edit_reply_markup(reply_markup=services_kb(services, selected))
    await callback.answer()


@router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    await delete_all_drafts(callback.bot, callback.message.chat.id, state)
    services = await get_services()
    selected = []
    await state.set_state(BookingState.service)
    await state.update_data(selected_service_ids=[])
    await callback.message.edit_text(
        "Выберите услуги (можно несколько), затем нажмите «Далее»:",
        reply_markup=services_kb(services, selected)
    )


# --- Шаг 2: Выбор мастера ---
@router.callback_query(F.data == "back_to_masters")
async def back_to_masters(callback: CallbackQuery, state: FSMContext):
    for key in ('draft_master', 'draft_date', 'draft_time'):
        await delete_draft(callback.bot, callback.message.chat.id, state, key)
    data = await state.get_data()
    masters = await get_masters_for_services(data['selected_service_ids'])
    await state.set_state(BookingState.master)
    await callback.message.edit_text("Выберите мастера:", reply_markup=masters_kb(masters))


# --- Шаг 3: Выбор даты ---
@router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext):
    for key in ('draft_date', 'draft_time'):
        await delete_draft(callback.bot, callback.message.chat.id, state, key)
    await state.set_state(BookingState.date)
    await callback.message.edit_text("Выберите дату:", reply_markup=dates_kb(get_dates()))


# --- Шаг 4: Выбор времени ---
@router.callback_query(F.data == "back_to_times")
async def back_to_times(callback: CallbackQuery, state: FSMContext):
    await delete_draft(callback.bot, callback.message.chat.id, state, 'draft_time')
    data = await state.get_data()
    total_duration = data.get('service_total_duration', 30)
    slots = await get_available_slots(data['master_id'], data['date'], total_duration)
    await state.set_state(BookingState.time)
    await callback.message.edit_text("Выберите время:", reply_markup=times_kb(slots))


@router.callback_query(BookingState.service, F.data == "services_done")
async def services_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = data.get('selected_service_ids', [])
    if not selected_ids:
        await callback.answer("Выберите хотя бы одну услугу!", show_alert=True)
        return

    services = await get_services()
    service_map = {s['id']: s for s in services}
    selected_services = [service_map[sid] for sid in selected_ids if sid in service_map]

    names = ", ".join(s['name'] for s in selected_services)
    total_price = sum(s['price'] for s in selected_services)
    total_duration = sum(s['duration_min'] for s in selected_services)

    await state.update_data(
        service_names=names,
        service_total_price=total_price,
        service_total_duration=total_duration,
    )

    masters = await get_masters_for_services(selected_ids)
    if not masters:
        await callback.answer("Нет мастеров для выбранных услуг.", show_alert=True)
        return

    await delete_draft(callback.bot, callback.message.chat.id, state, 'draft_service')
    await state.set_state(BookingState.master)

    # Черновик — редактируем текущее сообщение (оно останется выше)
    await callback.message.edit_text(f"✅ Услуги: {names} — {total_price}₽")
    await state.update_data(draft_service=callback.message.message_id)
    # Новое меню отправляем ниже
    await callback.message.answer("Выберите мастера:", reply_markup=masters_kb(masters))


@router.callback_query(BookingState.master, F.data.startswith("master_"))
async def step_date(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    master = await get_master(master_id)

    await delete_draft(callback.bot, callback.message.chat.id, state, 'draft_master')
    await state.update_data(master_id=master_id, master_name=master['name'])
    await state.set_state(BookingState.date)

    # Черновик — редактируем текущее сообщение
    await callback.message.edit_text(f"✅ Мастер: {master['name']}")
    await state.update_data(draft_master=callback.message.message_id)
    await callback.message.answer("Выберите дату:", reply_markup=dates_kb(get_dates()))


@router.callback_query(BookingState.date, F.data.startswith("date_"))
async def step_time(callback: CallbackQuery, state: FSMContext):
    date = callback.data.split("_", 1)[1]
    data = await state.get_data()
    total_duration = data.get('service_total_duration', 30)
    slots = await get_available_slots(data['master_id'], date, total_duration)
    if not slots:
        await callback.answer("На эту дату нет свободного времени, выберите другую.", show_alert=True)
        return

    await delete_draft(callback.bot, callback.message.chat.id, state, 'draft_date')

    d = datetime.strptime(date, "%Y-%m-%d")
    weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    today = datetime.now().date()
    delta = (d.date() - today).days
    if delta == 0:
        date_label = f"{d.strftime('%d.%m')} (сегодня)"
    elif delta == 1:
        date_label = f"{d.strftime('%d.%m')} (завтра)"
    else:
        date_label = f"{d.strftime('%d.%m')} ({weekdays[d.weekday()]})"

    await state.update_data(date=date, date_label=date_label)
    await state.set_state(BookingState.time)

    await callback.message.edit_text(f"✅ Дата: {date_label}")
    await state.update_data(draft_date=callback.message.message_id)
    await callback.message.answer("Выберите время:", reply_markup=times_kb(slots))


@router.callback_query(BookingState.time, F.data.startswith("time_"))
async def step_comment(callback: CallbackQuery, state: FSMContext):
    time = callback.data.split("_", 1)[1]

    await delete_draft(callback.bot, callback.message.chat.id, state, 'draft_time')
    await state.update_data(time=time, comment_photos=[])
    await state.set_state(BookingState.comment)

    await callback.message.edit_text(f"✅ Время: {time}")
    await state.update_data(draft_time=callback.message.message_id)
    msg = await callback.message.answer(
        "💬 Напишите комментарий и/или отправьте фото (референсы, пожелания).\n"
        "Когда закончите — нажмите «Готово». Или пропустите:",
        reply_markup=skip_comment_kb()
    )
    await state.update_data(comment_menu_id=msg.message_id)


# --- Шаг 5: Комментарий + фото ---
@router.callback_query(BookingState.comment, F.data == "skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    await state.update_data(comment="", comment_photos=[])
    await state.set_state(BookingState.phone)
    msg = await callback.message.edit_text("📞 Введите ваш номер телефона:")
    await state.update_data(phone_msg_id=msg.message_id)


@router.callback_query(BookingState.comment, F.data == "comment_done")
async def comment_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingState.phone)
    msg = await callback.message.edit_text("📞 Введите ваш номер телефона:")
    await state.update_data(phone_msg_id=msg.message_id)


@router.message(BookingState.comment)
async def receive_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('comment_photos', [])

    if message.photo:
        if len(photos) >= 3:
            await message.delete()
            await message.answer("⚠️ Максимум 3 фото. Нажмите «Готово».")
            return
        photos.append(message.photo[-1].file_id)
        await state.update_data(comment_photos=photos)
        # Не удаляем фото — пусть висят в истории
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=data.get('comment_menu_id'),
                reply_markup=comment_photos_kb()
            )
        except Exception:
            pass
        remaining = 3 - len(photos)
        if remaining > 0:
            await message.answer(f"📷 {len(photos)}/3. Можно добавить ещё {remaining} шт.")
        else:
            await message.answer("📷 3/3. Лимит достигнут. Нажмите «Готово».")
        return

    if message.text:
        await state.update_data(comment=message.text)
        await message.delete()
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=data.get('comment_menu_id'),
                reply_markup=comment_photos_kb()
            )
        except Exception:
            pass


# --- Шаг 6: Телефон ---
async def _ask_phone(message_or_callback, state: FSMContext):
    await state.set_state(BookingState.phone)
    text = "Введите номер телефона или нажмите кнопку:"
    if isinstance(message_or_callback, Message):
        msg = await message_or_callback.answer(text, reply_markup=share_phone_kb())
    else:
        # Убираем инлайн-кнопки с меню комментария
        try:
            await message_or_callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        # Отправляем новым сообщением — оно окажется ниже всех фото
        msg = await message_or_callback.message.answer(text, reply_markup=share_phone_kb())
    await state.update_data(phone_msg_id=msg.message_id)


@router.callback_query(BookingState.comment, F.data == "skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    await state.update_data(comment="", comment_photos=[])
    await _ask_phone(callback, state)


@router.callback_query(BookingState.comment, F.data == "comment_done")
async def comment_done(callback: CallbackQuery, state: FSMContext):
    await _ask_phone(callback, state)


# Получение контакта через кнопку
@router.message(BookingState.phone, F.contact)
async def receive_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone
    await message.delete()
    await _process_phone(message, state, phone)


@router.message(BookingState.phone)
async def receive_phone(message: Message, state: FSMContext):
    import re
    if not message.text:
        return
    phone = message.text.strip()
    await message.delete()

    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    if not re.match(r'^\+?\d{10,15}$', cleaned):
        await message.answer("Неверный формат. Введите номер (например: +79991234567):")
        return

    await _process_phone(message, state, cleaned)


async def _process_phone(message: Message, state: FSMContext, phone: str):
    # Сразу переключаем state чтобы повторные сообщения не обрабатывались
    await state.set_state(BookingState.name)
    data = await state.get_data()
    if data.get('phone_msg_id'):
        try:
            await message.bot.delete_message(message.chat.id, data['phone_msg_id'])
        except Exception:
            pass
    await state.update_data(phone=phone)
    await message.answer(f"✅ Телефон: {phone}")
    msg = await message.answer("Как к вам обращаться? Введите имя:", reply_markup=remove_kb())
    await state.update_data(name_msg_id=msg.message_id)


# --- Шаг 7: Имя ---
@router.message(BookingState.name)
async def receive_name(message: Message, state: FSMContext):
    client_name = message.text.strip()
    await message.delete()
    data = await state.get_data()

    if data.get('name_msg_id'):
        try:
            await message.bot.delete_message(message.chat.id, data['name_msg_id'])
        except Exception:
            pass

    photos = data.get('comment_photos', [])
    tg_id = message.from_user.id
    username = message.from_user.username
    if username:
        tg_username = f"@{username}"
    else:
        tg_username = f"tg://user?id={tg_id}"

    photo_line = f"\nФото: {len(photos)} шт." if photos else ""
    summary = (
        f"<b>Проверьте вашу запись:</b>\n\n"
        f"Услуги: {data['service_names']} — {data['service_total_price']}₽\n"
        f"Мастер: {data['master_name']}\n"
        f"Дата: {data['date_label']}\n"
        f"Время: {data['time']}\n"
        f"Телефон: {data['phone']}\n"
        f"Имя: {client_name}\n"
        f"Комментарий: {data.get('comment') or '—'}"
        f"{photo_line}"
    )

    await state.update_data(client_name=client_name, tg_username=tg_username)
    msg = await message.answer(summary, reply_markup=confirm_kb(), parse_mode="HTML")
    await state.update_data(confirm_msg_id=msg.message_id)
    await state.set_state(BookingState.confirm)


# --- Подтверждение ---
@router.callback_query(BookingState.confirm, F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = await get_or_create_user(callback.from_user.id, callback.from_user.full_name)
    photos = data.get('comment_photos', [])
    photo_file_ids = ",".join(photos)

    for service_id in data['selected_service_ids']:
        await create_appointment(
            user_id=user_id,
            master_id=data['master_id'],
            service_id=service_id,
            date=data['date'],
            time=data['time'],
            comment=data.get('comment', ''),
            phone=data.get('phone', ''),
            client_name=data.get('client_name', ''),
            tg_username=data.get('tg_username', ''),
            photo_file_ids=photo_file_ids
        )

    await delete_all_drafts(callback.bot, callback.message.chat.id, state)

    await callback.message.edit_text(
        f"<b>Запись подтверждена!</b>\n\n"
        f"{data['service_names']}\n"
        f"Мастер: {data['master_name']}\n"
        f"{data['date_label']} в {data['time']}\n\n"
        f"Ждём вас, {data.get('client_name', '')}! За 24 и 2 часа до приёма придёт напоминание.",
        parse_mode="HTML",
        reply_markup=__import__('keyboards.client_kb', fromlist=['main_menu_kb']).main_menu_kb()
    )

    # Уведомление администратору
    tg_link = data.get('tg_username', '')
    if tg_link.startswith('@'):
        profile_str = f'<a href="https://t.me/{tg_link[1:]}">{tg_link}</a>'
    elif tg_link.startswith('tg://'):
        profile_str = f'<a href="{tg_link}">открыть профиль</a>'
    else:
        profile_str = '—'

    admin_text = (
        f"<b>Новая запись!</b>\n\n"
        f"Имя: {data.get('client_name', '—')}\n"
        f"Профиль: {profile_str}\n"
        f"Телефон: {data.get('phone', '—')}\n"
        f"Услуги: {data['service_names']}\n"
        f"Мастер: {data['master_name']}\n"
        f"Дата: {data['date_label']} в {data['time']}\n"
        f"Комментарий: {data.get('comment') or '—'}"
    )
    try:
        await callback.bot.send_message(ADMIN_TG_ID, admin_text, parse_mode="HTML")
        # Отправляем фото если есть
        if photos:
            from aiogram.types import InputMediaPhoto
            media = [InputMediaPhoto(media=fid) for fid in photos]
            media[0].caption = f"📷 Фото от клиента {data.get('client_name', '')}"
            await callback.bot.send_media_group(ADMIN_TG_ID, media=media)
    except Exception:
        pass

    await state.clear()


@router.callback_query(BookingState.confirm, F.data == "cancel_booking")
async def cancel_booking_flow(callback: CallbackQuery, state: FSMContext):
    await delete_all_drafts(callback.bot, callback.message.chat.id, state)
    from keyboards.client_kb import main_menu_kb
    await callback.message.edit_text("❌ Запись отменена.", reply_markup=main_menu_kb())
    await state.clear()