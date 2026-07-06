from enum import Enum

from pydantic import BaseModel, ConfigDict


class AdapterIntermediateResponseType(str, Enum):
    narration = "narration"
    tool = "tool"


class AdapterIntermediateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: AdapterIntermediateResponseType
    body: str


class AdapterFinalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    body: str
