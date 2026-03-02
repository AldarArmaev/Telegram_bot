from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto

from keyboards.client_kb import masters_list_client_kb, master_profile_kb, main_menu_kb
from database.queries import get_masters_with_services

router = Router()


@router.callback_query(F.data == "masters_list")
async def show_masters_list(callback: CallbackQuery):
    masters = await get_masters_with_services()
    text = "👥 Выберите мастера:"
    kb = masters_list_client_kb(masters) if masters else main_menu_kb()
    if not masters:
        text = "Информация о мастерах пока не добавлена."

    # Если текущее сообщение — фото, удаляем и отправляем новое
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("view_master_"))
async def show_master_profile(callback: CallbackQuery):
    master_id = int(callback.data.split("_")[2])
    masters = await get_masters_with_services()
    master = next((m for m in masters if m['id'] == master_id), None)
    if not master:
        await callback.answer("Мастер не найден")
        return

    services_text = "\n".join(
        f"• {s['name']} — {s['price']}₽" for s in master['services']
    ) or "Услуги не указаны"

    text = f"👤 <b>{master['name']}</b>\n\n💇 Услуги:\n{services_text}"
    photos = master['photos']

    kb = master_profile_kb(master_id, bool(photos), 0, len(photos))

    if photos:
        # Удаляем старое сообщение и отправляем фото
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photos[0],
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text + "\n\n📷 Фото работ пока не добавлены.",
            reply_markup=kb,
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("mphoto_"))
async def navigate_master_photo(callback: CallbackQuery):
    _, master_id, index = callback.data.split("_")
    master_id, index = int(master_id), int(index)

    masters = await get_masters_with_services()
    master = next((m for m in masters if m['id'] == master_id), None)
    if not master:
        return

    photos = master['photos']
    services_text = "\n".join(f"• {s['name']} — {s['price']}₽" for s in master['services']) or "Услуги не указаны"
    text = f"👤 <b>{master['name']}</b>\n\n💇 Услуги:\n{services_text}"
    kb = master_profile_kb(master_id, True, index, len(photos))

    await callback.message.edit_media(
        media=InputMediaPhoto(media=photos[index], caption=text, parse_mode="HTML"),
        reply_markup=kb
    )


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()