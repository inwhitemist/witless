from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


MEETING_MESSAGE = (
    "Здарова, че я здесь забыл?\n"
    "Ну раз пригласили, то не забудьте выдать мне админку, "
    "а то часть функций может не работать.\n\n"
    "Список команд доступен по команде /help\n"
)

HELP_MESSAGE = (
    "⚙ Команды:\n"
    "/gen [any|small|medium|large] — генерация\n"
    "/info — сколько фраз сохранено\n"
    "/clear — очистка базы (админ)\n"
    "/settings — меню настроек\n\n"
    "Можно управлять через кнопки в /settings."
)

KAK_MESSAGE = "а как он так бистро пригае? он же с autobanihop пригае?"


@dataclass(frozen=True)
class AppConfig:
    token: str
    dialogs_dir: Path
    settings_dir: Path

    @classmethod
    def from_env(cls) -> "AppConfig":
        root_dir = Path(__file__).resolve().parent.parent
        base_dir = root_dir / "Dialogs"
        return cls(
            token=os.getenv("TELEGRAM_TOKEN", ""),
            dialogs_dir=base_dir / "dialogs",
            settings_dir=base_dir / "settings",
        )
