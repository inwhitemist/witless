import os
import json
import random
from random import choice
from dataclasses import dataclass, asdict

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, ChatMemberUpdated, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage


# ================== НАСТРОЙКИ БОТА ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

meeting = (
    "Здарова, че я здесь забыл?\n"
    "Ну раз пригласили, то не забудьте выдать мне админку, "
    "а то часть функций может не работать.\n\n"
    "Список команд доступен по команде /help\n"
)

BASE_DIR = "Dialogs"
DIALOGS_DIR = os.path.join(BASE_DIR, "dialogs")
SETTINGS_DIR = os.path.join(BASE_DIR, "settings")


# ================== ГЕНЕРАТОР ==================
_START = "___start___"
_END = "___end___"

def generate(samples: list[str], tries_count: int = 200, size: int = 0) -> str | None:
    if not samples:
        return None

    frames: list[str] = []
    start_frames: list[str] = []
    frame_map: dict[str, list[str]] = {}

    for sample in samples:
        words = sample.split()
        if not words:
            continue
        frames.append(_START)
        frames.extend(words)
        frames.append(_END)

    for i in range(len(frames) - 1):
        cur = frames[i]
        nxt = frames[i + 1]
        if cur == _END:
            continue
        frame_map.setdefault(cur, []).append(nxt)
        if cur == _START:
            start_frames.append(nxt)

    if not start_frames:
        return None

    for _ in range(tries_count):
        result = [choice(start_frames)]
        for frame in result:
            nxt = choice(frame_map.get(frame, [_END]))
            if nxt == _END:
                break
            result.append(nxt)

        str_result = " ".join(result)

        if str_result in samples:
            continue

        n = len(result)
        if size == 0:
            if n <= 100:
                return str_result
        elif size == 1:
            if 2 <= n <= 3:
                return str_result
        elif size == 2:
            if 4 <= n <= 7:
                return str_result
        elif size == 3:
            if 8 <= n <= 100:
                return str_result
        else:
            raise ValueError("Size must be 0, 1, 2 or 3")

    return None


# ================== НАСТРОЙКИ ЧАТА ==================
@dataclass
class ChatSettings:
    auto_reply_enabled: bool = True
    auto_reply_chance_n: int = 3      # 1 из N
    max_store_text_len: int = 80
    min_samples: int = 4
    default_gen_size: int = 0         # 0 any, 1 small, 2 medium, 3 large


def ensure_dirs() -> None:
    os.makedirs(DIALOGS_DIR, exist_ok=True)
    os.makedirs(SETTINGS_DIR, exist_ok=True)


def dialog_path(chat_id: int) -> str:
    return os.path.join(DIALOGS_DIR, f"{chat_id}.txt")


def settings_path(chat_id: int) -> str:
    return os.path.join(SETTINGS_DIR, f"{chat_id}.json")


def addtobd(chat_id: int) -> None:
    ensure_dirs()
    if not os.path.exists(dialog_path(chat_id)):
        with open(dialog_path(chat_id), "w", encoding="utf8") as f:
            f.write("")


def load_samples(chat_id: int) -> list[str]:
    path = dialog_path(chat_id)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf8") as f:
        lines = [ln.strip() for ln in f.readlines()]
    return [ln for ln in lines if ln]


def append_sample(chat_id: int, text: str) -> None:
    with open(dialog_path(chat_id), "a", encoding="utf8") as f:
        f.write(text.replace("\n", " ").strip() + "\n")


def clear_samples(chat_id: int) -> None:
    with open(dialog_path(chat_id), "w", encoding="utf8") as f:
        f.write("")


def load_settings(chat_id: int) -> ChatSettings:
    ensure_dirs()
    path = settings_path(chat_id)
    if not os.path.exists(path):
        s = ChatSettings()
        save_settings(chat_id, s)
        return s
    try:
        with open(path, "r", encoding="utf8") as f:
            data = json.load(f)
        return ChatSettings(**data)
    except Exception:
        # если файл битый — сбросим
        s = ChatSettings()
        save_settings(chat_id, s)
        return s


def save_settings(chat_id: int, settings: ChatSettings) -> None:
    ensure_dirs()
    with open(settings_path(chat_id), "w", encoding="utf8") as f:
        json.dump(asdict(settings), f, ensure_ascii=False, indent=2)


def size_to_name(size: int) -> str:
    return {0: "any", 1: "small", 2: "medium", 3: "large"}.get(size, "any")


def parse_size_arg(arg: str | None) -> int:
    if not arg:
        return 0
    a = arg.strip().lower()
    if a in ("0", "any", "любое", "любой"):
        return 0
    if a in ("1", "small", "s", "мал", "корот", "короткое"):
        return 1
    if a in ("2", "medium", "m", "сред", "среднее"):
        return 2
    if a in ("3", "large", "l", "длин", "длинное"):
        return 3
    return 0


def is_allowed_text(text: str, settings: ChatSettings) -> bool:
    if not text:
        return False
    t = text.strip()
    if not t:
        return False
    if t.startswith("/"):
        return False
    if len(t) > settings.max_store_text_len:
        return False
    return True


def maybe_caps(text: str) -> str:
    """Return text uppercased with 10% chance, otherwise unchanged."""
    if random.random() < 0.1:
        return text.upper()
    return text


async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ("administrator", "creator")


# ================== КНОПКИ/МЕНЮ ==================
def settings_kb(settings: ChatSettings) -> InlineKeyboardMarkup:
    enabled = "✅ Вкл" if settings.auto_reply_enabled else "❌ Выкл"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"Автоответы: {enabled}", callback_data="set:toggle_autoreply"),
        ],
        [
            InlineKeyboardButton(text=f"Шанс: 1 из {settings.auto_reply_chance_n}", callback_data="set:chance"),
            InlineKeyboardButton(text=f"Макс.длина: {settings.max_store_text_len}", callback_data="set:maxlen"),
        ],
        [
            InlineKeyboardButton(text=f"Мин.фраз: {settings.min_samples}", callback_data="set:minsamples"),
            InlineKeyboardButton(text=f"Размер по умолч.: {size_to_name(settings.default_gen_size)}", callback_data="set:defsize"),
        ],
        [
            InlineKeyboardButton(text="✨ Генерировать", callback_data="gen:menu"),
            InlineKeyboardButton(text="🧹 Очистить базу", callback_data="clear:confirm"),
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="set:refresh"),
            InlineKeyboardButton(text="✖ Закрыть", callback_data="set:close"),
        ]
    ])


def gen_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="any", callback_data="gen:0"),
            InlineKeyboardButton(text="small", callback_data="gen:1"),
            InlineKeyboardButton(text="medium", callback_data="gen:2"),
            InlineKeyboardButton(text="large", callback_data="gen:3"),
        ],
        [
            InlineKeyboardButton(text="⬅ Назад", callback_data="set:refresh"),
        ]
    ])


def clear_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, очистить", callback_data="clear:yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="set:refresh"),
        ]
    ])


# ================== FSM (ввод чисел) ==================
class SettingsForm(StatesGroup):
    waiting_chance = State()
    waiting_maxlen = State()
    waiting_minsamples = State()


router = Router()


# ================== СЛУЖЕБНЫЕ ХЕНДЛЕРЫ ==================
@router.my_chat_member()
async def on_my_chat_member(update: ChatMemberUpdated):
    if update.new_chat_member.user.is_bot is False:
        return
    if update.new_chat_member.status in ("member", "administrator", "creator"):
        chat_id = update.chat.id
        addtobd(chat_id)
        load_settings(chat_id)
        try:
            await update.bot.send_message(chat_id, meeting)
        except Exception:
            pass


@router.message(F.new_chat_members)
async def on_new_members(message: Message):
    if message.new_chat_members and any(u.is_bot and u.id == message.bot.id for u in message.new_chat_members):
        addtobd(message.chat.id)
        load_settings(message.chat.id)
        await message.answer(meeting)


# ================== КОМАНДЫ ==================
@router.message(Command("help"))
async def cmd_help(message: Message):
    addtobd(message.chat.id)
    await message.answer(
        "⚙ Команды:\n"
        "/gen [any|small|medium|large] — генерация\n"
        "/info — сколько фраз сохранено\n"
        "/clear — очистка базы (админ)\n"
        "/settings — меню настроек\n\n"
        "Можно управлять через кнопки в /settings."
    )

@router.message(F.text == "как")
async def cmd_help(message: Message):
    addtobd(message.chat.id)
    await message.answer("а как он так бистро пригае? он же с autobanihop пригае?")

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    addtobd(message.chat.id)
    s = load_settings(message.chat.id)
    await message.answer("⚙ Настройки чата:", reply_markup=settings_kb(s))


@router.message(Command("info"))
async def cmd_info(message: Message):
    """Show number of saved phrases and dialog file size."""
    addtobd(message.chat.id)
    samples = load_samples(message.chat.id)

    path = dialog_path(message.chat.id)
    try:
        size = os.path.getsize(path)
    except Exception:
        size = 0

    await message.answer(
        f"сохранил фраз: {len(samples)}\n"
        f"размер файла: {size} байт"
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message):
    addtobd(message.chat.id)

    if message.from_user is None:
        await message.answer("Не могу определить пользователя.")
        return

    # только админы могут запрашивать очистку
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("Вы не администратор беседы")
        return

    # попросим подтвердить действие, реальное удаление будет в cb_clear_yes
    await message.answer("Точно очистить базу этого чата?", reply_markup=clear_confirm_kb())


@router.message(Command("gen"))
async def cmd_gen(message: Message):
    addtobd(message.chat.id)
    s = load_settings(message.chat.id)

    arg = None
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2:
            arg = parts[1]

    size = parse_size_arg(arg) if arg else s.default_gen_size

    samples = load_samples(message.chat.id)
    if len(samples) < s.min_samples:
        await message.answer(f"Недостаточно фраз для генерации (минимум {s.min_samples})")
        return

    out = generate(samples, tries_count=300, size=size)
    await message.answer(maybe_caps((out or "че").lower()))


# ================== CALLBACK-МЕНЮ ==================
@router.callback_query(F.data == "set:refresh")
async def cb_refresh(call: CallbackQuery, state: FSMContext):
    await state.clear()
    s = load_settings(call.message.chat.id)
    await call.message.edit_text("⚙ Настройки чата:", reply_markup=settings_kb(s))
    await call.answer()


@router.callback_query(F.data == "set:close")
async def cb_close(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Настройки закрыты.")
    await call.answer()


@router.callback_query(F.data == "set:toggle_autoreply")
async def cb_toggle(call: CallbackQuery):
    chat_id = call.message.chat.id
    s = load_settings(chat_id)
    s.auto_reply_enabled = not s.auto_reply_enabled
    save_settings(chat_id, s)
    await call.message.edit_text("⚙ Настройки чата:", reply_markup=settings_kb(s))
    await call.answer("Ок")


@router.callback_query(F.data == "set:chance")
async def cb_set_chance(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.waiting_chance)
    await call.answer()
    await call.message.answer("Введи число N для шанса автоответа: будет отвечать 1 раз из N.\nПример: 3 (это 1/3). Допустимо 1..20")


@router.callback_query(F.data == "set:maxlen")
async def cb_set_maxlen(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.waiting_maxlen)
    await call.answer()
    await call.message.answer("Введи максимальную длину сохраняемого сообщения (символы). Допустимо 10..400")


@router.callback_query(F.data == "set:minsamples")
async def cb_set_minsamples(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.waiting_minsamples)
    await call.answer()
    await call.message.answer("Введи минимум фраз для генерации. Допустимо 2..200")


@router.callback_query(F.data == "set:defsize")
async def cb_defsize(call: CallbackQuery):
    await call.answer()
    await call.message.answer("Выбери размер генерации по умолчанию:", reply_markup=gen_kb())


@router.callback_query(F.data == "gen:menu")
async def cb_gen_menu(call: CallbackQuery):
    await call.answer()
    await call.message.answer("Выбери размер для генерации:", reply_markup=gen_kb())


@router.callback_query(F.data.startswith("gen:"))
async def cb_gen(call: CallbackQuery):
    chat_id = call.message.chat.id
    s = load_settings(chat_id)

    try:
        size = int(call.data.split(":")[1])
    except Exception:
        size = s.default_gen_size

    samples = load_samples(chat_id)
    if len(samples) < s.min_samples:
        await call.answer("Мало фраз", show_alert=True)
        return

    out = generate(samples, tries_count=300, size=size) or "че"
    await call.message.answer(maybe_caps(out.lower()))
    await call.answer("Готово")


@router.callback_query(F.data == "clear:confirm")
async def cb_clear_confirm(call: CallbackQuery):
    await call.answer()
    await call.message.answer("Точно очистить базу этого чата?", reply_markup=clear_confirm_kb())


@router.callback_query(F.data == "clear:yes")
async def cb_clear_yes(call: CallbackQuery):
    chat_id = call.message.chat.id

    if call.from_user is None:
        await call.answer("Не могу определить пользователя", show_alert=True)
        return

    if not await is_admin(call.bot, chat_id, call.from_user.id):
        await call.answer("Нужны права администратора", show_alert=True)
        return

    clear_samples(chat_id)
    await call.message.answer("База очищена ✅")
    await call.answer()


# ================== FSM: ПРИЁМ ЧИСЕЛ ==================
@router.message(SettingsForm.waiting_chance)
async def on_chance_input(message: Message, state: FSMContext):
    chat_id = message.chat.id
    try:
        n = int(message.text.strip())
    except Exception:
        await message.answer("Нужно число. Пример: 3")
        return

    if not (1 <= n <= 20):
        await message.answer("Диапазон 1..20")
        return

    s = load_settings(chat_id)
    s.auto_reply_chance_n = n
    save_settings(chat_id, s)
    await state.clear()
    await message.answer("Готово ✅")
    await message.answer("⚙ Настройки чата:", reply_markup=settings_kb(s))


@router.message(SettingsForm.waiting_maxlen)
async def on_maxlen_input(message: Message, state: FSMContext):
    chat_id = message.chat.id
    try:
        n = int(message.text.strip())
    except Exception:
        await message.answer("Нужно число. Пример: 80")
        return

    if not (10 <= n <= 400):
        await message.answer("Диапазон 10..400")
        return

    s = load_settings(chat_id)
    s.max_store_text_len = n
    save_settings(chat_id, s)
    await state.clear()
    await message.answer("Готово ✅")
    await message.answer("⚙ Настройки чата:", reply_markup=settings_kb(s))


@router.message(SettingsForm.waiting_minsamples)
async def on_minsamples_input(message: Message, state: FSMContext):
    chat_id = message.chat.id
    try:
        n = int(message.text.strip())
    except Exception:
        await message.answer("Нужно число. Пример: 4")
        return

    if not (2 <= n <= 200):
        await message.answer("Диапазон 2..200")
        return

    s = load_settings(chat_id)
    s.min_samples = n
    save_settings(chat_id, s)
    await state.clear()
    await message.answer("Готово ✅")
    await message.answer("⚙ Настройки чата:", reply_markup=settings_kb(s))


# ================== АВТОСБОР ТЕКСТА + АВТООТВЕТ ==================
@router.message()
async def on_message(message: Message):
    addtobd(message.chat.id)
    s = load_settings(message.chat.id)

    if message.text is None:
        return
    if message.from_user is None:
        return

    if not is_allowed_text(message.text, s):
        return

    append_sample(message.chat.id, message.text)
    samples = load_samples(message.chat.id)

    if not s.auto_reply_enabled:
        return

    # шанс 1 из N
    if len(samples) >= s.min_samples and random.randint(1, s.auto_reply_chance_n) == 1:
        out = generate(samples, tries_count=200, size=s.default_gen_size)
        if out:
            await message.answer(maybe_caps(out.lower()))


# ================== ЗАПУСК ==================
async def main():
    ensure_dirs()
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())