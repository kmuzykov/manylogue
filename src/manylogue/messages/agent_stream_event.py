from enum import Enum
from pydantic import BaseModel, ConfigDict

from manylogue.messages.adapter_response import AdapterIntermediateResponse


class AgentResponseStreamEventType(str, Enum):
    # the agent began engaging the model — fired before any output, so the UI can
    # show "thinking" during the gap before the first chunk arrives
    agent_turn_start = "agent_turn_start"

    # each individual intermediate agent response stream event
    agent_stream_event = "agent_stream_event"

    # a signal that stream events are over and message with full list is coming
    # so the events need to be removed
    agent_stream_end = "agent_stream_end"


class AgentTurnOutcome(str, Enum):
    # the agent produced a reply (now committed as a message)
    answered = "answered"

    # the agent engaged the model but chose to stay silent (<skip>)
    skipped = "skipped"

    # the agent's adapter call failed or the turn crashed
    errored = "errored"

    # the agent never engaged the model (nothing new / not addressed)
    idle = "idle"


class AgentStreamEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: AgentResponseStreamEventType
    author: str

    # intermediate response payload; set only for agent_stream_event
    response: AdapterIntermediateResponse | None = None

    # how the turn ended; set only for agent_stream_end
    outcome: AgentTurnOutcome | None = None
