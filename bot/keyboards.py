from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .models import ChatSettings
from .textgen import size_to_name


def settings_kb(settings: ChatSettings) -> InlineKeyboardMarkup:
    enabled = "✅ Вкл" if settings.auto_reply_enabled else "❌ Выкл"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Автоответы: {enabled}",
                    callback_data="set:toggle_autoreply",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"Шанс: 1 из {settings.auto_reply_chance_n}",
                    callback_data="set:chance",
                ),
                InlineKeyboardButton(
                    text=f"Макс.длина: {settings.max_store_text_len}",
                    callback_data="set:maxlen",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"Мин.фраз: {settings.min_samples}",
                    callback_data="set:minsamples",
                ),
                InlineKeyboardButton(
                    text=f"Размер по умолч.: {size_to_name(settings.default_gen_size)}",
                    callback_data="set:defsize",
                ),
            ],
            [
                InlineKeyboardButton(text="✨ Генерировать", callback_data="gen:menu"),
                InlineKeyboardButton(text="🧹 Очистить базу", callback_data="clear:confirm"),
            ],
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="set:refresh"),
                InlineKeyboardButton(text="✖ Закрыть", callback_data="set:close"),
            ],
        ]
    )


def gen_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="any", callback_data="gen:0"),
                InlineKeyboardButton(text="small", callback_data="gen:1"),
                InlineKeyboardButton(text="medium", callback_data="gen:2"),
                InlineKeyboardButton(text="large", callback_data="gen:3"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="set:refresh"),
            ],
        ]
    )


def clear_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, очистить", callback_data="clear:yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="set:refresh"),
            ]
        ]
    )
