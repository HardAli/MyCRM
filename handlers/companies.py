from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from config import PAGE_SIZE
from db import get_session
from keyboards import company_source_keyboard, company_status_keyboard, main_menu, priority_keyboard
from models import Company, CompanySource, CompanyStatus, PriorityLevel, Suggestion, SuggestionType

router = Router()


class AddCompanyStates(StatesGroup):
    name = State()
    city = State()
    niche = State()
    phone = State()
    source = State()
    priority = State()
    contact_person = State()
    note = State()


def format_company(company: Company) -> str:
    lines = [
        f"<b>{company.name}</b> ({company.city or 'город не указан'})",
        f"Ниша: {company.niche or '—'}",
        f"Телефон: {company.phone or '—'}",
        f"Источник: {company.source.value}",
        f"Статус: {company.status.value}",
        f"Приоритет: {company.priority.value}",
        f"Контактное лицо: {company.contact_person or '—'}",
        f"Комментарий: {company.note or '—'}",
    ]
    return "\n".join(lines)


def build_suggestions_keyboard(values: list[str], prefix: str) -> InlineKeyboardMarkup | None:
    if not values:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(values), 2):
        pair = values[i : i + 2]
        rows.append(
            [InlineKeyboardButton(text=value, callback_data=f"{prefix}:{value}") for value in pair]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def get_suggestions(suggestion_type: SuggestionType) -> list[str]:
    async with get_session() as session:
        stmt = (
            select(Suggestion.value)
            .where(Suggestion.type == suggestion_type)
            .order_by(Suggestion.value)
        )
        return (await session.execute(stmt)).scalars().all()


async def remember_suggestion(value: str | None, suggestion_type: SuggestionType) -> None:
    if not value:
        return
    async with get_session() as session:
        exists_stmt = select(Suggestion).where(
            Suggestion.type == suggestion_type, Suggestion.value == value
        )
        exists = (await session.execute(exists_stmt)).scalar_one_or_none()
        if exists:
            return
        session.add(Suggestion(type=suggestion_type, value=value))
        await session.commit()


async def send_city_prompt(message: Message) -> None:
    suggestions = await get_suggestions(SuggestionType.CITY)
    keyboard = build_suggestions_keyboard(suggestions, "city_suggestion")
    await message.answer(
        "Город (выберите из предложенных вариантов или отправьте свой):",
        reply_markup=keyboard,
    )


async def send_niche_prompt(message: Message) -> None:
    suggestions = await get_suggestions(SuggestionType.NICHE)
    keyboard = build_suggestions_keyboard(suggestions, "niche_suggestion")
    await message.answer(
        "Ниша/сфера (выберите кнопку или отправьте свой вариант):",
        reply_markup=keyboard,
    )


@router.message(F.text == "🏢 Добавить компанию")
@router.message(Command("add_company"))
async def start_add_company(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddCompanyStates.name)
    await message.answer("Название компании:")


@router.message(AddCompanyStates.name)
async def company_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(AddCompanyStates.city)
    await send_city_prompt(message)


@router.message(AddCompanyStates.city)
async def company_city(message: Message, state: FSMContext) -> None:
    city = None if message.text == "-" else message.text
    await state.update_data(city=city)
    await remember_suggestion(city, SuggestionType.CITY)
    await state.set_state(AddCompanyStates.niche)
    await send_niche_prompt(message)

    @router.callback_query(AddCompanyStates.city, F.data.startswith("city_suggestion:"))
    async def company_city_suggestion(callback: CallbackQuery, state: FSMContext) -> None:
        city = callback.data.split(":", 1)[1]
        await state.update_data(city=city)
        await remember_suggestion(city, SuggestionType.CITY)
        await state.set_state(AddCompanyStates.niche)
        await callback.answer(f"Выбран город: {city}")
        await send_niche_prompt(callback.message)


@router.message(AddCompanyStates.niche)
async def company_niche(message: Message, state: FSMContext) -> None:
    niche = None if message.text == "-" else message.text
    await state.update_data(niche=niche)
    await remember_suggestion(niche, SuggestionType.NICHE)
    await state.set_state(AddCompanyStates.phone)
    await message.answer("Телефон (или '-' если нет):")


@router.callback_query(AddCompanyStates.niche, F.data.startswith("niche_suggestion:"))
async def company_niche_suggestion(callback: CallbackQuery, state: FSMContext) -> None:
    niche = callback.data.split(":", 1)[1]
    await state.update_data(niche=niche)
    await remember_suggestion(niche, SuggestionType.NICHE)
    await state.set_state(AddCompanyStates.phone)
    await callback.answer(f"Выбрана ниша: {niche}")
    await callback.message.answer("Телефон (или '-' если нет):")


@router.message(AddCompanyStates.phone)
async def company_phone(message: Message, state: FSMContext) -> None:
    phone = None if message.text == "-" else message.text
    await state.update_data(phone=phone)
    await state.set_state(AddCompanyStates.source)
    await message.answer("Источник", reply_markup=company_source_keyboard())


@router.callback_query(AddCompanyStates.source, F.data.startswith("company_source:"))
async def company_source(callback: CallbackQuery, state: FSMContext) -> None:
    source = CompanySource(callback.data.split(":", 1)[1])
    await state.update_data(source=source.value)
    await state.set_state(AddCompanyStates.priority)
    await callback.message.edit_text("Приоритет", reply_markup=priority_keyboard())
    await callback.answer()


@router.callback_query(AddCompanyStates.priority, F.data.startswith("priority:"))
async def company_priority(callback: CallbackQuery, state: FSMContext) -> None:
    level = PriorityLevel(callback.data.split(":", 1)[1])
    await state.update_data(priority=level.value)
    await state.set_state(AddCompanyStates.contact_person)
    await callback.message.edit_text("Контактное лицо:")
    await callback.answer()


@router.message(AddCompanyStates.contact_person)
async def company_contact(message: Message, state: FSMContext) -> None:
    contact = None if message.text == "-" else message.text
    await state.update_data(contact_person=contact)
    await state.set_state(AddCompanyStates.note)
    await message.answer("Комментарий или '-' для пропуска:")


@router.message(AddCompanyStates.note)
async def company_note(message: Message, state: FSMContext) -> None:
    note = None if message.text == "-" else message.text
    data = await state.get_data()
    company = Company(
        name=data.get("name"),
        city=data.get("city"),
        niche=data.get("niche"),
        phone=data.get("phone"),
        source=CompanySource(data.get("source", CompanySource.FOUND.value)),
        priority=PriorityLevel(data.get("priority", PriorityLevel.MEDIUM.value)),
        contact_person=data.get("contact_person"),
        note=note,
    )
    async with get_session() as session:
        session.add(company)
        await session.commit()
    await state.clear()
    await message.answer(format_company(company), parse_mode=ParseMode.HTML, reply_markup=main_menu())


@router.message(F.text == "📂 Компании")
async def list_companies(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Все", callback_data="companies:all:0")],
            [InlineKeyboardButton(text="Не звонили", callback_data="companies:not_called:0")],
            [InlineKeyboardButton(text="Высокий приоритет", callback_data="companies:high:0")],
            [InlineKeyboardButton(text="Нашли сами", callback_data="companies:found:0")],
        ]
    )
    await message.answer("Выберите фильтр", reply_markup=keyboard)


@router.callback_query(F.data.startswith("companies:"))
async def paginate_companies(callback: CallbackQuery) -> None:
    _, filter_name, page_str = callback.data.split(":")
    page = int(page_str)
    stmt = select(Company)
    if filter_name == "not_called":
        stmt = stmt.where(Company.status == CompanyStatus.NOT_CALLED)
    elif filter_name == "high":
        stmt = stmt.where(Company.priority == PriorityLevel.HIGH)
    elif filter_name == "found":
        stmt = stmt.where(Company.source == CompanySource.FOUND)
    stmt = stmt.order_by(Company.created_at.desc()).offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    async with get_session() as session:
        companies = (await session.execute(stmt)).scalars().all()
    rows = []
    for comp in companies:
        rows.append(
            [InlineKeyboardButton(text=f"{comp.name} ({comp.city or '-'})", callback_data=f"company:{comp.id}")]
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"companies:{filter_name}:{page-1}"))
    if len(companies) == PAGE_SIZE:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"companies:{filter_name}:{page+1}"))
    if nav:
        rows.append(nav)
    if not rows:
        rows.append([InlineKeyboardButton(text="Нет компаний", callback_data="noop")])

    await callback.message.edit_text(
        "Компании:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("company:"))
async def show_company(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        company = (await session.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
        if not company:
            await callback.message.answer("Компания не найдена")
            await callback.answer()
            return
    await callback.message.answer(
        format_company(company),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✏️ Статус", callback_data=f"comp_status_change:{company.id}"),
                    InlineKeyboardButton(text="🔥 Приоритет", callback_data=f"comp_priority:{company.id}"),
                ],
                [InlineKeyboardButton(text="📝 Комментарий", callback_data=f"comp_note:{company.id}")],
            ]
        ),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("comp_status_change:"))
async def change_company_status(callback: CallbackQuery, state: FSMContext) -> None:
    company_id = int(callback.data.split(":")[1])
    await state.update_data(company_id=company_id, change_type="status")
    await callback.message.answer("Статус компании", reply_markup=company_status_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("comp_priority:"))
async def change_company_priority(callback: CallbackQuery, state: FSMContext) -> None:
    company_id = int(callback.data.split(":")[1])
    await state.update_data(company_id=company_id, change_type="priority")
    await callback.message.answer("Приоритет компании", reply_markup=priority_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("comp_note:"))
async def change_company_note(callback: CallbackQuery, state: FSMContext) -> None:
    company_id = int(callback.data.split(":")[1])
    await state.update_data(company_id=company_id, change_type="note")
    await state.set_state(AddCompanyStates.note)
    await callback.message.answer("Введите новый комментарий")
    await callback.answer()


@router.callback_query(F.data.startswith("comp_status:"))
async def apply_company_status(callback: CallbackQuery, state: FSMContext) -> None:
    status = CompanyStatus(callback.data.split(":", 1)[1])
    data = await state.get_data()
    if data.get("change_type") != "status":
        await callback.answer()
        return
    async with get_session() as session:
        company = (await session.execute(select(Company).where(Company.id == data.get("company_id")))).scalar_one()
        company.status = status
        await session.commit()
    await state.clear()
    await callback.message.answer("Статус обновлен")
    await callback.answer()


@router.callback_query(F.data.startswith("priority:"))
async def apply_company_priority(callback: CallbackQuery, state: FSMContext) -> None:
    level = PriorityLevel(callback.data.split(":", 1)[1])
    data = await state.get_data()
    if data.get("change_type") != "priority":
        await callback.answer()
        return
    async with get_session() as session:
        company = (await session.execute(select(Company).where(Company.id == data.get("company_id")))).scalar_one()
        company.priority = level
        await session.commit()
    await state.clear()
    await callback.message.answer("Приоритет обновлен")
    await callback.answer()


@router.message(AddCompanyStates.note)
async def apply_company_note(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("change_type") != "note":
        return
    async with get_session() as session:
        company = (await session.execute(select(Company).where(Company.id == data.get("company_id")))).scalar_one()
        company.note = message.text
        await session.commit()
    await state.clear()
    await message.answer("Комментарий обновлен")
