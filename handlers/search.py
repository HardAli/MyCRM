from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from db import get_session
from models import Client, Company


def normalize_phone_for_search(value: str | None) -> str:
    digits = "".join(ch for ch in value or "" if ch.isdigit())
    if digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits

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
async def perform_search(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("mode")
    text = message.text or ""
    results_buttons = []
    async with get_session() as session:
        if mode == "phone":
            normalized_query = normalize_phone_for_search(text)
            client_stmt = select(Client)
            for client in (await session.execute(client_stmt)).scalars().all():
                if normalized_query in normalize_phone_for_search(client.phone):
                    results_buttons.append(
                        [
                            InlineKeyboardButton(
                                text=f"👤 {client.phone}", callback_data=f"client:{client.id}"
                            )
                        ]
                    )

            company_stmt = select(Company)
            for company in (await session.execute(company_stmt)).scalars().all():
                if normalized_query in normalize_phone_for_search(company.phone):
                    results_buttons.append(
                        [
                            InlineKeyboardButton(
                                text=f"🏢 {company.name}", callback_data=f"company:{company.id}"
                            )
                        ]
                    )
        elif mode == "name":
            stmt = select(Client).where(Client.name.ilike(f"%{text}%"))  # type: ignore[arg-type]
            for client in (await session.execute(stmt)).scalars().all():
                results_buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"👤 {client.name or client.phone}",
                            callback_data=f"client:{client.id}",
                        )
                    ]
                )

                company_stmt = select(Company).where(Company.name.ilike(f"%{text}%"))  # type: ignore[arg-type]
                for company in (await session.execute(company_stmt)).scalars().all():
                    results_buttons.append(
                        [
                            InlineKeyboardButton(
                                text=f"🏢 {company.name}", callback_data=f"company:{company.id}"
                            )
                        ]
                )
        elif mode == "company":
            stmt = select(Company).where(Company.name.ilike(f"%{text}%"))  # type: ignore[arg-type]
            for company in (await session.execute(stmt)).scalars().all():
                results_buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"🏢 {company.name}", callback_data=f"company:{company.id}"
                        )
                    ]
                )

                client_stmt = (
                    select(Client)
                    .join(Company)
                    .where(Company.name.ilike(f"%{text}%"))  # type: ignore[arg-type]
                )
                for client in (await session.execute(client_stmt)).scalars().all():
                    results_buttons.append(
                        [
                            InlineKeyboardButton(
                                text=f"👤 {client.name or client.phone}",
                                callback_data=f"client:{client.id}",
                            )
                        ]
                )
    await state.clear()
    if not results_buttons:
        await message.answer("Ничего не найдено")
        return
    await message.answer(
        "Результаты:", reply_markup=InlineKeyboardMarkup(inline_keyboard=results_buttons)
    )
