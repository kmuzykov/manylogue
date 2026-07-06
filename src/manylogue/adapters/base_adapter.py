import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

from manylogue.messages.adapter_response import AdapterFinalResponse, AdapterIntermediateResponse
from manylogue.messages.message import Message

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    _working_dir: str

    __session_id: str | None

    # Roster last sent to this session, so the per-turn roster line is re-sent only when
    # membership changed (a stateful session remembers the prior one). None = nothing sent yet.
    _last_sent_roster: tuple[str, ...] | None

    def __init__(self, working_dir: str) -> None:
        self._working_dir = working_dir
        self.__session_id = None
        self._last_sent_roster = None

    @abstractmethod
    async def get_response(self,
                           agent_name: str,
                           system_prompt: str,
                           roster: Sequence[str],
                           full_history: Sequence[Message],
                           new_messages: Sequence[Message],
                           on_intermediate_response: Callable[[
                               AdapterIntermediateResponse], None]
                           ) -> AdapterFinalResponse | None:
        ...

    def get_session_id(self) -> str | None:
        return self.__session_id

    def restore_session_id(self, session_id: str | None) -> None:
        if self.__session_id is not None:
            logger.error(
                "Restoring session for adapter %s that already has session_id. "
                "\n Current session = %s. "
                "\n New session = %s",
                type(self).__name__, self.__session_id, session_id)

        self.__session_id = session_id

    def _update_session_id(self, session_id: str | None) -> None:
        # Subclass path: record the session id a completed turn produced (no guard).
        self.__session_id = session_id

    def _roster_line(self, roster: Sequence[str]) -> str:
        return f"Participants in the room right now (including you): {', '.join(roster)}."

    def _combine_new_messages(self, agent_name: str, roster: Sequence[str], new_messages: Sequence[Message]) -> str:

        # The roster travels per-turn — it can't live in the sent-once system prompt,
        # because membership changes mid-chat and a stateful session would never see the
        # update. Re-send it only when membership actually changed: the session remembers
        # the prior roster, so restating an unchanged room wastes tokens and attention.
        # Appending to the new-message block (never mutating earlier prompt content) also
        # keeps provider prefix caching intact. (A roster change landing on a turn that
        # then errors is the rare miss; the next change re-sends it.)
        combined_prompt = ""
        roster_key = tuple(roster)
        if roster_key != self._last_sent_roster:
            combined_prompt += self._roster_line(roster) + "\n\n"
            self._last_sent_roster = roster_key

        for m in new_messages:
            # Skip the agent's own messages — a stateful session already holds them
            # server-side. This mostly drops the agent's own last reply: with the cursor
            # at N, the agent is called, a human adds N+1 mid-turn, and the reply lands
            # as N+2. The cursor stops at N+1, so N+2 shows up as "new" next turn — but
            # the session has seen it, so re-sending it would duplicate.
            if m.author == agent_name:
                continue
            combined_prompt += f"[{m.author}]\n{m.body}\n\n"

        return combined_prompt
