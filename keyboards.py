from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from models import ClientStatus, CompanySource, CompanyStatus, InterestLevel, PriorityLevel


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента"), KeyboardButton(text="🏢 Добавить компанию")],
            [KeyboardButton(text="📋 Мои клиенты"), KeyboardButton(text="📂 Компании")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚡ Быстрое добавление компаний")],
            [KeyboardButton(text="⏰ Задачи на сегодня"), KeyboardButton(text="🔍 Поиск")],
        ],
        resize_keyboard=True,
    )


def source_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Instagram", callback_data="source:Instagram"),
            InlineKeyboardButton(text="WhatsApp", callback_data="source:WhatsApp"),
        ],
        [InlineKeyboardButton(text="Звонок", callback_data="source:звонок")],
        [InlineKeyboardButton(text="Рекомендация", callback_data="source:рекомендация")],
        [InlineKeyboardButton(text="Другое", callback_data="source:другое")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def company_source_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Нашли сами", callback_data=f"company_source:{CompanySource.FOUND.value}")],
            [
                InlineKeyboardButton(
                    text="Рекомендация", callback_data=f"company_source:{CompanySource.RECOMMENDATION.value}"
                )
            ],
            [InlineKeyboardButton(text="Входящий", callback_data=f"company_source:{CompanySource.INBOUND.value}")],
        ]
    )


def priority_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Высокий", callback_data=f"priority:{PriorityLevel.HIGH.value}")],
            [InlineKeyboardButton(text="🟡 Средний", callback_data=f"priority:{PriorityLevel.MEDIUM.value}")],
            [InlineKeyboardButton(text="🔵 Низкий", callback_data=f"priority:{PriorityLevel.LOW.value}")],
        ]
    )


def company_status_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Не звонили", callback_data=f"comp_status:{CompanyStatus.NOT_CALLED.value}")],
        [InlineKeyboardButton(text="Исследуем", callback_data=f"comp_status:{CompanyStatus.RESEARCH.value}")],
        [InlineKeyboardButton(text="Не дозвонились", callback_data=f"comp_status:{CompanyStatus.NO_ANSWER.value}")],
        [InlineKeyboardButton(text="Переговоры", callback_data=f"comp_status:{CompanyStatus.NEGOTIATION.value}")],
        [InlineKeyboardButton(text="Клиент", callback_data=f"comp_status:{CompanyStatus.CLIENT.value}")],
        [InlineKeyboardButton(text="Отказ", callback_data=f"comp_status:{CompanyStatus.DECLINED.value}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def interest_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔵 Холодный", callback_data=f"interest:{InterestLevel.COLD.value}")],
        [InlineKeyboardButton(text="🟡 Тёплый", callback_data=f"interest:{InterestLevel.WARM.value}")],
        [InlineKeyboardButton(text="🔴 Горячий", callback_data=f"interest:{InterestLevel.HOT.value}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def client_status_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Новый", callback_data=f"status:{ClientStatus.NEW.value}")],
        [InlineKeyboardButton(text="Запланирован", callback_data=f"status:{ClientStatus.PLANNED_CALL.value}")],
        [InlineKeyboardButton(text="Не дозвонились", callback_data=f"status:{ClientStatus.NO_ANSWER.value}")],
        [InlineKeyboardButton(text="Думает", callback_data=f"status:{ClientStatus.THINKING.value}")],
        [InlineKeyboardButton(text="Согласился", callback_data=f"status:{ClientStatus.AGREED.value}")],
        [InlineKeyboardButton(text="Отказался", callback_data=f"status:{ClientStatus.DECLINED.value}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def call_result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Согласился", callback_data=f"callres:{ClientStatus.AGREED.value}")],
            [InlineKeyboardButton(text="❌ Отказался", callback_data=f"callres:{ClientStatus.DECLINED.value}")],
            [InlineKeyboardButton(text="🤔 Думает", callback_data=f"callres:{ClientStatus.THINKING.value}")],
            [InlineKeyboardButton(text="📵 Не дозвонился", callback_data=f"callres:{ClientStatus.NO_ANSWER.value}")],
        ]
    )


def next_contact_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сегодня", callback_data="next:same")],
            [InlineKeyboardButton(text="Завтра", callback_data="next:tomorrow")],
            [InlineKeyboardButton(text="Через 3 дня", callback_data="next:3days")],
            [InlineKeyboardButton(text="Без планирования", callback_data="next:none")],
        ]
    )
