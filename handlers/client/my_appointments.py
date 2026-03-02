from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.client_kb import my_appointments_kb, appointment_detail_kb, cancel_confirm_kb, main_menu_kb
from database.queries import get_user_appointments, get_appointment, cancel_appointment, get_or_create_user
from config import ADMIN_TG_ID

router = Router()


@router.callback_query(F.data == "my_appointments")
async def show_appointments(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = await get_or_create_user(callback.from_user.id, callback.from_user.full_name)
    appointments = await get_user_appointments(user_id)

    if not appointments:
        await callback.message.edit_text(
            "У вас нет активных записей.",
            reply_markup=main_menu_kb()
        )
        return

    await callback.message.edit_text(
        "Ваши записи:", reply_markup=my_appointments_kb(appointments)
    )


@router.callback_query(F.data.startswith("appt_"))
async def show_appointment_detail(callback: CallbackQuery):
    appt_id = int(callback.data.split("_")[1])
    a = await get_appointment(appt_id)
    if not a:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    text = (
        f"📋 <b>Детали записи:</b>\n\n"
        f"💇 Услуга: {a['service_name']}\n"
        f"👤 Мастер: {a['master_name']}\n"
        f"📅 Дата: {a['date']} в {a['time']}\n"
        f"💬 Комментарий: {a['comment'] or '—'}"
    )
    await callback.message.edit_text(text, reply_markup=appointment_detail_kb(appt_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("cancel_appt_"))
async def ask_cancel(callback: CallbackQuery):
    appt_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        "Вы уверены, что хотите отменить запись?",
        reply_markup=cancel_confirm_kb(appt_id)
    )


@router.callback_query(F.data.startswith("do_cancel_"))
async def do_cancel(callback: CallbackQuery):
    appt_id = int(callback.data.split("_")[2])
    a = await get_appointment(appt_id)
    await cancel_appointment(appt_id)

    await callback.message.edit_text("❌ Запись отменена.", reply_markup=main_menu_kb())

    if a:
        try:
            await callback.bot.send_message(
                ADMIN_TG_ID,
                f"❌ <b>Отмена записи</b>\n\n"
                f"👤 {callback.from_user.full_name}\n"
                f"💇 {a['service_name']} у {a['master_name']}\n"
                f"📅 {a['date']} в {a['time']}",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery):
    await callback.message.edit_text(
        "📞 <b>Контакты администратора:</b>\n\n"
        "Телефон: +7 (999) 123-45-67\n"
        "Telegram: @admin_username\n"
        "Режим работы: пн-сб 9:00–19:00",
        reply_markup=__import__('keyboards.client_kb', fromlist=['main_menu_kb']).main_menu_kb(),
        parse_mode="HTML"
    )