import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from manylogue.agents.agent_definition import AgentDefinition
from manylogue.messages.adapter_response import AdapterIntermediateResponse
from manylogue.agents import Agent, AgentBase, MissingAgent
from manylogue.agents.role import Role
from manylogue.chat.chat_participants_storage import ChatParticipantsStorage
from manylogue.chat.chat_meta_storage import ChatMetaStorage, ChatMetaModel
from manylogue.config.constants import HUMAN_NAME
from manylogue.messages import MessagesStorage, MessageDraft, Message
from manylogue.messages.agent_stream_event import AgentResponseStreamEventType, AgentStreamEvent, AgentTurnOutcome
from manylogue.util import is_chat_name_valid, make_chat_id, pick_unique_name

MAX_ROUNDS = 20

logger = logging.getLogger(__name__)


class ParticipantView(NamedTuple):
    """UI-facing roster entry: a name plus whether its definition is currently missing."""
    name: str
    is_missing: bool


class ChatRoom():

    _meta: ChatMetaModel

    # Working folder where the chat project lives, under it there's the .manylogue folder
    _workspace_root: Path
    _chat_dir: Path

    _meta_storage: ChatMetaStorage
    _message_storage: MessagesStorage
    _participants_storage: ChatParticipantsStorage
    _participants: list[AgentBase]

    _cond: asyncio.Condition
    _worker_task: asyncio.Task[None] | None
    _agent_stream_subscribers: list[asyncio.Queue[AgentStreamEvent]]

    def __init__(self, meta: ChatMetaModel, workspace_root: Path) -> None:
        self._meta = meta
        self._workspace_root = workspace_root
        self._chat_dir = ChatRoom.get_chat_dir(workspace_root, meta.id)

        # One directory per chat: meta.json + messages.jsonl + participants.json all live here.
        self._meta_storage = ChatMetaStorage(self._chat_dir)
        self._message_storage = MessagesStorage(self._chat_dir, meta.id)
        self._message_storage.load()

        self._participants_storage = ChatParticipantsStorage(self._chat_dir)
        self._participants = []

        self._cond = asyncio.Condition()
        self._worker_task = None

        self._agent_stream_subscribers = []

        self._restore_participants()

    @property
    def chat_id(self) -> str:
        return self._meta.id

    @property
    def name(self) -> str:
        return self._meta.name

    @property
    def default_project_dir(self) -> Path:
        return self._meta.default_project_dir

    def add_participant(self, agent: AgentBase) -> None:
        """Attach an already-built participant (live Agent or MissingAgent) to the roster.

        The low-level path: append only, NO persistence — so restore and tests never write.
        add_participant_by_def builds on it and is the only mutator that persists; that
        asymmetry is what keeps the in-memory roster and participants.json from drifting.
        """
        self._participants.append(agent)

    def add_participant_by_def(self, agent_def_name: str, agent_project_dir: str | None = None) -> None:
        """Resolve an agent definition (brain + soul + cwd) into an Agent, add it, persist.

        A def that can't be loaded or built (missing / unsafe / bad toml / unknown adapter)
        is logged and skipped — adding a fresh participant never crashes the request.
        """
        try:
            agent_def = AgentDefinition.load_one(
                self._workspace_root, agent_def_name)
            if agent_def is None:
                # unknown / renamed / unsafe ref — degrade gracefully, never crash
                logger.warning(
                    "unknown agent def '%s' — skipping", agent_def_name)
                return

            # Validate the cwd and fall back to the chat default; don't trust the caller.
            if agent_project_dir is None or not Path(agent_project_dir).is_dir():
                agent_project_dir = str(self._meta.default_project_dir)

            # Dedup happens here (the room knows the roster) so multiple instances of the same agent def can be added
            # the resolved name is persisted and reused verbatim on load — never re-derived.
            name = pick_unique_name(agent_def.name, self._taken_names())
            role = Role.load(self._workspace_root, agent_def.role)
            agent = Agent.from_definition(
                agent_def, role, agent_project_dir, name_override=name)
        except Exception:
            logger.warning(
                "agent def '%s' could not be built — skipping", agent_def_name, exc_info=True)
            return

        self.add_participant(agent)
        self._save_participants()

    def _restore_participants(self) -> None:
        """Rebuild the roster from participants.json on open.

        A resolvable def becomes a live Agent restored to its saved cursor/session. A def
        that is missing OR present-but-broken (bad toml, unknown adapter) becomes a
        MissingAgent that keeps the seat and its state. Read-only: never persists (load
        must not write, or restore would churn the file). One bad seat degrades to a
        MissingAgent rather than crashing the whole chat load.
        """
        for record in self._participants_storage.load():
            try:
                agent_def = AgentDefinition.load_one(
                    self._workspace_root, record.def_name)
                if agent_def is None:
                    raise ValueError(
                        f"agent def '{record.def_name}' not found")
                role = Role.load(self._workspace_root, agent_def.role)
                agent = Agent.from_definition(
                    agent_def, role, record.directory, name_override=record.name)
                agent.restore_state(record.state)
                self.add_participant(agent)
            except Exception:
                logger.warning(
                    "seat '%s' (def '%s') failed to build — restoring as MissingAgent",
                    record.name, record.def_name, exc_info=True)
                self.add_participant(MissingAgent(record))

    def _save_participants(self) -> None:
        """Project the roster (membership + each agent's cursor/session) to participants.json.
        Callers persist only when something actually changed — on add, and on a non-idle turn."""
        self._participants_storage.save(
            [p.to_record() for p in self._participants])

    def _taken_names(self) -> set[str]:
        # Includes missing seats — a temporarily-unresolved name stays reserved.
        return {HUMAN_NAME, *(p.agent_name for p in self._participants)}

    def get_roster_names(self) -> list[str]:
        """Model-facing roster: Human + active agents. MissingAgents are excluded — they
        can't participate, so the model shouldn't be told they're in the room."""
        return [HUMAN_NAME, *(p.agent_name for p in self._participants if not p.is_missing)]

    def get_participants_view(self) -> list[ParticipantView]:
        """UI roster: Human + every seat, missing ones flagged for Missing(Name) rendering."""
        view = [ParticipantView(name=HUMAN_NAME, is_missing=False)]
        view.extend(ParticipantView(name=p.agent_name, is_missing=p.is_missing)
                    for p in self._participants)
        return view

    async def append(self, draft: MessageDraft) -> Message:
        async with self._cond:
            msg = self._message_storage.add_message(draft)
            self._touch()
            self._cond.notify_all()
            return msg

    def _touch(self) -> None:
        """Bump last-activity time so list_chats can show recently-active chats first."""
        self._meta = self._meta.model_copy(
            update={"updated_at": datetime.now()})
        self._meta_storage.save(self._meta)

    def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(
                self._worker_loop(self._last_processed_message()))

    def _last_processed_message(self) -> str | None:
        messages = self._message_storage.get_messages(include_invisible=True)
        return messages[-1].id if messages else None

    async def stop(self) -> None:
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def _worker_loop(self, cursor_id: str | None) -> None:
        while True:

            # Block until ≥1 message exists after `cursor`. Reusing the SSE method matters:
            # it checks for pending messages WHILE HOLDING THE LOCK and only waits if there
            # are none — so a message appended while we were mid-pass is never missed
            # (this is the lost-wakeup fix; a bare cond.wait() drops that notify).
            # We ignore the returned list on purpose: each agent re-reads the full log and
            # decides via its own last-viewed index whether it was addressed.
            await self.process_existing_messages_or_wait_for_new(cursor_id)

            for _ in range(MAX_ROUNDS):
                latest_message = self._last_processed_message()

                for agent in self._participants:
                    # Missing seats are null-objects: they never take a turn (no adapter),
                    # so skip them outright rather than broadcasting an empty turn.
                    if agent.is_missing:
                        continue

                    # Light the dot up front. The no-engage path returns synchronously,
                    # so its start+end land together and the dot never visibly leaves
                    # green; only a real model call holds "working" long enough to show.
                    self._broadcast_agent_turn_start(agent.agent_name)
                    outcome = AgentTurnOutcome.errored  # until the turn reports otherwise

                    try:
                        result = await agent.process_messages(
                            self._message_storage,
                            self.get_roster_names(),
                            self._broadcast_agent_stream_event,
                        )

                        if result.draft is not None:
                            await self.append(result.draft)

                        # Persist after the draft is durable (a duplicate replay on crash
                        # beats a lost reply). Only an engaged turn can move the cursor or
                        # session; an idle turn changed nothing, so skip the write.
                        if result.outcome is not AgentTurnOutcome.idle:
                            self._save_participants()
                        outcome = result.outcome
                    except Exception:
                        logger.exception(
                            "agent (%s) turn crashed", agent.agent_name)
                    finally:
                        self._broadcast_agent_stream_end(
                            agent.agent_name, outcome)

                if latest_message == self._last_processed_message():
                    break  # no new messages, means agents conversation has settled/paused for human input

            # Move pointer to the latest processed message
            cursor_id = self._last_processed_message()

    async def process_existing_messages_or_wait_for_new(self, cursor_id: str | None) -> tuple[Message, ...]:
        async with self._cond:

            # first check if we already have messages accumulated or this is first call maybe
            new_messages = self._message_storage.messages_after(
                cursor_id, include_invisible=True)
            if new_messages:
                return new_messages

            # if not let's wait for new message to append
            await self._cond.wait()
            return self._message_storage.messages_after(cursor_id, include_invisible=True)

    def subscribe_to_agent_stream(self) -> asyncio.Queue[AgentStreamEvent]:
        queue: asyncio.Queue[AgentStreamEvent] = asyncio.Queue()
        self._agent_stream_subscribers.append(queue)
        return queue

    def unsubscribe_from_agent_stream(self, queue: asyncio.Queue[AgentStreamEvent]) -> None:
        if queue in self._agent_stream_subscribers:
            self._agent_stream_subscribers.remove(queue)
        else:
            logger.error("Trying to unsubscribe without a queue")

    def _publish_agent_stream_event(self, event: AgentStreamEvent) -> None:
        for s in self._agent_stream_subscribers:
            s.put_nowait(event)

    def _broadcast_agent_turn_start(self, author: str) -> None:
        self._publish_agent_stream_event(AgentStreamEvent(
            type=AgentResponseStreamEventType.agent_turn_start, author=author))

    def _broadcast_agent_stream_event(self, author: str, response: AdapterIntermediateResponse) -> None:
        self._publish_agent_stream_event(AgentStreamEvent(
            type=AgentResponseStreamEventType.agent_stream_event, author=author, response=response))

    def _broadcast_agent_stream_end(self, author: str, outcome: AgentTurnOutcome) -> None:
        self._publish_agent_stream_event(AgentStreamEvent(
            type=AgentResponseStreamEventType.agent_stream_end, author=author, outcome=outcome))

    # ---- identity / factory ----

    @staticmethod
    def create(workspace_root: Path, chat_project_dir: Path, name: str) -> "ChatRoom":
        """Mint a new chat: stable id, meta.json on disk, empty message log."""
        now = datetime.now()
        meta = ChatMetaModel(id=make_chat_id(name), name=name,
                        created_at=now, updated_at=now, default_project_dir=chat_project_dir)
        chat_dir = ChatRoom.get_chat_dir(workspace_root, meta.id)
        chat_dir.mkdir(parents=True, exist_ok=True)
        ChatMetaStorage(chat_dir).save(meta)
        # Write an empty participants.json up front so a later missing file is a real error
        # (corruption / manual deletion), not the normal "new chat, no participants yet" case.
        ChatParticipantsStorage(chat_dir).save([])
        return ChatRoom(meta, workspace_root)

    @staticmethod
    def open(workspace_root: Path, chat_id: str) -> "ChatRoom | None":
        """Load an existing chat by id. Returns None when it doesn't exist."""
        if not is_chat_name_valid(chat_id):
            return None
        meta_storage = ChatMetaStorage(
            ChatRoom.get_chat_dir(workspace_root, chat_id))
        if not meta_storage.exists():
            return None
        return ChatRoom(meta_storage.load(), workspace_root)

    @staticmethod
    def list_chats(workspace_root: Path) -> tuple[ChatMetaModel, ...]:
        """Every chat on disk, most-recently-active first. Names come from meta.json."""
        chats_root = ChatRoom.get_chats_storage_path(workspace_root)
        if not chats_root.exists():
            return ()
        metas: list[ChatMetaModel] = []
        for chat_dir in chats_root.iterdir():
            meta_storage = ChatMetaStorage(chat_dir)
            if meta_storage.exists():
                metas.append(meta_storage.load())
        metas.sort(key=lambda m: m.updated_at, reverse=True)
        return tuple(metas)

    # ---- paths ----

    @staticmethod
    def get_chats_storage_path(workspace_root: Path) -> Path:
        return workspace_root / ".manylogue" / "storage" / "chats"

    @staticmethod
    def get_chat_dir(workspace_root: Path, chat_id: str) -> Path:
        return ChatRoom.get_chats_storage_path(workspace_root) / chat_id
