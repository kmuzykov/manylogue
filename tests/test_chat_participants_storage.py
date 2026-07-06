from pathlib import Path

from manylogue.agents import AgentState, PersistedParticipant
from manylogue.chat import ChatParticipantsStorage


def test_participants_round_trip(tmp_path: Path) -> None:
    storage = ChatParticipantsStorage(tmp_path)
    records = [
        PersistedParticipant(
            def_name="Claude", name="Claude", directory="/x",
            state=AgentState(last_seen_message_id="m-1", adapter_session_id="s-1")),
        PersistedParticipant(def_name="Claude", name="Claude_2", directory="/y"),
    ]

    storage.save(records)

    assert storage.load() == tuple(records)


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    assert ChatParticipantsStorage(tmp_path).load() == ()
