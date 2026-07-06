import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Role():
    """An agent's soul: a markdown role prompt (from <home>/.manylogue/roles/*.md)
    appended to the base system prompt. Empty role = vanilla agent."""

    role_prompt: str

    def __init__(self, prompt: str = "") -> None:
        self.role_prompt = prompt

    @staticmethod
    def load(workspace_root: Path, role_ref: str) -> "Role":
        """Load a role prompt from <home>/.manylogue/<role_ref> (e.g. 'roles/foo.md').

        A missing file resolves to an empty role rather than raising, so a bad
        ref in an agent definition never crashes adding a participant.
        """
        role_file = workspace_root / ".manylogue" / role_ref
        if not role_file.is_file():
            logger.warning(
                "role file not found: %s — using empty role", role_file)
            return Role("")
        return Role(role_file.read_text(encoding="utf-8"))
