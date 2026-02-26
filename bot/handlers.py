from __future__ import annotations

import random

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from .config import HELP_MESSAGE, MEETING_MESSAGE
from .keyboards import clear_confirm_kb, gen_kb, settings_kb
from .services import callback_chat_id, is_admin
from .states import SettingsForm
from .storage import ChatStorage
from .textgen import generate, is_allowed_text, maybe_caps, parse_size_arg


def build_router(storage: ChatStorage) -> Router:
    router = Router()

    @router.my_chat_member()
    async def on_my_chat_member(update: ChatMemberUpdated):
        if not update.new_chat_member.user.is_bot:
            return
        if update.new_chat_member.user.id != update.bot.id:
            return
        if update.new_chat_member.status in ("member", "administrator", "creator"):
            chat_id = update.chat.id
            storage.ensure_chat(chat_id)
            storage.load_settings(chat_id)
            try:
                await update.bot.send_message(chat_id, MEETING_MESSAGE)
            except Exception:
                pass

    @router.message(F.new_chat_members)
    async def on_new_members(message: Message):
        if message.new_chat_members and any(
            user.is_bot and user.id == message.bot.id for user in message.new_chat_members
        ):
            chat_id = message.chat.id
            storage.ensure_chat(chat_id)
            storage.load_settings(chat_id)
            await message.answer(MEETING_MESSAGE)

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        storage.ensure_chat(message.chat.id)
        await message.answer(HELP_MESSAGE)

    @router.message(F.text == "как")
    async def msg_kak(message: Message):
        storage.ensure_chat(message.chat.id)
        await message.answer("а как он так бистро пригае? он же с autobanihop пригае?")

    @router.message(Command("settings"))
    async def cmd_settings(message: Message):
        storage.ensure_chat(message.chat.id)
        settings = storage.load_settings(message.chat.id)
        await message.answer("⚙ Настройки чата:", reply_markup=settings_kb(settings))

    @router.message(Command("info"))
    async def cmd_info(message: Message):
        storage.ensure_chat(message.chat.id)
        samples = storage.load_samples(message.chat.id)

        try:
            size = storage.dialog_path(message.chat.id).stat().st_size
        except Exception:
            size = 0

        await message.answer(f"сохранил фраз: {len(samples)}\nразмер файла: {size} байт")

    @router.message(Command("clear"))
    async def cmd_clear(message: Message):
        storage.ensure_chat(message.chat.id)
        if message.from_user is None:
            await message.answer("Не могу определить пользователя.")
            return

        if not await is_admin(message.bot, message.chat.id, message.from_user.id):
            await message.answer("Вы не администратор беседы")
            return

        await message.answer("Точно очистить базу этого чата?", reply_markup=clear_confirm_kb())

    @router.message(Command("gen"))
    async def cmd_gen(message: Message):
        storage.ensure_chat(message.chat.id)
        settings = storage.load_settings(message.chat.id)

        arg = None
        if message.text:
            parts = message.text.split(maxsplit=1)
            if len(parts) == 2:
                arg = parts[1]

        size = parse_size_arg(arg) if arg else settings.default_gen_size
        samples = storage.load_samples(message.chat.id)
        if len(samples) < settings.min_samples:
            await message.answer(f"Недостаточно фраз для генерации (минимум {settings.min_samples})")
            return

        out = generate(samples, tries_count=300, size=size)
        await message.answer(maybe_caps((out or "че").lower()))

    @router.callback_query(F.data == "set:refresh")
    async def cb_refresh(call: CallbackQuery, state: FSMContext):
        chat_id = callback_chat_id(call)
        if chat_id is None or call.message is None:
            await call.answer()
            return
        await state.clear()
        settings = storage.load_settings(chat_id)
        await call.message.edit_text("⚙ Настройки чата:", reply_markup=settings_kb(settings))
        await call.answer()

    @router.callback_query(F.data == "set:close")
    async def cb_close(call: CallbackQuery, state: FSMContext):
        if call.message is None:
            await call.answer()
            return
        await state.clear()
        await call.message.edit_text("Настройки закрыты.")
        await call.answer()

    @router.callback_query(F.data == "set:toggle_autoreply")
    async def cb_toggle(call: CallbackQuery):
        chat_id = callback_chat_id(call)
        if chat_id is None or call.message is None:
            await call.answer()
            return
        settings = storage.load_settings(chat_id)
        settings.auto_reply_enabled = not settings.auto_reply_enabled
        storage.save_settings(chat_id, settings)
        await call.message.edit_text("⚙ Настройки чата:", reply_markup=settings_kb(settings))
        await call.answer("Ок")

    @router.callback_query(F.data == "set:chance")
    async def cb_set_chance(call: CallbackQuery, state: FSMContext):
        if call.message is None:
            await call.answer()
            return
        await state.set_state(SettingsForm.waiting_chance)
        await call.answer()
        await call.message.answer(
            "Введи число N для шанса автоответа: будет отвечать 1 раз из N.\n"
            "Пример: 3 (это 1/3). Допустимо 1..20"
        )

    @router.callback_query(F.data == "set:maxlen")
    async def cb_set_maxlen(call: CallbackQuery, state: FSMContext):
        if call.message is None:
            await call.answer()
            return
        await state.set_state(SettingsForm.waiting_maxlen)
        await call.answer()
        await call.message.answer(
            "Введи максимальную длину сохраняемого сообщения (символы). Допустимо 10..400"
        )

    @router.callback_query(F.data == "set:minsamples")
    async def cb_set_minsamples(call: CallbackQuery, state: FSMContext):
        if call.message is None:
            await call.answer()
            return
        await state.set_state(SettingsForm.waiting_minsamples)
        await call.answer()
        await call.message.answer("Введи минимум фраз для генерации. Допустимо 2..200")

    @router.callback_query(F.data == "set:defsize")
    async def cb_defsize(call: CallbackQuery):
        if call.message is None:
            await call.answer()
            return
        await call.answer()
        await call.message.answer("Выбери размер генерации по умолчанию:", reply_markup=gen_kb())

    @router.callback_query(F.data == "gen:menu")
    async def cb_gen_menu(call: CallbackQuery):
        if call.message is None:
            await call.answer()
            return
        await call.answer()
        await call.message.answer("Выбери размер для генерации:", reply_markup=gen_kb())

    @router.callback_query(F.data.startswith("gen:"))
    async def cb_gen(call: CallbackQuery):
        chat_id = callback_chat_id(call)
        if chat_id is None or call.message is None:
            await call.answer()
            return

        settings = storage.load_settings(chat_id)
        try:
            size = int(call.data.split(":")[1])
        except Exception:
            size = settings.default_gen_size

        samples = storage.load_samples(chat_id)
        if len(samples) < settings.min_samples:
            await call.answer("Мало фраз", show_alert=True)
            return

        out = generate(samples, tries_count=300, size=size) or "че"
        await call.message.answer(maybe_caps(out.lower()))
        await call.answer("Готово")

    @router.callback_query(F.data == "clear:confirm")
    async def cb_clear_confirm(call: CallbackQuery):
        if call.message is None:
            await call.answer()
            return
        await call.answer()
        await call.message.answer("Точно очистить базу этого чата?", reply_markup=clear_confirm_kb())

    @router.callback_query(F.data == "clear:yes")
    async def cb_clear_yes(call: CallbackQuery):
        chat_id = callback_chat_id(call)
        if chat_id is None or call.message is None:
            await call.answer()
            return
        if call.from_user is None:
            await call.answer("Не могу определить пользователя", show_alert=True)
            return
        if not await is_admin(call.bot, chat_id, call.from_user.id):
            await call.answer("Нужны права администратора", show_alert=True)
            return

        storage.clear_samples(chat_id)
        await call.message.answer("База очищена ✅")
        await call.answer()

    @router.message(SettingsForm.waiting_chance)
    async def on_chance_input(message: Message, state: FSMContext):
        chat_id = message.chat.id
        try:
            value = int(message.text.strip())
        except Exception:
            await message.answer("Нужно число. Пример: 3")
            return

        if not 1 <= value <= 20:
            await message.answer("Диапазон 1..20")
            return

        settings = storage.load_settings(chat_id)
        settings.auto_reply_chance_n = value
        storage.save_settings(chat_id, settings)
        await state.clear()
        await message.answer("Готово ✅")
        await message.answer("⚙ Настройки чата:", reply_markup=settings_kb(settings))

    @router.message(SettingsForm.waiting_maxlen)
    async def on_maxlen_input(message: Message, state: FSMContext):
        chat_id = message.chat.id
        try:
            value = int(message.text.strip())
        except Exception:
            await message.answer("Нужно число. Пример: 80")
            return

        if not 10 <= value <= 400:
            await message.answer("Диапазон 10..400")
            return

        settings = storage.load_settings(chat_id)
        settings.max_store_text_len = value
        storage.save_settings(chat_id, settings)
        await state.clear()
        await message.answer("Готово ✅")
        await message.answer("⚙ Настройки чата:", reply_markup=settings_kb(settings))

    @router.message(SettingsForm.waiting_minsamples)
    async def on_minsamples_input(message: Message, state: FSMContext):
        chat_id = message.chat.id
        try:
            value = int(message.text.strip())
        except Exception:
            await message.answer("Нужно число. Пример: 4")
            return

        if not 2 <= value <= 200:
            await message.answer("Диапазон 2..200")
            return

        settings = storage.load_settings(chat_id)
        settings.min_samples = value
        storage.save_settings(chat_id, settings)
        await state.clear()
        await message.answer("Готово ✅")
        await message.answer("⚙ Настройки чата:", reply_markup=settings_kb(settings))

    @router.message()
    async def on_message(message: Message):
        chat_id = message.chat.id
        storage.ensure_chat(chat_id)
        settings = storage.load_settings(chat_id)

        if message.text is None or message.from_user is None:
            return
        if not is_allowed_text(message.text, settings):
            return

        storage.append_sample(chat_id, message.text)
        if not settings.auto_reply_enabled:
            return
        if random.randint(1, settings.auto_reply_chance_n) != 1:
            return

        samples = storage.load_samples(chat_id)
        if len(samples) < settings.min_samples:
            return

        out = generate(samples, tries_count=200, size=settings.default_gen_size)
        if out:
            await message.answer(maybe_caps(out.lower()))

    return router
