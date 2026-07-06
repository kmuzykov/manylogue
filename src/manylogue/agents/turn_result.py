from typing import NamedTuple

from manylogue.messages import MessageDraft
from manylogue.messages.agent_stream_event import AgentTurnOutcome


class TurnResult(NamedTuple):
    """What an agent's turn produced: the draft to commit (if any) and how it ended."""
    draft: MessageDraft | None
    outcome: AgentTurnOutcome
