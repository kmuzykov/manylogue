from datetime import datetime
from pathlib import Path

from manylogue.config.constants import ENCODING
from manylogue.messages.message import Message, MessageDraft, MessageMeta, MessageKind

MESSAGES_FILENAME = "messages.jsonl"


class MessagesStorage:
    _chat_id: str
    _dir: Path
    _messages: list[Message]
    _id_index: dict[str, int]

    def __init__(self, chat_dir: Path, chat_id: str) -> None:
        self._chat_id = chat_id
        self._dir = chat_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._messages = []
        self._id_index = {}

    def add_message(self, draft: MessageDraft) -> Message:
        new_id = f"{self._chat_id}-{len(self._messages)}"
        msg = Message(id=new_id, ts=datetime.now(), meta=MessageMeta(),
                      **draft.model_dump())
        self._messages.append(msg)
        self._id_index[new_id] = len(self._messages) - 1
        self._append_one(msg)
        return msg

    def messages_after(self, cursor_id: str | None, *, include_invisible: bool = False) -> tuple[Message, ...]:
        if cursor_id is None:
            tail = self._messages
        else:
            idx = self._id_index.get(cursor_id)
            # unknown cursor -> replay all (safe)
            tail = self._messages if idx is None else self._messages[idx + 1:]

        if include_invisible:
            return tuple(tail)
        return tuple(m for m in tail if self._is_visible_to_models(m))

    def get_messages(self, *, include_invisible: bool = False) -> tuple[Message, ...]:

        if include_invisible:
            return tuple(self._messages)

        return tuple(m for m in self._messages if self._is_visible_to_models(m))

    def load(self) -> None:
        path = self._file_path()
        if not path.exists():
            # todo: log error
            return
        with path.open("r", encoding=ENCODING) as f:
            for line in f:
                if line.strip():
                    msg = Message.model_validate_json(line)
                    self._messages.append(msg)
                    self._id_index[msg.id] = len(self._messages) - 1

    def _append_one(self, msg: Message) -> None:
        with open(self._file_path(), "a", encoding=ENCODING) as f:
            f.write(msg.model_dump_json())
            f.write("\n")

    def _file_path(self) -> Path:
        return self._dir / MESSAGES_FILENAME

    @staticmethod
    def _is_visible_to_models(msg: Message) -> bool:
        return msg.kind == MessageKind.message
