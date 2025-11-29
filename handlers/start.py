from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    text = (
        "Привет! Это мини-CRM бот для учета клиентов и компаний.\n"
        "Добавляй контакты, планируй звонки и отслеживай историю общения."
    )
    await message.answer(text, reply_markup=main_menu())


@router.callback_query(F.data == "back:main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Главное меню", reply_markup=main_menu())
    await callback.answer()