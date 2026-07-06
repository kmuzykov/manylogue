from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from manylogue.chat.chat_mode import ChatMode
from manylogue.config.constants import ENCODING

META_FILENAME = "meta.json"


class ChatMetaModel(BaseModel):
    # Frozen like the rest of the data layer; changes (rename, mode, last-activity)
    # go through model_copy + re-save, never in-place mutation.
    model_config = ConfigDict(frozen=True)
    schema_version: int = Field(default=2)
    id: str
    name: str
    mode: ChatMode = Field(default=ChatMode.round_robin)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    # The default project directory passed as cwd for agents (overridable when adding an agent).
    # Defaults to the process working directory so no machine-specific path ships; new chats
    # always set this explicitly from the create form, so the default only backstops loaded data.
    default_project_dir: Path = Field(default_factory=Path.cwd)
    # NOTE: participants used to live here; they now have their own participants.json
    # (see ChatParticipantsStorage). Old meta.json files may still carry a `participants`
    # key — pydantic ignores extra keys, so they load fine.


class ChatMetaStorage:
    """Reads/writes a chat's meta.json (id, display name, mode) inside its dir."""

    _path: Path

    def __init__(self, chat_dir: Path) -> None:
        self._path = chat_dir / META_FILENAME

    def exists(self) -> bool:
        return self._path.exists()

    def load(self) -> ChatMetaModel:
        return ChatMetaModel.model_validate_json(self._path.read_text(encoding=ENCODING))

    def save(self, meta: ChatMetaModel) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        with tmp_path.open("w", encoding=ENCODING) as f:
            f.write(meta.model_dump_json(indent=2))
        tmp_path.replace(self._path)
