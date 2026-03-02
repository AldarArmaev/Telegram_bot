from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записаться", callback_data="book")],
        [InlineKeyboardButton(text="👥 Наши мастера", callback_data="masters_list")],
        [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")],
        [InlineKeyboardButton(text="📞 Связаться с администратором", callback_data="contacts")],
    ])


def services_kb(services: list, selected_ids: list = None):
    selected_ids = selected_ids or []
    buttons = []
    for s in services:
        check = "✅ " if s['id'] in selected_ids else ""
        buttons.append([InlineKeyboardButton(
            text=f"{check}{s['name']} — {s['price']}₽ ({s['duration_min']} мин)",
            callback_data=f"service_{s['id']}"
        )])
    row = []
    row.append(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    if selected_ids:
        row.append(InlineKeyboardButton(text="Далее ➡️", callback_data="services_done"))
    buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def masters_kb(masters: list):
    buttons = [
        [InlineKeyboardButton(text=m['name'], callback_data=f"master_{m['id']}")]
        for m in masters
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_services")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dates_kb(dates: list):
    buttons = [
        [InlineKeyboardButton(text=d['label'], callback_data=f"date_{d['value']}")]
        for d in dates
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_masters")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def times_kb(slots: list):
    rows = []
    row = []
    for i, slot in enumerate(slots):
        row.append(InlineKeyboardButton(text=slot, callback_data=f"time_{slot}"))
        if (i + 1) % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_dates")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_comment_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_comment")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_times")],
    ])


def comment_photos_kb():
    """Кнопка Готово появляется когда уже есть текст или фото."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово", callback_data="comment_done")],
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_comment")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_times")],
    ])


def share_phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Или введите номер вручную..."
    )


def remove_kb():
    return ReplyKeyboardRemove()


def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")],
    ])


def my_appointments_kb(appointments: list):
    buttons = [
        [InlineKeyboardButton(
            text=f"{a['date']} {a['time']} — {a['service_name']}",
            callback_data=f"appt_{a['id']}"
        )]
        for a in appointments
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def appointment_detail_kb(appt_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_appt_{appt_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_appointments")],
    ])


def masters_list_client_kb(masters: list):
    buttons = [
        [InlineKeyboardButton(text=f"👤 {m['name']}", callback_data=f"view_master_{m['id']}")]
        for m in masters
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def master_profile_kb(master_id: int, has_photos: bool, photo_index: int = 0, total_photos: int = 0):
    buttons = []
    if has_photos and total_photos > 1:
        nav = []
        if photo_index > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mphoto_{master_id}_{photo_index - 1}"))
        nav.append(InlineKeyboardButton(text=f"{photo_index + 1}/{total_photos}", callback_data="noop"))
        if photo_index < total_photos - 1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mphoto_{master_id}_{photo_index + 1}"))
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="◀️ Назад к мастерам", callback_data="masters_list")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_confirm_kb(appt_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, отменить", callback_data=f"do_cancel_{appt_id}")],
        [InlineKeyboardButton(text="Нет", callback_data=f"appt_{appt_id}")],
    ])