import pytest
from pathlib import Path
from collections.abc import Callable, Sequence

from manylogue.adapters import BaseAdapter
from manylogue.agents import Agent, AgentDefinition, Role
from manylogue.messages import (
    AdapterFinalResponse, AdapterIntermediateResponse, AdapterIntermediateResponseType,
    Message, MessageDraft, MessageKind, MessagesStorage)

DEFAULT_AGENT_NAME = "AgentBot"
PARTICIPANTS_SINGLE = ["Human", DEFAULT_AGENT_NAME]


class FakeAdapter(BaseAdapter):

    _scripted_responses: tuple[AdapterIntermediateResponse |
                               AdapterFinalResponse, ...]
    last_system_prompt: str | None
    last_roster: Sequence[str] | None
    last_new_messages: Sequence[Message] | None

    def __init__(self, *scripted_responses: AdapterIntermediateResponse | AdapterFinalResponse, working_dir: str = "") -> None:
        super().__init__(working_dir)
        self._scripted_responses = scripted_responses
        self.last_system_prompt = None
        self.last_roster = None
        self.last_new_messages = None

    async def get_response(self,
                           agent_name: str,
                           system_prompt: str,
                           roster: Sequence[str],
                           full_history: Sequence[Message],
                           new_messages: Sequence[Message],
                           on_intermediate_response: Callable[[AdapterIntermediateResponse], None]) -> AdapterFinalResponse | None:

        self.last_system_prompt = system_prompt
        self.last_roster = roster
        self.last_new_messages = new_messages

        for r in self._scripted_responses:
            if isinstance(r, AdapterFinalResponse):
                return r
            on_intermediate_response(r)
        return None


def fake_definition(name: str = DEFAULT_AGENT_NAME) -> AgentDefinition:
    """A synthetic agent definition for tests — pairs with FakeAdapter via the
    fake_adapters fixture (which bypasses the real Claude/Codex adapter wiring)."""
    return AgentDefinition(adapter="FakeAdapter", name=name,
                           description="test", role="", model="")


def make_agent(*responses: AdapterIntermediateResponse | AdapterFinalResponse) -> Agent:
    return Agent(definition=fake_definition(), role=Role(),
                 adapter=FakeAdapter(*responses), working_dir="", name=DEFAULT_AGENT_NAME)


def write_agent_def(home: Path, name: str, *, adapter: str = "FakeAdapter",
                    role: str = "", model: str = "") -> None:
    """Write a minimal agent-def toml into <home>/.manylogue/agents so load_one finds it.
    The name comes from the file stem (load() overrides any name in the toml)."""
    agents_dir = home / ".manylogue" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{name}.toml").write_text(
        f'adapter = "{adapter}"\ndescription = "test"\nrole = "{role}"\nmodel = "{model}"\n',
        encoding="utf-8")


def _fake_build_adapter(definition: AgentDefinition, working_dir: str) -> BaseAdapter:
    return FakeAdapter(working_dir=working_dir)


@pytest.fixture
def fake_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make Agent.from_definition build a FakeAdapter regardless of the def's adapter
    name, so ChatRoom add/restore flows can be exercised without real backends."""
    monkeypatch.setattr(Agent, "_build_adapter",
                        staticmethod(_fake_build_adapter))


@pytest.fixture
def storage(tmp_path: Path) -> MessagesStorage:
    return MessagesStorage(tmp_path, "test")


def human_msg(msg: str) -> MessageDraft:
    return MessageDraft(kind=MessageKind.message, author="Human", body=msg)


def error_msg(msg: str) -> MessageDraft:
    return MessageDraft(kind=MessageKind.error, author=DEFAULT_AGENT_NAME, body=msg)


def agent_final_response(msg: str) -> AdapterFinalResponse:
    return AdapterFinalResponse(body=msg)


def agent_narration(msg: str) -> AdapterIntermediateResponse:
    return AdapterIntermediateResponse(type=AdapterIntermediateResponseType.narration, body=msg)
