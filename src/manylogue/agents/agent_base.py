from abc import ABC, abstractmethod
from collections.abc import Callable

from manylogue.agents.agent_participant import PersistedParticipant
from manylogue.agents.turn_result import TurnResult
from manylogue.messages import MessagesStorage
from manylogue.messages.adapter_response import AdapterIntermediateResponse


class AgentBase(ABC):
    """The protocol ChatRoom + the worker loop need from a seat in the roster.

    Implemented by Agent (a live brain) and MissingAgent (a null-object placeholder for
    an unresolved definition). The roster is a single `list[AgentBase]`: no optional
    agent, no second collection, one uniform turn/persist path.
    """

    agent_name: str

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name

    @property
    def is_missing(self) -> bool:
        return False

    @abstractmethod
    async def process_messages(self,
                               full_history: MessagesStorage,
                               participants: list[str],
                               on_intermediate_response:
                               Callable[[str, AdapterIntermediateResponse],
                                        None] | None = None
                               ) -> TurnResult:
        ...

    @abstractmethod
    def to_record(self) -> PersistedParticipant:
        """The durable record persisted to participants.json for this seat."""
        ...
