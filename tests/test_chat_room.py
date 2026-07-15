import asyncio
from collections.abc import Sequence
from pathlib import Path

from manylogue.agents import PersistedParticipant
from manylogue.chat import ChatParticipantsStorage, ChatRoom
from manylogue.messages import (
    AgentResponseStreamEventType, AgentStreamEvent, AgentTurnOutcome)
from tests.conftest import (agent_final_response, agent_narration, human_msg,
                            make_agent, write_agent_def)


async def _drain_until_end(queue: "asyncio.Queue[AgentStreamEvent]") -> AgentStreamEvent:
    """Pull events until the turn's end signal, which carries the outcome."""
    while True:
        event = await asyncio.wait_for(queue.get(), timeout=2.0)
        if event.type == AgentResponseStreamEventType.agent_stream_end:
            return event


class RecordingParticipantsStorage(ChatParticipantsStorage):
    """Captures whether the agent's reply was already durable in messages.jsonl the first
    time the roster is persisted — the Q-19 append-before-persist ordering guarantee."""
    first_save_saw_reply: bool | None
    _reply_body: str

    def __init__(self, chat_dir: Path, reply_body: str) -> None:
        super().__init__(chat_dir)
        self.first_save_saw_reply = None
        self._reply_body = reply_body

    def save(self, participants: Sequence[PersistedParticipant]) -> None:
        if self.first_save_saw_reply is None:
            messages_file = self._path.parent / "messages.jsonl"
            messages_text = messages_file.read_text(
                encoding="utf-8") if messages_file.exists() else ""
            self.first_save_saw_reply = self._reply_body in messages_text
        super().save(participants)


async def test_append_wakes_a_waiter(tmp_path: Path) -> None:
    room = ChatRoom.create(tmp_path, tmp_path, "test")

    waiter = asyncio.create_task(
        room.process_existing_messages_or_wait_for_new(None))

    # let the waiter reach its wait()
    await asyncio.sleep(0)

    msg = await room.append(human_msg("hi"))

    got = await asyncio.wait_for(waiter, timeout=1.0)
    assert [m.id for m in got] == [msg.id]


async def test_worker_runs_agent_and_commits_its_reply(tmp_path: Path) -> None:
    agent = make_agent(agent_final_response("hello"))

    room = ChatRoom.create(tmp_path, tmp_path, "test")
    room.add_participant(agent)

    room.start()
    try:
        human = await room.append(human_msg("hi"))

        # block until something lands AFTER the human message
        replies = await asyncio.wait_for(
            room.process_existing_messages_or_wait_for_new(human.id),
            timeout=2.0,
        )

        assert [m.author for m in replies] == [agent.agent_name]
        assert replies[0].body == "hello"
    finally:
        await room.stop()


async def test_worker_appends_reply_before_persisting_participants(tmp_path: Path) -> None:
    reply_body = "durable first"
    agent = make_agent(agent_final_response(reply_body))

    room = ChatRoom.create(tmp_path, tmp_path, "test")
    room.add_participant(agent)

    recorder = RecordingParticipantsStorage(
        ChatRoom.get_chat_dir(tmp_path, room.chat_id), reply_body)
    setattr(room, "_participants_storage", recorder)

    room.start()
    try:
        human = await room.append(human_msg("hi"))

        await asyncio.wait_for(
            room.process_existing_messages_or_wait_for_new(human.id),
            timeout=2.0,
        )

        assert recorder.first_save_saw_reply is True
    finally:
        await room.stop()


async def test_agent_work_events_reach_a_subscriber(tmp_path: Path) -> None:
    agent = make_agent(
        agent_narration("thinking"),
        agent_final_response("done"))

    room = ChatRoom.create(tmp_path, tmp_path, "test")
    room.add_participant(agent)

    # subscribe BEFORE the agent runs — no replay
    queue = room.subscribe_to_agent_stream()

    room.start()
    try:
        await room.append(human_msg("hi"))

        # the lifecycle opens with a turn-start signal, fired before any output
        start = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert start.author == agent.agent_name
        assert start.type == AgentResponseStreamEventType.agent_turn_start
        assert start.response is None

        # then the intermediate work events
        event = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert event.author == agent.agent_name
        assert event.response is not None
        assert event.type == AgentResponseStreamEventType.agent_stream_event
        assert event.response.body == "thinking"  # the narration — NOT the final
    finally:
        room.unsubscribe_from_agent_stream(queue)
        await room.stop()


async def test_skip_after_thinking_reports_skipped(tmp_path: Path) -> None:
    # engages the model (a narration), then the model emits the skip sentinel
    agent = make_agent(
        agent_narration("considering"),
        agent_final_response("<skip>"))

    room = ChatRoom.create(tmp_path, tmp_path, "test")
    room.add_participant(agent)
    queue = room.subscribe_to_agent_stream()

    room.start()
    try:
        await room.append(human_msg("hi"))

        # turn_start proves it engaged — so the None reply is a skip, not idle
        start = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert start.type == AgentResponseStreamEventType.agent_turn_start

        end = await _drain_until_end(queue)
        assert end.outcome == AgentTurnOutcome.skipped
    finally:
        room.unsubscribe_from_agent_stream(queue)
        await room.stop()


# --- participant persistence / dedup / missing-def (fake_adapters bypasses real backends) ---


async def test_duplicate_def_gets_numbered_seat(tmp_path: Path, fake_adapters: None) -> None:
    write_agent_def(tmp_path, "Claude")
    room = ChatRoom.create(tmp_path, tmp_path, "test")

    room.add_participant_by_def("Claude", str(tmp_path))
    room.add_participant_by_def("Claude", str(tmp_path))

    # same role allowed; the second seat is numbered, not rejected
    assert room.get_roster_names() == ["Human", "Claude", "Claude_2"]


async def test_duplicate_seat_persists_and_resumes(tmp_path: Path, fake_adapters: None) -> None:
    write_agent_def(tmp_path, "Claude")
    room = ChatRoom.create(tmp_path, tmp_path, "test")
    room.add_participant_by_def("Claude", str(tmp_path))
    room.add_participant_by_def("Claude", str(tmp_path))

    # reopen from disk: both seats come back, deduped names reused verbatim
    reopened = ChatRoom.open(tmp_path, room.chat_id)
    assert reopened is not None
    assert reopened.get_roster_names() == ["Human", "Claude", "Claude_2"]


async def test_missing_def_restored_as_missing_then_resumes(tmp_path: Path, fake_adapters: None) -> None:
    write_agent_def(tmp_path, "Claude")
    room = ChatRoom.create(tmp_path, tmp_path, "test")
    room.add_participant_by_def("Claude", str(tmp_path))

    # def disappears -> seat retained as a MissingAgent, excluded from the model roster
    (tmp_path / ".manylogue" / "agents" / "Claude.toml").unlink()
    missing_room = ChatRoom.open(tmp_path, room.chat_id)
    assert missing_room is not None
    view = {(v.name, v.is_missing) for v in missing_room.get_participants_view()}
    assert ("Claude", True) in view
    assert missing_room.get_roster_names() == ["Human"]

    # def returns -> seat is live again on the next open
    write_agent_def(tmp_path, "Claude")
    live_room = ChatRoom.open(tmp_path, room.chat_id)
    assert live_room is not None
    assert live_room.get_roster_names() == ["Human", "Claude"]


async def test_broken_def_restores_as_missing_not_crash(tmp_path: Path) -> None:
    # A def that loads but has an unknown adapter must degrade to MissingAgent on restore,
    # not crash chat load. No fake_adapters here: we want the real _build_adapter to raise.
    write_agent_def(tmp_path, "Bad", adapter="BogusAdapter")
    room = ChatRoom.create(tmp_path, tmp_path, "test")
    ChatParticipantsStorage(ChatRoom.get_chat_dir(tmp_path, room.chat_id)).save(
        [PersistedParticipant(def_name="Bad", name="Bad", directory=str(tmp_path))])

    reopened = ChatRoom.open(tmp_path, room.chat_id)  # must not raise
    assert reopened is not None
    view = {(v.name, v.is_missing) for v in reopened.get_participants_view()}
    assert ("Bad", True) in view
    assert reopened.get_roster_names() == ["Human"]


async def test_def_with_unknown_key_restores_as_missing_not_crash(tmp_path: Path) -> None:
    # extra="forbid" on AgentDefinition: a typo'd key fails validation loudly and the
    # seat degrades to MissingAgent — instead of silently running with defaults.
    write_agent_def(tmp_path, "Typo", extra_lines='reasonning_effort = "high"\n')
    room = ChatRoom.create(tmp_path, tmp_path, "test")
    ChatParticipantsStorage(ChatRoom.get_chat_dir(tmp_path, room.chat_id)).save(
        [PersistedParticipant(def_name="Typo", name="Typo", directory=str(tmp_path))])

    reopened = ChatRoom.open(tmp_path, room.chat_id)  # must not raise
    assert reopened is not None
    view = {(v.name, v.is_missing) for v in reopened.get_participants_view()}
    assert ("Typo", True) in view
    assert reopened.get_roster_names() == ["Human"]


async def test_add_broken_def_is_skipped_not_crash(tmp_path: Path) -> None:
    # Adding a def with an unknown adapter logs + skips; it never crashes the request.
    write_agent_def(tmp_path, "Bad", adapter="BogusAdapter")
    room = ChatRoom.create(tmp_path, tmp_path, "test")

    room.add_participant_by_def("Bad", str(tmp_path))  # must not raise

    assert room.get_roster_names() == ["Human"]
