"""Jinja template setup + HTML fragment rendering.

Owns the template environment and the small presentation filters, so app.py
stays routes-only — the same role markdown_render.py plays for message bodies.
"""

from importlib.resources import files

from fastapi.templating import Jinja2Templates

# HUMAN_NAME comes from the config leaf, NOT from manylogue.chat — chat_room imports
# this package (util), so reaching back into chat here would close an import cycle.
from manylogue.config.constants import HUMAN_NAME
from manylogue.messages import Message
from manylogue.util.markdown_render import render_markdown

# Keep in sync with AVATAR_HUES in chat.html.
_AVATAR_HUES = 6

# Resolved by package name, not by this file's location — same mechanism config.py uses
# for the packaged defaults, so it works from a checkout and an installed wheel alike.
templates = Jinja2Templates(directory=str(files("manylogue") / "templates"))
templates.env.filters["markdown"] = render_markdown


def _avatar_class(name: str) -> str:
    # Stable per-author identity color (Human is neutral). Mirrored in chat.html JS.
    if name == HUMAN_NAME:
        return "av-human"
    return f"av-{sum(ord(c) for c in name) % _AVATAR_HUES}"


def _avatar_initial(name: str) -> str:
    return (name[:2] or "?").upper()


templates.env.filters["avatar_class"] = _avatar_class
templates.env.filters["avatar_initial"] = _avatar_initial


def render_message_fragment(message: Message) -> str:
    """One committed message rendered as the shared _message.html fragment —
    used by the SSE stream; full-page loads render the same fragment via chat.html."""
    return templates.env.get_template("_message.html").render(msg=message)
