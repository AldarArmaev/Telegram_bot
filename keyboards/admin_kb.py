from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💇 Услуги", callback_data="admin_services")],
        [InlineKeyboardButton(text="👤 Мастера", callback_data="admin_masters")],
        [InlineKeyboardButton(text="📅 Записи на сегодня", callback_data="admin_today")],
        [InlineKeyboardButton(text="🗓 Записи на 14 дней", callback_data="admin_14days")],
    ])


def services_list_kb(services: list):
    buttons = [
        [InlineKeyboardButton(
            text=f"{'✅' if s['is_active'] else '❌'} {s['name']} — {s['price']}₽",
            callback_data=f"admin_service_{s['id']}"
        )]
        for s in services
    ]
    buttons.append([InlineKeyboardButton(text="➕ Добавить услугу", callback_data="admin_add_service")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_detail_kb(service_id: int, is_active: bool):
    toggle_text = "❌ Деактивировать" if is_active else "✅ Активировать"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить цену", callback_data=f"admin_edit_price_{service_id}")],
        [InlineKeyboardButton(text="⏱ Изменить длительность", callback_data=f"admin_edit_dur_{service_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin_toggle_service_{service_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_delete_service_{service_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_services")],
    ])


def masters_list_kb(masters: list):
    buttons = [
        [InlineKeyboardButton(
            text=f"{'✅' if m['is_active'] else '❌'} {m['name']}",
            callback_data=f"admin_master_{m['id']}"
        )]
        for m in masters
    ]
    buttons.append([InlineKeyboardButton(text="➕ Добавить мастера", callback_data="admin_add_master")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def master_detail_kb(master_id: int, is_active: bool):
    toggle_text = "❌ Деактивировать" if is_active else "✅ Активировать"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓 Расписание", callback_data=f"admin_schedule_{master_id}")],
        [InlineKeyboardButton(text="💇 Услуги мастера", callback_data=f"admin_master_services_{master_id}")],
        [InlineKeyboardButton(text="🖼 Фото работ", callback_data=f"admin_photos_{master_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin_toggle_master_{master_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_masters")],
    ])


def photos_manage_kb(master_id: int, photos: list):
    buttons = []
    for p in photos:
        buttons.append([InlineKeyboardButton(
            text=f"🗑 Удалить фото #{p['id']}",
            callback_data=f"admin_del_photo_{p['id']}_{master_id}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Добавить фото", callback_data=f"admin_add_photo_{master_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_master_{master_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def weekdays_kb(master_id: int, schedule: dict):
    """schedule: {weekday: (start, end)}"""
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    buttons = []
    for i, day in enumerate(days):
        if i in schedule:
            s, e = schedule[i]
            text = f"✅ {day} {s}–{e}"
        else:
            text = f"➕ {day}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"admin_day_{master_id}_{i}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_master_{master_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def master_services_kb(master_id: int, all_services: list, linked_ids: list):
    buttons = []
    for s in all_services:
        check = "✅" if s['id'] in linked_ids else "☐"
        buttons.append([InlineKeyboardButton(
            text=f"{check} {s['name']}",
            callback_data=f"admin_toggle_ms_{master_id}_{s['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_master_{master_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_kb(back_cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Отмена", callback_data=back_cb)]
    ])