from manylogue.agents import Agent, MissingAgent, PersistedParticipant, Role
from manylogue.agents.agent import SKIP_SENTINEL
from manylogue.messages import (
    AdapterIntermediateResponse, AgentTurnOutcome, MessageKind, MessagesStorage)

from tests.conftest import DEFAULT_AGENT_NAME, PARTICIPANTS_SINGLE, FakeAdapter, fake_definition, human_msg, agent_final_response, agent_narration, make_agent


async def test_agent_returns_final_as_message(storage: MessagesStorage) -> None:
    storage.add_message(human_msg("hi!"))

    reply_msg = "hi there!"
    agent = make_agent(agent_final_response(reply_msg))
    result = await agent.process_messages(storage, PARTICIPANTS_SINGLE)

    assert result.outcome == AgentTurnOutcome.answered
    assert result.draft is not None
    assert result.draft.body == reply_msg


async def test_base_prompt_includes_shared_room_state_coordination(storage: MessagesStorage) -> None:
    storage.add_message(human_msg("please continue"))
    adapter = FakeAdapter(agent_final_response("done"))
    agent = Agent(definition=fake_definition(), role=Role(), adapter=adapter,
                  working_dir="", name=DEFAULT_AGENT_NAME)

    await agent.process_messages(storage, PARTICIPANTS_SINGLE)

    assert adapter.last_system_prompt is not None
    assert "read what other participants said they already did" in adapter.last_system_prompt
    assert "verify the actual current" in adapter.last_system_prompt
    assert "Act on the remaining delta" in adapter.last_system_prompt


async def test_agent_returns_none_on_skip(storage: MessagesStorage) -> None:
    storage.add_message(human_msg("hi!"))

    agent = make_agent(agent_final_response(SKIP_SENTINEL))
    result = await agent.process_messages(storage, PARTICIPANTS_SINGLE)

    assert result.outcome == AgentTurnOutcome.skipped
    assert result.draft is None


async def test_agent_no_return_is_an_error(storage: MessagesStorage) -> None:
    storage.add_message(human_msg("hi!"))
    agent = make_agent()  # empty responses

    result = await agent.process_messages(storage, PARTICIPANTS_SINGLE)
    assert result.outcome == AgentTurnOutcome.errored
    assert result.draft is not None
    assert result.draft.kind == MessageKind.error


async def test_agent_doesnt_re_report_same_error_message(storage: MessagesStorage) -> None:
    # Note: This is a deliberate arch choice.
    # We dont want to spam and retriger other agents on the same error, if nothing has changed.

    storage.add_message(human_msg("hi!"))
    agent = make_agent()  # empty responses

    first = await agent.process_messages(storage, PARTICIPANTS_SINGLE)
    second = await agent.process_messages(storage, PARTICIPANTS_SINGLE)

    assert first.draft is not None and first.draft.kind == MessageKind.error
    # same error, not re-reported as a message — but the turn still errored
    assert second.draft is None
    assert second.outcome == AgentTurnOutcome.errored


async def test_intermediate_responses_reach_callback_and_thread(storage: MessagesStorage) -> None:
    storage.add_message(human_msg("hi!"))
    captured: list[AdapterIntermediateResponse] = []
    agent = make_agent(agent_narration("thinking..."),
                       agent_final_response("done"))

    result = await agent.process_messages(
        storage, PARTICIPANTS_SINGLE, lambda _name, resp: captured.append(resp))

    assert result.draft is not None and result.draft.body == "done"

    # callback got work, not the final
    assert [r.body for r in captured] == ["thinking..."]

    # work preserved on the draft
    assert [r.body for r in result.draft.thread] == [
        "thinking..."]


async def test_no_new_messages_are_skipped(storage: MessagesStorage) -> None:
    storage.add_message(human_msg("hi!"))

    agent = make_agent(agent_final_response("well hello"))

    # processes messages
    first = await agent.process_messages(storage, PARTICIPANTS_SINGLE)

    # no new messages -> idle (never engages)
    second = await agent.process_messages(storage, PARTICIPANTS_SINGLE)

    # another message by human/other agent -> another response
    storage.add_message(human_msg("are you still there?"))
    third = await agent.process_messages(storage, PARTICIPANTS_SINGLE)

    assert first.draft is not None and first.outcome == AgentTurnOutcome.answered
    assert second.draft is None and second.outcome == AgentTurnOutcome.idle
    assert third.draft is not None and third.outcome == AgentTurnOutcome.answered


def test_agent_to_record_reflects_identity() -> None:
    record = make_agent().to_record()
    assert record.def_name == DEFAULT_AGENT_NAME
    assert record.name == DEFAULT_AGENT_NAME
    assert record.directory == ""


async def test_missing_agent_skips_turn(storage: MessagesStorage) -> None:
    record = PersistedParticipant(def_name="Claude", name="Claude", directory="/p")
    missing = MissingAgent(record)

    assert missing.is_missing is True
    assert missing.agent_name == "Claude"

    result = await missing.process_messages(storage, ["Human", "Claude"])
    assert result.draft is None
    assert result.outcome == AgentTurnOutcome.idle

    # round-trips the record verbatim — state preserved for a later resume
    assert missing.to_record() == record
