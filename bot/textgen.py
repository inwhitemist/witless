from __future__ import annotations

import random
from random import choice
from typing import Optional

from .models import ChatSettings

_START = "___start___"
_END = "___end___"


def generate(samples: list[str], tries_count: int = 200, size: int = 0) -> Optional[str]:
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

    max_tokens = 100
    for _ in range(tries_count):
        result = [choice(start_frames)]
        for _ in range(max_tokens):
            frame = result[-1]
            nxt = choice(frame_map.get(frame, [_END]))
            if nxt == _END:
                break
            result.append(nxt)
        else:
            continue

        str_result = " ".join(result)

        if str_result in samples:
            continue

        n = len(result)
        if size == 0 and n <= 100:
            return str_result
        if size == 1 and 2 <= n <= 3:
            return str_result
        if size == 2 and 4 <= n <= 7:
            return str_result
        if size == 3 and 8 <= n <= 100:
            return str_result
        if size not in (0, 1, 2, 3):
            raise ValueError("Size must be 0, 1, 2 or 3")

    return None


def size_to_name(size: int) -> str:
    return {0: "any", 1: "small", 2: "medium", 3: "large"}.get(size, "any")


def parse_size_arg(arg: str | None) -> int:
    if not arg:
        return 0

    value = arg.strip().lower()
    if value in ("0", "any", "любое", "любой"):
        return 0
    if value in ("1", "small", "s", "мал", "корот", "короткое"):
        return 1
    if value in ("2", "medium", "m", "сред", "среднее"):
        return 2
    if value in ("3", "large", "l", "длин", "длинное"):
        return 3
    return 0


def is_allowed_text(text: str, settings: ChatSettings) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith("/"):
        return False
    if len(stripped) > settings.max_store_text_len:
        return False
    return True


def maybe_caps(text: str) -> str:
    if random.random() < 0.1:
        return text.upper()
    return text
