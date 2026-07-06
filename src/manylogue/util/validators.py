import re
from pathlib import Path

_CHAT_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_chat_name_valid(chat_name: str) -> bool:
    return _CHAT_NAME_RE.fullmatch(chat_name) is not None


def resolve_existing_dir(raw: str | None) -> Path | None:
    """User-supplied directory input -> absolute Path, or None if it doesn't name one.

    Expands ~ and resolves relative segments before checking, so "~/project" works,
    and what callers store is an absolute path that survives a server restart from a
    different cwd. Empty input must be caught before Path() sees it — Path("") is "."
    and would validate as the server's own cwd.
    """
    if raw is None or not raw.strip():
        return None
    path = Path(raw.strip()).expanduser().resolve()
    return path if path.is_dir() else None
