from collections.abc import Callable

from manylogue.agents.agent_base import AgentBase
from manylogue.agents.agent_participant import PersistedParticipant
from manylogue.agents.turn_result import TurnResult
from manylogue.messages import MessagesStorage
from manylogue.messages.adapter_response import AdapterIntermediateResponse
from manylogue.messages.agent_stream_event import AgentTurnOutcome


class MissingAgent(AgentBase):
    """Null-object stand-in for a participant whose agent definition can't be resolved
    (deleted / renamed / unsafe ref). Keeps its seat and its saved state, renders as
    Missing(Name) in the roster, and skips every turn (it has no adapter). If the def
    reappears, the next load rebuilds a live Agent that resumes from this record's cursor.
    """

    _record: PersistedParticipant

    def __init__(self, record: PersistedParticipant) -> None:
        super().__init__(record.name)
        self._record = record

    @property
    def is_missing(self) -> bool:
        return True

    async def process_messages(self,
                               full_history: MessagesStorage,
                               participants: list[str],
                               on_intermediate_response:
                               Callable[[str, AdapterIntermediateResponse],
                                        None] | None = None
                               ) -> TurnResult:
        # Never engages a model — idle means "did not participate this turn".
        return TurnResult(None, AgentTurnOutcome.idle)

    def to_record(self) -> PersistedParticipant:
        # Round-trip the record verbatim so a temporary def outage loses nothing.
        return self._record
