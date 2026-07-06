from collections.abc import AsyncIterator
from pathlib import Path
from types import TracebackType
from typing import ClassVar

import pytest

import manylogue.adapters.codex_adapter as codex_adapter
from manylogue.adapters import CodexAdapter
from manylogue.messages import MessagesStorage
from tests.conftest import human_msg


class FakeTurn:
    async def stream(self) -> AsyncIterator[object]:
        for item in ():
            yield item


class FakeThread:
    id: str = "fresh-thread"
    prompts: list[str]

    def __init__(self) -> None:
        self.prompts = []

    async def turn(self, prompt: str, cwd: str, model: str, summary: object, effort: object) -> FakeTurn:
        self.prompts.append(prompt)
        return FakeTurn()


class FakeCodex:
    latest: ClassVar["FakeCodex | None"] = None

    resume_calls: list[tuple[str, str]]
    start_calls: list[str]
    thread: FakeThread

    def __init__(self, config: object) -> None:
        self.resume_calls = []
        self.start_calls = []
        self.thread = FakeThread()
        FakeCodex.latest = self

    async def __aenter__(self) -> "FakeCodex":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def thread_resume(self, session_id: str, cwd: str) -> FakeThread:
        self.resume_calls.append((session_id, cwd))
        raise RuntimeError("stale thread")

    async def thread_start(self, cwd: str, model: str) -> FakeThread:
        self.start_calls.append(cwd)
        return self.thread


async def test_codex_stale_resume_clears_session_and_retries_fresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(codex_adapter, "AsyncCodex", FakeCodex)

    storage = MessagesStorage(tmp_path, "test")
    message = storage.add_message(human_msg("hi"))

    adapter = CodexAdapter("/work/project")
    adapter.restore_session_id("dead-thread")

    result = await adapter.get_response(
        agent_name="Codex",
        system_prompt="SYSTEM",
        roster=["Human", "Codex"],
        full_history=(message,),
        new_messages=(message,),
        on_intermediate_response=lambda _response: None,
    )

    fake = FakeCodex.latest
    assert fake is not None
    assert result is not None
    assert adapter.get_session_id() == "fresh-thread"
    assert fake.resume_calls == [("dead-thread", "/work/project")]
    assert fake.start_calls == ["/work/project"]
    # roster now leads the per-turn prompt (Q-16: not baked into the system prompt)
    assert fake.thread.prompts == [
        "SYSTEM\n\nParticipants in the room right now (including you): Human, Codex.\n\n[Human]\nhi\n\n"]
