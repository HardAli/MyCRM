from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import AsyncEngine

from config import TELEGRAM_BOT_TOKEN
from db import Base, engine
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_bot() -> Bot:
    # В aiogram 3.7+ parse_mode нужно передавать через DefaultBotProperties
    return Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def on_startup(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")


async def set_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="add_client", description="Добавить клиента"),
        BotCommand(command="add_company", description="Добавить компанию"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    bot = setup_bot()
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(router)

    await on_startup(engine)
    await set_commands(bot)

    logger.info("Starting bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
