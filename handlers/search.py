from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import Client, Company

router = Router()


class SearchStates(StatesGroup):
    mode = State()
    query = State()


@router.message(F.text == "🔍 Поиск")
async def search_menu(message: Message, state: FSMContext) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="По номеру", callback_data="search:phone")],
            [InlineKeyboardButton(text="По имени", callback_data="search:name")],
            [InlineKeyboardButton(text="По компании", callback_data="search:company")],
        ]
    )
    await state.clear()
    await message.answer("Выберите тип поиска", reply_markup=keyboard)


@router.callback_query(F.data.startswith("search:"))
async def choose_search(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split(":", 1)[1]
    await state.update_data(mode=mode)
    await state.set_state(SearchStates.query)
    await callback.message.answer("Введите строку для поиска")
    await callback.answer()


@router.message(SearchStates.query)
async def perform_search(message: Message, state: FSMContext, session: AsyncSession = get_session()) -> None:
    data = await state.get_data()
    mode = data.get("mode")
    text = message.text or ""
    results_buttons = []
    if mode == "phone":
        stmt = select(Client).where(Client.phone.like(f"%{text}%"))
        for client in (await session.execute(stmt)).scalars().all():
            results_buttons.append(
                [InlineKeyboardButton(text=client.phone, callback_data=f"client:{client.id}")]
            )
    elif mode == "name":
        stmt = select(Client).where(Client.name.ilike(f"%{text}%"))  # type: ignore[arg-type]
        for client in (await session.execute(stmt)).scalars().all():
            results_buttons.append(
                [InlineKeyboardButton(text=client.name or client.phone, callback_data=f"client:{client.id}")]
            )
    elif mode == "company":
        stmt = select(Company).where(Company.name.ilike(f"%{text}%"))  # type: ignore[arg-type]
        for company in (await session.execute(stmt)).scalars().all():
            results_buttons.append(
                [InlineKeyboardButton(text=company.name, callback_data=f"company:{company.id}")]
            )
    await state.clear()
    if not results_buttons:
        await message.answer("Ничего не найдено")
        return
    await message.answer(
        "Результаты:", reply_markup=InlineKeyboardMarkup(inline_keyboard=results_buttons)
    )
