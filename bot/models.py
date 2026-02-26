from dataclasses import dataclass


@dataclass
class ChatSettings:
    auto_reply_enabled: bool = True
    auto_reply_chance_n: int = 3
    max_store_text_len: int = 80
    min_samples: int = 4
    default_gen_size: int = 0
