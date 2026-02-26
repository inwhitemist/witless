from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import AppConfig
from .handlers import build_router
from .storage import ChatStorage


async def run_bot(config: AppConfig | None = None) -> None:
    app_config = config or AppConfig.from_env()
    if not app_config.token:
        raise RuntimeError("TELEGRAM_TOKEN is not set")

    storage = ChatStorage(
        dialogs_dir=app_config.dialogs_dir,
        settings_dir=app_config.settings_dir,
    )

    bot = Bot(token=app_config.token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(build_router(storage))

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)
