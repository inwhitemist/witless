from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import ChatSettings


class ChatStorage:
    def __init__(self, dialogs_dir: Path, settings_dir: Path):
        self.dialogs_dir = dialogs_dir
        self.settings_dir = settings_dir
        self.ensure_dirs()

    def ensure_dirs(self) -> None:
        self.dialogs_dir.mkdir(parents=True, exist_ok=True)
        self.settings_dir.mkdir(parents=True, exist_ok=True)

    def dialog_path(self, chat_id: int) -> Path:
        return self.dialogs_dir / f"{chat_id}.txt"

    def settings_path(self, chat_id: int) -> Path:
        return self.settings_dir / f"{chat_id}.json"

    def ensure_chat(self, chat_id: int) -> None:
        self.ensure_dirs()
        path = self.dialog_path(chat_id)
        if not path.exists():
            path.write_text("", encoding="utf8")

    def load_samples(self, chat_id: int) -> list[str]:
        self.ensure_dirs()
        path = self.dialog_path(chat_id)
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf8").splitlines()
        except Exception:
            return []
        return [line.strip() for line in lines if line.strip()]

    def append_sample(self, chat_id: int, text: str) -> None:
        self.ensure_dirs()
        normalized = text.replace("\n", " ").strip()
        with self.dialog_path(chat_id).open("a", encoding="utf8") as file:
            file.write(normalized + "\n")

    def clear_samples(self, chat_id: int) -> None:
        self.ensure_dirs()
        self.dialog_path(chat_id).write_text("", encoding="utf8")

    def load_settings(self, chat_id: int) -> ChatSettings:
        self.ensure_dirs()
        path = self.settings_path(chat_id)
        if not path.exists():
            settings = ChatSettings()
            self.save_settings(chat_id, settings)
            return settings
        try:
            data = json.loads(path.read_text(encoding="utf8"))
            return ChatSettings(**data)
        except Exception:
            settings = ChatSettings()
            self.save_settings(chat_id, settings)
            return settings

    def save_settings(self, chat_id: int, settings: ChatSettings) -> None:
        self.ensure_dirs()
        payload = json.dumps(asdict(settings), ensure_ascii=False, indent=2)
        self.settings_path(chat_id).write_text(payload, encoding="utf8")
