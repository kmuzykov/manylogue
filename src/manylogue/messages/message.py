from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from manylogue.messages.adapter_response import AdapterIntermediateResponse


class MessageKind(str, Enum):
    message = "message"
    error = "error"


class MessageMeta(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: int = Field(default=1)


class MessageDraft(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: MessageKind = Field(default=MessageKind.message)
    author: str
    body: str
    thread: tuple[AdapterIntermediateResponse, ...] = Field(default_factory=tuple)


class Message(MessageDraft):
    id: str
    ts: datetime = Field(default_factory=datetime.now)
    meta: MessageMeta
