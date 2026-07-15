from collections.abc import AsyncIterator
from pathlib import Path
from types import TracebackType
from typing import ClassVar

import pytest

import manylogue.adapters.codex_adapter as codex_adapter
from manylogue.adapters import CodexAdapter
from manylogue.adapters.codex_adapter import ReasoningEffort
from manylogue.messages import MessagesStorage
from tests.conftest import human_msg


class FakeTurn:
    async def stream(self) -> AsyncIterator[object]:
        for item in ():
            yield item


class FakeThread:
    id: str = "fresh-thread"
    prompts: list[str]
    efforts: list[object]

    def __init__(self) -> None:
        self.prompts = []
        self.efforts = []

    async def turn(self, prompt: str, cwd: str, model: str, summary: object, effort: object) -> FakeTurn:
        self.prompts.append(prompt)
        self.efforts.append(effort)
        return FakeTurn()


class FakeCodex:
    latest: ClassVar["FakeCodex | None"] = None

    resume_calls: list[tuple[str, str]]
    start_calls: list[str]
    thread: FakeThread

    config: object

    def __init__(self, config: object) -> None:
        self.config = config
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
    # unset in the def -> the adapter default (medium, matching stock Codex)
    assert fake.thread.efforts == [ReasoningEffort.medium]


async def test_codex_reasoning_effort_from_def_reaches_turn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(codex_adapter, "AsyncCodex", FakeCodex)

    storage = MessagesStorage(tmp_path, "test")
    message = storage.add_message(human_msg("hi"))

    adapter = CodexAdapter("/work/project", model="gpt-5.6-sol",
                           reasoning_effort="high")

    await adapter.get_response(
        agent_name="Codex",
        system_prompt="SYSTEM",
        roster=["Human", "Codex"],
        full_history=(message,),
        new_messages=(message,),
        on_intermediate_response=lambda _response: None,
    )

    fake = FakeCodex.latest
    assert fake is not None
    assert fake.thread.efforts == [ReasoningEffort.high]


def test_codex_invalid_reasoning_effort_raises() -> None:
    # Fail fast at seat build (add skips / restore degrades to MissingAgent),
    # never mid-turn.
    with pytest.raises(ValueError, match="reasoning_effort"):
        CodexAdapter("/work/project", reasoning_effort="ultra")


async def test_codex_bin_env_override_reaches_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # MANYLOGUE_CODEX_BIN escape hatch: a standalone codex executable for when the
    # bundled runtime lags newly released models. Unset -> None -> SDK default.
    monkeypatch.setattr(codex_adapter, "AsyncCodex", FakeCodex)
    monkeypatch.setenv("MANYLOGUE_CODEX_BIN", "/opt/codex/codex")

    storage = MessagesStorage(tmp_path, "test")
    message = storage.add_message(human_msg("hi"))

    adapter = CodexAdapter("/work/project")
    await adapter.get_response(
        agent_name="Codex",
        system_prompt="SYSTEM",
        roster=["Human", "Codex"],
        full_history=(message,),
        new_messages=(message,),
        on_intermediate_response=lambda _response: None,
    )

    fake = FakeCodex.latest
    assert fake is not None
    assert isinstance(fake.config, codex_adapter.CodexConfig)
    assert fake.config.codex_bin == "/opt/codex/codex"
    assert fake.config.cwd == "/work/project"
