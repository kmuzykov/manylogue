"""Home resolution, first-run config seeding, and cross-cutting constants.

The Manylogue home holds the user's ``.manylogue`` config (agents, roles) and runtime storage.
By default it's the user's home dir (``~/.manylogue``) — always user-writable, unlike an
installed package dir. Set ``MANYLOGUE_HOME`` (env or ``.env``) to point elsewhere, e.g. a
repo checkout during development.

Shipped defaults live in ``manylogue/defaults/`` as package data and are copied into
``<home>/.manylogue`` on first run. ``importlib.resources`` resolves that package data
identically whether Manylogue runs from a source checkout or an installed wheel, so the same
seeding path serves both ``git clone`` and ``pip install``.

This package imports nothing from the rest of manylogue (a leaf), so any module may
import from it without creating a cycle.
"""

import logging
import os
import shutil
from functools import cache
from importlib.resources import as_file, files
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from manylogue.config.constants import ENCODING, HUMAN_NAME

__all__ = ["ENCODING", "HUMAN_NAME", "ensure_home_seeded", "home", "load_env"]

logger = logging.getLogger(__name__)

ENV_FILENAME = ".env"


def _resolve_home() -> Path:
    """MANYLOGUE_HOME from the process env, else from the launch-dir ``.env``, else ``~``."""
    env = os.environ.get("MANYLOGUE_HOME")
    if env:
        return Path(env)
    cwd_home = dotenv_values(ENV_FILENAME).get("MANYLOGUE_HOME")
    if cwd_home:
        return Path(cwd_home)
    return Path.home()


def load_env() -> None:
    """Layered ``.env`` loading. Call once at startup, before reading any config vars.

    Precedence (first setter wins — every load uses ``override=False``, so real process
    env vars are never clobbered):

    1. the process environment
    2. ``<home>/.manylogue/.env`` — user config, the place for secrets
    3. ``./.env`` in the launch directory — dev fallback, may set ``MANYLOGUE_HOME``

    ``MANYLOGUE_HOME`` itself belongs in the process env or the launch-dir ``.env``;
    setting it inside ``<home>/.manylogue/.env`` would be self-referential and is ignored
    for home resolution.
    """
    load_dotenv(_resolve_home() / ".manylogue" / ENV_FILENAME, override=False)
    load_dotenv(ENV_FILENAME, override=False)


@cache
def home() -> Path:
    """The Manylogue home dir — resolved and seeded once on first call, then cached.

    The single init-once entry point: a cached module function is Python's idiom for a
    process-wide singleton, so everything that needs the home dir just calls
    ``config.home()`` without worrying about ordering or repeat seeding.
    """
    return ensure_home_seeded()


def ensure_home_seeded(home_dir: Path | None = None) -> Path:
    """Copy packaged default agents/roles into ``<home>/.manylogue`` and return the home dir.

    ``home_dir`` defaults to ``MANYLOGUE_HOME`` (env) else the user's home dir. Idempotent and
    non-destructive: only files that don't already exist are written, so user edits and the
    runtime ``storage/`` tree are never touched (``storage/`` isn't shipped, so it's never
    seeded). A write failure degrades to a logged error rather than crashing startup.
    """
    if home_dir is None:
        home_dir = _resolve_home()
    dest_root = home_dir / ".manylogue"
    try:
        with as_file(files("manylogue") / "defaults") as defaults_dir:
            if not defaults_dir.is_dir():
                logger.warning("no packaged defaults found at %s", defaults_dir)
                return home_dir
            for src in sorted(defaults_dir.rglob("*")):
                if not src.is_file():
                    continue
                dest = dest_root / src.relative_to(defaults_dir)
                if dest.exists():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                logger.info("seeded default config: %s", dest)
    except OSError:
        logger.exception("could not seed default config into %s", dest_root)
    return home_dir
