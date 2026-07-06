from pathlib import Path
import logging
from collections.abc import Sequence
from pydantic import BaseModel, Field

from manylogue.agents.agent_participant import PersistedParticipant
from manylogue.config.constants import ENCODING

PARTICIPANTS_FILENAME = "participants.json"

logger = logging.getLogger(__name__)


class ChatParticipantsModel(BaseModel):
    schema_version: int = Field(default=1)
    participants: list[PersistedParticipant] = Field(
        default_factory=list[PersistedParticipant])


class ChatParticipantsStorage:
    """Per-chat roster, stored as participants.json inside the chat's dir.

    Each record carries a seat's membership (def_name, resolved name, cwd) AND its agent
    state (cursor + adapter session). Replaces the old agent_state.json: one source of
    truth per participant, so the agent name is no longer a join key across two files.
    """

    _path: Path

    def __init__(self, chat_dir: Path) -> None:
        self._path = chat_dir / PARTICIPANTS_FILENAME

    def load(self) -> tuple[PersistedParticipant, ...]:
        if not self._path.exists():
            logger.error(
                "Trying to load participants file, but the path doesn't exist: %s", self._path)
            return ()
        model = ChatParticipantsModel.model_validate_json(
            self._path.read_text(encoding=ENCODING))
        return tuple(model.participants)

    def save(self, participants: Sequence[PersistedParticipant]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        model = ChatParticipantsModel(participants=list(participants))
        tmp_path = self._path.with_suffix(".tmp")
        with tmp_path.open("w", encoding=ENCODING) as f:
            f.write(model.model_dump_json(indent=2))
        tmp_path.replace(self._path)
