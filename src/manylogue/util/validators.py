import re

_CHAT_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_chat_name_valid(chat_name: str) -> bool:
    return _CHAT_NAME_RE.fullmatch(chat_name) is not None
