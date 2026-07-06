import re
from uuid import uuid4

_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SLUG_MAX_LEN = 24


def slugify(text: str) -> str:
    """Lowercase, hyphenated, ascii-only slug. Cosmetic only — never parsed back."""
    slug = _NON_SLUG_RE.sub("-", text.lower()).strip("-")[:_SLUG_MAX_LEN].strip("-")
    return slug or "chat"


def make_chat_id(name: str) -> str:
    """Stable, opaque chat id: a cosmetic slug of the name plus a short uuid.

    The slug is frozen at creation; identity is the whole string, never the slug.
    """
    return f"{slugify(name)}-{uuid4().hex[:8]}"


def pick_unique_name(base: str, taken: set[str]) -> str:
    """Pick a roster-unique seat name: `base`, else `base_2`, `base_3`, ... .

    Runs only when a participant is added (the room knows the current roster), so duplicates
    of the same definition are allowed and become `Name_2` etc. The resolved name is then
    persisted and reused verbatim on load — never re-derived, which could shift names and
    orphan per-agent state. Pass `"Human"` plus the current seat names as `taken`.
    """
    if base not in taken:
        return base
    suffix = 2
    while f"{base}_{suffix}" in taken:
        suffix += 1
    return f"{base}_{suffix}"
