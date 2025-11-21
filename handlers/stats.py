from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from db import get_session
from models import Client, ClientStatus, Interaction, InterestLevel

router = Router()


@router.message(F.text == "⏰ Задачи на сегодня")
async def tasks_today(message: Message) -> None:
    today = date.today()

    async with get_session() as session:
        stmt = select(Client).where(
            func.date(Client.next_contact_at) == today  # type: ignore[arg-type]
        )
        result = await session.execute(stmt)
        clients = result.scalars().all()

    if not clients:
        await message.answer("На сегодня задач нет")
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=client.name or client.phone,
                callback_data=f"client:{client.id}",
            )
        ]
        for client in clients
    ]

    await message.answer(
        "Клиенты для контакта сегодня:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.message(F.text == "📊 Статистика")
async def stats(message: Message) -> None:
    async with get_session() as session:
        result = await session.execute(select(func.count(Client.id)))
        total_clients = result.scalar_one() or 0

        result = await session.execute(
            select(func.count(Client.id)).where(Client.status == ClientStatus.NEW)
        )
        new_clients = result.scalar_one() or 0

        result = await session.execute(
            select(func.count(Client.id)).where(
                Client.status.in_(
                    [
                        ClientStatus.PLANNED_CALL,
                        ClientStatus.THINKING,
                        ClientStatus.NO_ANSWER,
                    ]
                )
            )
        )
        in_work = result.scalar_one() or 0

        result = await session.execute(
            select(func.count(Client.id)).where(Client.status == ClientStatus.AGREED)
        )
        agreed = result.scalar_one() or 0

        result = await session.execute(
            select(func.count(Client.id)).where(Client.status == ClientStatus.DECLINED)
        )
        declined = result.scalar_one() or 0

        result = await session.execute(
            select(func.count(Client.id)).where(Client.interest == InterestLevel.COLD)
        )
        cold = result.scalar_one() or 0

        result = await session.execute(
            select(func.count(Client.id)).where(Client.interest == InterestLevel.WARM)
        )
        warm = result.scalar_one() or 0

        result = await session.execute(
            select(func.count(Client.id)).where(Client.interest == InterestLevel.HOT)
        )
        hot = result.scalar_one() or 0

        result = await session.execute(
            select(func.count(Interaction.id)).where(
                func.date(Interaction.created_at) == date.today()  # type: ignore[arg-type]
            )
        )
        today_interactions = result.scalar_one() or 0

    text = (
        f"Всего клиентов: {total_clients}\n"
        f"Новые: {new_clients}\n"
        f"В работе: {in_work}\n"
        f"Согласились: {agreed}\n"
        f"Отказались: {declined}\n\n"
        f"Интерес — холодные: {cold}, тёплые: {warm}, горячие: {hot}\n"
        f"Контактов сегодня: {today_interactions}"
    )

    await message.answer(text)
