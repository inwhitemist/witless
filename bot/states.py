from aiogram.fsm.state import State, StatesGroup


class SettingsForm(StatesGroup):
    waiting_chance = State()
    waiting_maxlen = State()
    waiting_minsamples = State()
