from __future__ import annotations

from typing import Optional

from aiogram import Bot
from aiogram.types import CallbackQuery


async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception:
        return False
    return member.status in ("administrator", "creator")


def callback_chat_id(call: CallbackQuery) -> Optional[int]:
    if call.message is None:
        return None
    return call.message.chat.id
