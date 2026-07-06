import logging
import re
from collections.abc import Sequence
from typing import Callable

from manylogue.adapters import BaseAdapter
from manylogue.agents.agent_base import AgentBase
from manylogue.agents.agent_definition import AgentDefinition
from manylogue.agents.agent_participant import AgentState, PersistedParticipant
from manylogue.agents.turn_result import TurnResult
from manylogue.messages.adapter_response import AdapterFinalResponse, AdapterIntermediateResponse, AdapterIntermediateResponseType
from manylogue.messages.agent_stream_event import AgentTurnOutcome
from manylogue.agents.role import Role
from manylogue.messages import MessageDraft, Message, MessageKind, MessagesStorage
from manylogue.adapters.claude_adapter import ClaudeAdapter
from manylogue.adapters.codex_adapter import CodexAdapter


logger = logging.getLogger(__name__)

SKIP_SENTINEL = "<skip>"

SYSTEM_TEMPLATE = """\
You are {name}, one participant in a group text chat with a human and other AI agents.

How the chat is shown to you:
- Each message is tagged with [Author] showing who sent it. The body follows the tag.
- Messages may arrive as separate turns (one [Author] per turn) or grouped together in a single block (multiple [Author] blocks separated by blank lines). Treat both the same way.
- Treat [Author] as metadata, not part of what the speaker wrote.

Writing your reply:
- Write only the body. Do NOT prefix it with your name, an @-mention of yourself, or any [bracket]. The system tags messages.
- @-mention a participant (e.g. @Alice) only when you are directly addressing them. You don't need to @-mention to reply.

When to reply:
- You can see every message. Reply only when you genuinely add value: answer when you're
  addressed, make a substantive point, correct a real error, or ask a question the group needs.
- If someone already covered it, or you weren't addressed and have nothing to add, output exactly
  {sentinel} on its own and nothing else. Prefer {sentinel} over a low-value answer, "I agree" or "sounds good".
- If you feel the discussion has been ongoing for a long time without a human input also reply exactly {sentinel} to let them speak.

Shared-room coordination:
- Earlier messages are live room history, not a private task queue addressed only to you.
- Before acting, read what other participants said they already did, then verify the actual current
  state where relevant (files, git, tool output, app state). Do not be surprised by changes a peer
  already claimed to make, but do not trust a claim without checking when correctness matters.
- Act on the remaining delta: do not redo confirmed work, do not assume unverified work is done,
  and review, extend, correct, or skip as appropriate.
"""

# Finding @-mentions
MENTION_RE = re.compile(r"(?<!\w)@(\w+)")

# Poor man's toggle for the mention-only mode; stays a constant until chat modes are
# wired into routing. The gate returns idle without moving the cursor, so a later
# mention delivers the full backlog.
ONLY_REPLY_WHEN_MENTIONED = False


class Agent(AgentBase):
    _definition: AgentDefinition
    _role: Role
    _adapter: BaseAdapter
    _working_dir: str
    _last_seen_message_id_cursor: str | None
    _errored_message_id: str | None

    def __init__(self, definition: AgentDefinition, role: Role, adapter: BaseAdapter,
                 working_dir: str, name: str) -> None:
        super().__init__(name)
        self._definition = definition
        self._role = role
        self._adapter = adapter
        self._working_dir = working_dir

        self._last_seen_message_id_cursor = None
        self._errored_message_id = None

    async def process_messages(self,
                               full_history: MessagesStorage,
                               participants: list[str],
                               on_intermediate_response:
                               Callable[[str, AdapterIntermediateResponse],
                                        None] | None = None
                               ) -> TurnResult:
        """Run one turn and pair the draft to commit (if any) with the outcome:

        - answered: draft is the final reply (kind=message)
        - errored:  draft is one error bubble (kind=error) — or None when the same
                    stuck position already produced one, so the error isn't re-reported
        - skipped:  no draft — engaged the model, which chose to stay silent
        - idle:     no draft — nothing new / not addressed, model never engaged
        """

        # We need to take a snapshot here, since while we await more messages can appear
        history_snapshot = full_history.get_messages()
        new_messages = full_history.messages_after(
            self._last_seen_message_id_cursor)

        # Always idle when nothing new arrived from anyone else — safe in every mode,
        # and the thing that stops agents endlessly replying to their own last message.
        new_from_others = [
            m for m in new_messages if m.author != self.agent_name]
        if not new_from_others:
            return TurnResult(None, AgentTurnOutcome.idle)

        logger.debug("New messages to %s: %s", self.agent_name, new_messages)

        is_mentioned = self._was_agent_mentioned(new_messages)

        logger.debug("%s was mentioned: %s", self.agent_name, is_mentioned)

        # Not mentioned -> idle without moving the cursor, so these messages are
        # re-delivered (and can still be contributed to) once the agent is addressed.
        if not is_mentioned and ONLY_REPLY_WHEN_MENTIONED:
            return TurnResult(None, AgentTurnOutcome.idle)

        # Roster is NOT baked into the (cached, sent-once) system prompt — it changes as
        # participants join, and stateful adapters wouldn't see the update. It travels
        # per-turn via the `participants` arg below instead.
        system_prompt = SYSTEM_TEMPLATE.format(
            name=self.agent_name,
            sentinel=SKIP_SENTINEL)

        if self._role.role_prompt.strip() != "":
            system_prompt += "\n\n" + self._role.role_prompt

        logger.debug("Calling %s with %d new messages",
                     self.agent_name, len(new_messages))

        last_message_seen_before_agent_call = new_messages[-1].id
        thread_responses: list[AdapterIntermediateResponse] = []

        def record_intermediate(response: AdapterIntermediateResponse) -> None:
            logger.debug("Got a reply from %s: %s", self.agent_name, response)
            thread_responses.append(response)
            if on_intermediate_response is not None:
                on_intermediate_response(self.agent_name, response)

        final_response: AdapterFinalResponse | None = None
        try:
            final_response = await self._adapter.get_response(
                self.agent_name,
                system_prompt,
                participants,  # current roster, injected per-turn (not in the system prompt)
                history_snapshot,  # passing snapshot, since full_history is a live list
                new_messages,
                record_intermediate)
        except Exception:
            logger.exception("%s: adapter call failed", self.agent_name)

        answer_message = None
        if final_response is not None:
            logger.debug("Got a reply from %s: %s",
                         self.agent_name, final_response)
            answer_message = final_response.body

        if answer_message is None:

            # errored again on the same message -> skip as we already reported that error.
            if self._errored_message_id == last_message_seen_before_agent_call:
                return TurnResult(None, AgentTurnOutcome.errored)
            
            self._errored_message_id = last_message_seen_before_agent_call
            return TurnResult(
                MessageDraft(kind=MessageKind.error,
                             author=self.agent_name,
                             body="Error: Failed to reply (see server log)",
                             thread=tuple(thread_responses)),
                AgentTurnOutcome.errored)

        # Moving cursor to the last message if we got an answer (skip _is_ an answer)
        self._update_cursor_position(
            last_message_seen_before_agent_call)

        # the model chose to stay silent (nothing to say)
        if answer_message.strip().lower() == SKIP_SENTINEL:
            return TurnResult(None, AgentTurnOutcome.skipped)

        # Some agents (e.g. Claude) stream their final answer as the last narration too —
        # drop that duplicate so the collapsed thread doesn't end with a copy of the reply.
        if (
            thread_responses
            and thread_responses[-1].type == AdapterIntermediateResponseType.narration
            and thread_responses[-1].body.strip() == answer_message.strip()
        ):
            thread_responses.pop()

        return TurnResult(
            MessageDraft(kind=MessageKind.message,
                         author=self.agent_name,
                         body=answer_message,
                         thread=tuple(thread_responses)),
            AgentTurnOutcome.answered)

    def _update_cursor_position(self, new_cursor_id: str) -> None:
        self._last_seen_message_id_cursor = new_cursor_id

        # resetting error on successful answer
        self._errored_message_id = None

    def _was_agent_mentioned(self, new_messages: Sequence[Message]) -> bool:
        for m in new_messages:
            # skip self mentions just to guard against infinite loop of agents mentioning themselves
            if m.author == self.agent_name:
                continue

            mentions = MENTION_RE.findall(m.body)
            if self.agent_name in mentions:
                return True

        return False

    def _export_state(self) -> AgentState:
        session_id = self._adapter.get_session_id()
        return AgentState(last_seen_message_id=self._last_seen_message_id_cursor, adapter_session_id=session_id)

    def restore_state(self, state: AgentState) -> None:
        self._adapter.restore_session_id(state.adapter_session_id)

        if self._last_seen_message_id_cursor is not None:
            logger.error("Restoring Agent %s last seen message when current is not None"
                         "\n Current = %s"
                         "\n New = %s",
                         self.agent_name, self._last_seen_message_id_cursor, state.last_seen_message_id)

        self._last_seen_message_id_cursor = state.last_seen_message_id

    def to_record(self) -> PersistedParticipant:
        # Derived from the live object — the single copy of name/def/cwd, plus current
        # state — so the durable record can never disagree with the agent.
        return PersistedParticipant(
            def_name=self._definition.name,
            name=self.agent_name,
            directory=self._working_dir,
            state=self._export_state())

    @staticmethod
    def _build_adapter(definition: AgentDefinition, working_dir: str) -> BaseAdapter:
        # todo: a more elegant way (e.g. registry to allow user expansion) than a matcher over adapter names
        match definition.adapter:
            case "ClaudeAdapter":
                return ClaudeAdapter(working_dir, definition.model)
            case "CodexAdapter":
                return CodexAdapter(working_dir, definition.model)
            case _:
                raise ValueError(f"Unknown agent adapter: {definition.adapter}")

    @staticmethod
    def from_definition(definition: AgentDefinition, role: Role, working_dir: str,
                        name_override: str | None = None) -> "Agent":
        # Role is loaded by the caller (which knows the home); Agent just wires brain + soul.
        # Name uniqueness is decided OUTSIDE (ChatRoom, which knows the roster) and passed
        # in as name_override; default is the definition's own name.
        adapter = Agent._build_adapter(definition, working_dir)
        return Agent(definition, role, adapter, working_dir, name_override or definition.name)
