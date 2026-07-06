# pyright: reportUnknownVariableType=false
"""Markdown rendering shim.

Wraps markdown-it-py + Pygments. Pygments has no type stubs, so the
file-level pyright suppression is scoped here — keeps app.py clean.
"""

from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter


def _highlight_code(code: str, name: str, attrs: str) -> str:
    try:
        lexer = get_lexer_by_name(name) if name else guess_lexer(code)
    except Exception:
        return ""  # let markdown-it use the default <pre><code>
    return highlight(code, lexer, HtmlFormatter(nowrap=True))


_md = (
    MarkdownIt("gfm-like2", {
        "breaks": True,
        "html": False,
        "highlight": _highlight_code,
    })
    .use(footnote_plugin)
)


def render_markdown(text: str) -> str:
    return _md.render(text)
