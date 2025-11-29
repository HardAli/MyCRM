from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from db import get_session
from keyboards import (
    call_result_keyboard,
    client_status_keyboard,
    interest_keyboard,
    main_menu,
    next_contact_keyboard,
    source_keyboard,
)
from models import Client, ClientStatus, Company, Interaction, InteractionResult, InterestLevel
from handlers.filters import build_status_filter_keyboard, get_existing_company_statuses

router = Router()


class AddClientStates(StatesGroup):
    phone = State()
    name = State()
    source = State()
    interest = State()
    next_contact = State()
    comment = State()


def normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit() or ch == "+")
    if digits.startswith("8"):
        digits = "+7" + digits[1:]
    if not digits.startswith("+"):
        digits = "+" + digits
    return digits


def build_whatsapp_url(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return None
    return f"https://wa.me/{digits}"


def format_client(client: Client, last_interaction: Interaction | None = None) -> str:
    interest_map = {
        InterestLevel.COLD: "🔵 Холодный",
        InterestLevel.WARM: "🟡 Тёплый",
        InterestLevel.HOT: "🔴 Горячий",
    }
    status_map = {
        ClientStatus.NEW: "Новый",
        ClientStatus.PLANNED_CALL: "Запланирован звонок",
        ClientStatus.NO_ANSWER: "Не дозвонились",
        ClientStatus.THINKING: "Думает",
        ClientStatus.AGREED: "Согласился",
        ClientStatus.DECLINED: "Отказался",
    }
    phone = f"<code>{client.phone}</code>" if client.phone else "—"
    lines = [
        f"<b>{client.name or 'Без имени'}</b> — {phone}",
        f"Статус: {status_map.get(client.status, client.status.value)}",
        f"Интерес: {interest_map.get(client.interest, client.interest.value)}",
        f"Источник: {client.source}",
    ]
    if client.company:
        lines.append(f"Компания: {client.company.name}")
    if client.next_contact_at:
        lines.append(f"Следующий контакт: {client.next_contact_at:%d.%m.%Y %H:%M}")
    if last_interaction:
        comment = last_interaction.comment or "без комментария"
        lines.append(
            f"Последнее общение: {last_interaction.created_at:%d.%m %H:%M} — {comment}"
        )
    return "\n".join(lines)


async def get_last_interaction(session: AsyncSession, client_id: int) -> Interaction | None:
    stmt = (
        select(Interaction)
        .where(Interaction.client_id == client_id)
        .order_by(Interaction.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.message(F.text == "➕ Добавить клиента")
@router.message(Command("add_client"))
async def start_add_client(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddClientStates.phone)
    await message.answer("Введите номер телефона клиента (можно прислать контактом).")


@router.message(AddClientStates.phone)
async def add_client_phone(message: Message, state: FSMContext) -> None:
    phone = message.text or (message.contact.phone_number if message.contact else None)
    if not phone:
        await message.answer("Не вижу номера телефона, отправьте цифрами или контактом.")
        return
    normalized = normalize_phone(phone)
    await state.update_data(phone=normalized)
    await state.set_state(AddClientStates.name)
    await message.answer("Имя клиента (или пропустите, отправив '-'):")


@router.message(AddClientStates.name)
async def add_client_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("comment_client_id"):
        return await save_comment(message, state)  # type: ignore[arg-type]
    name = None if (message.text == "-" or not message.text) else message.text
    await state.update_data(name=name)
    await state.set_state(AddClientStates.source)
    await message.answer("Источник лида?", reply_markup=source_keyboard())


@router.callback_query(AddClientStates.source, F.data.startswith("source:"))
async def add_client_source(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(source=callback.data.split(":", 1)[1])
    await state.set_state(AddClientStates.interest)
    await callback.message.edit_text("Степень интереса?", reply_markup=interest_keyboard())
    await callback.answer()


@router.callback_query(AddClientStates.interest, F.data.startswith("interest:"))
async def add_client_interest(callback: CallbackQuery, state: FSMContext) -> None:
    level = InterestLevel(callback.data.split(":", 1)[1])
    await state.update_data(interest=level.value)
    await state.set_state(AddClientStates.next_contact)
    await callback.message.edit_text("Запланировать контакт?", reply_markup=next_contact_keyboard())
    await callback.answer()


def resolve_next_contact(choice: str) -> datetime | None:
    now = datetime.utcnow()
    if choice == "same":
        return now.replace(hour=12, minute=0, second=0, microsecond=0)
    if choice == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    if choice == "3days":
        return (now + timedelta(days=3)).replace(hour=12, minute=0, second=0, microsecond=0)
    return None


@router.callback_query(AddClientStates.next_contact, F.data.startswith("next:"))
async def add_client_next_contact(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    choice = callback.data.split(":", 1)[1]
    await state.update_data(next_contact=choice)
    data = await state.get_data()
    await state.clear()

    phone = data.get("phone")
    name = data.get("name")
    source = data.get("source", "другое")
    interest = InterestLevel(data.get("interest", InterestLevel.COLD.value))
    next_contact_at = resolve_next_contact(choice)

    client = Client(
        phone=phone,
        name=name,
        source=source,
        interest=interest,
        next_contact_at=next_contact_at,
    )
    async with get_session() as session:
        try:
            session.add(client)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await callback.message.answer("Клиент с таким телефоном уже существует.")
            await callback.answer()
            return

        last_interaction = await get_last_interaction(session, client.id)
        message_text = format_client(client, last_interaction)

    await callback.message.answer(
        message_text, parse_mode=ParseMode.HTML, reply_markup=main_menu()
    )
    await callback.answer()


@router.message(F.text == "📋 Мои клиенты")
async def list_clients(message: Message) -> None:
    statuses = await get_existing_company_statuses()
    keyboard = build_status_filter_keyboard("clients", statuses)
    await message.answer("Выберите фильтр по статусу компании", reply_markup=keyboard)


@router.callback_query(F.data.startswith("clients:"))
async def paginate_clients(callback: CallbackQuery) -> None:
    _, filter_name, page_str = callback.data.split(":")
    page = int(page_str)
    stmt = select(Client)
    if filter_name.startswith("status-"):
        status_value = filter_name.split("-", 1)[1]
        stmt = stmt.join(Client.company).where(Company.status == CompanyStatus(status_value))
    stmt = stmt.order_by(Client.created_at.desc()).offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    async with get_session() as session:
        result = await session.execute(stmt)
        clients = result.scalars().all()

    keyboard_rows = []
    for client in clients:
        keyboard_rows.append(
            [InlineKeyboardButton(text=client.name or client.phone, callback_data=f"client:{client.id}")]
        )
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"clients:{filter_name}:{page-1}"))
    if len(clients) == PAGE_SIZE:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"clients:{filter_name}:{page+1}"))
    if nav_row:
        keyboard_rows.append(nav_row)

    if not keyboard_rows:
        keyboard_rows.append([InlineKeyboardButton(text="Нет данных", callback_data="noop")])

    await callback.message.edit_text(
        "Список клиентов:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("client:"))
async def show_client(callback: CallbackQuery) -> None:
    client_id = int(callback.data.split(":")[1])
    stmt = select(Client).where(Client.id == client_id)
    async with get_session() as session:
        client = (await session.execute(stmt)).scalar_one_or_none()
        if not client:
            await callback.message.answer("Клиент не найден")
            await callback.answer()
            return
        last_interaction = await get_last_interaction(session, client.id)
        message_text = format_client(client, last_interaction)

    buttons = [
        [
            InlineKeyboardButton(text="✏️ Статус", callback_data=f"status_change:{client.id}"),
            InlineKeyboardButton(text="🔥 Интерес", callback_data=f"interest_change:{client.id}"),
        ],
        [
            InlineKeyboardButton(text="📝 Комментарий", callback_data=f"comment:{client.id}"),
            InlineKeyboardButton(text="📜 История", callback_data=f"history:{client.id}"),
        ],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_client:{client.id}")],
        [
            InlineKeyboardButton(text="⏰ Следующий контакт", callback_data=f"setnext:{client.id}"),
            InlineKeyboardButton(text="📞 Результат звонка", callback_data=f"call:{client.id}"),
        ],
    ]

    whatsapp_url = build_whatsapp_url(client.phone)
    if whatsapp_url:
        buttons.insert(0, [InlineKeyboardButton(text="💬 Открыть WhatsApp", url=whatsapp_url)])

    await callback.message.answer(
        message_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("status_change:"))
async def change_status(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[1])
    await state.update_data(target_client_id=client_id, change_type="status")
    await callback.message.answer("Выберите статус", reply_markup=client_status_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("interest_change:"))
async def change_interest(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[1])
    await state.update_data(target_client_id=client_id, change_type="interest")
    await callback.message.answer("Степень интереса", reply_markup=interest_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("status:"))
async def apply_status(callback: CallbackQuery, state: FSMContext) -> None:
    status = ClientStatus(callback.data.split(":", 1)[1])
    data = await state.get_data()
    client_id = data.get("target_client_id")
    change_type = data.get("change_type")
    if change_type != "status" or not client_id:
        await callback.answer()
        return
    async with get_session() as session:
        client = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one()
        client.status = status
        session.add(client)
        await session.commit()
    await state.clear()
    await callback.message.answer("Статус обновлен")
    await callback.answer()


@router.callback_query(F.data.startswith("interest:"))
async def apply_interest(callback: CallbackQuery, state: FSMContext) -> None:
    interest = InterestLevel(callback.data.split(":", 1)[1])
    data = await state.get_data()
    client_id = data.get("target_client_id")
    change_type = data.get("change_type")
    if change_type != "interest" or not client_id:
        await callback.answer()
        return
    async with get_session() as session:
        client = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one()
        client.interest = interest
        session.add(client)
        await session.commit()
    await state.clear()
    await callback.message.answer("Интерес обновлен")
    await callback.answer()


@router.callback_query(F.data.startswith("comment:"))
async def add_comment_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[1])
    await state.update_data(comment_client_id=client_id)
    await state.set_state(AddClientStates.comment)
    await callback.message.answer("Введите комментарий для истории")
    await callback.answer()


@router.message(AddClientStates.comment)
async def save_comment(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    client_id = data.get("comment_client_id")
    if not client_id:
        return
    if message.text == "-":
        await state.clear()
        await message.answer("Пропущено")
        return
    comment_text = message.text or ""
    interaction = Interaction(
        client_id=client_id,
        result=InteractionResult.CALL,
        status_after=ClientStatus.NEW,
        comment=comment_text,
    )
    async with get_session() as session:
        session.add(interaction)
        await session.commit()
    await message.answer("Комментарий сохранен")
    await state.clear()


@router.callback_query(F.data.startswith("history:"))
async def show_history(callback: CallbackQuery) -> None:
    client_id = int(callback.data.split(":")[1])
    stmt = (
        select(Interaction)
        .where(Interaction.client_id == client_id)
        .order_by(Interaction.created_at.desc())
        .limit(10)
    )
    async with get_session() as session:
        interactions = (await session.execute(stmt)).scalars().all()
    if not interactions:
        await callback.message.answer("История пуста")
        await callback.answer()
        return
    lines = [
        f"{i.created_at:%d.%m %H:%M} — {i.result.value} — {i.status_after.value}\n{i.comment or ''}"
        for i in interactions
    ]
    await callback.message.answer("\n\n".join(lines))
    await callback.answer()


@router.callback_query(F.data.startswith("setnext:"))
async def set_next(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[1])
    await state.update_data(next_client_id=client_id)
    await state.set_state(AddClientStates.next_contact)
    await callback.message.answer("Когда связаться?", reply_markup=next_contact_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("call:"))
async def call_result(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[1])
    await state.update_data(target_client_id=client_id, change_type="call")
    await callback.message.answer("Зафиксируйте результат звонка", reply_markup=call_result_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("callres:"))
async def apply_call_result(
    callback: CallbackQuery, state: FSMContext
) -> None:
    status = ClientStatus(callback.data.split(":", 1)[1])
    data = await state.get_data()
    client_id = data.get("target_client_id")
    if not client_id:
        await callback.answer()
        return
    async with get_session() as session:
        client = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one()
        client.status = status
        interaction = Interaction(
            client_id=client.id,
            result=InteractionResult.CALL,
            status_after=status,
            comment=None,
        )
        session.add_all([client, interaction])
        await session.commit()
    await state.clear()
    await callback.message.answer(
        "Результат звонка сохранен. Добавить комментарий текстом? Отправьте сообщение, либо '-' чтобы пропустить."
    )
    await state.update_data(comment_client_id=client.id)
    await state.set_state(AddClientStates.comment)
    await callback.answer()


@router.callback_query(AddClientStates.next_contact, F.data.startswith("next:"))
async def handle_next_for_existing(
    callback: CallbackQuery, state: FSMContext
) -> None:
    data = await state.get_data()
    client_id = data.get("next_client_id")
    if not client_id:
        await callback.answer()
        return
    choice = callback.data.split(":", 1)[1]
    next_contact = resolve_next_contact(choice)
    async with get_session() as session:
        client = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one()
        client.next_contact_at = next_contact
        await session.commit()
    await callback.message.answer("Дата следующего контакта обновлена")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("delete_client:"))
async def delete_client(callback: CallbackQuery) -> None:
    client_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        client = (
            await session.execute(select(Client).where(Client.id == client_id))
        ).scalar_one_or_none()
        if not client:
            await callback.message.answer("Клиент уже удален")
            await callback.answer()
            return
        await session.delete(client)
        await session.commit()
    await callback.message.answer("Клиент удален")
    await callback.answer()