from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from keyboards.client_kb import main_menu_kb
from database.queries import get_or_create_user

router = Router()


async def show_main_menu(target, edit=False):
    text = "👋 Главное меню"
    if edit and isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=main_menu_kb())
    elif isinstance(target, Message):
        await target.answer(text, reply_markup=main_menu_kb())


@router.message(CommandStart())
async def cmd_start(message: Message):
    await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await show_main_menu(message)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer("👋 Главное меню", reply_markup=main_menu_kb())
    else:
        await callback.message.edit_text("👋 Главное меню", reply_markup=main_menu_kb())