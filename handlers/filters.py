from __future__ import annotations

from typing import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from db import get_session
from models import Company, CompanyStatus


async def get_existing_company_statuses() -> list[CompanyStatus]:
    async with get_session() as session:
        result = await session.execute(select(Company.status).distinct())
        existing_statuses = set(result.scalars().all())
    ordered_statuses = [status for status in CompanyStatus if status in existing_statuses]
    return ordered_statuses


def build_status_filter_keyboard(
    prefix: str, statuses: Iterable[CompanyStatus]
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="Все", callback_data=f"{prefix}:all:0")]
    ]
    status_list = list(statuses)
    for i in range(0, len(status_list), 2):
        row_statuses = status_list[i : i + 2]
        buttons.append(
            [
                InlineKeyboardButton(
                    text=status.value,
                    callback_data=f"{prefix}:status-{status.value}:0",
                )
                for status in row_statuses
            ]
        )
    if not status_list:
        buttons.append([InlineKeyboardButton(text="Нет данных", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)