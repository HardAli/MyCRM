from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards import main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    text = (
        "Привет! Это мини-CRM бот для учета клиентов и компаний.\n"
        "Добавляй контакты, планируй звонки и отслеживай историю общения."
    )
    await message.answer(text, reply_markup=main_menu())
