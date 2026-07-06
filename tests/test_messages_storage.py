from pathlib import Path

import pytest


from manylogue.messages import MessageDraft, MessageKind, MessagesStorage
from tests.conftest import DEFAULT_AGENT_NAME, error_msg, human_msg


def fill_human_msg_storage(storage: MessagesStorage, *messages: str) -> list[str]:
    ids: list[str] = []
    for m in messages:
        added_message = storage.add_message(human_msg(m))
        ids.append(added_message.id)

    return ids


def test_error_messages_are_hidden_from_models(storage: MessagesStorage) -> None:
    storage.add_message(human_msg("hi"))
    storage.add_message(MessageDraft(
        kind=MessageKind.error, author=DEFAULT_AGENT_NAME, body="error"))

    chat_visible_msgs = storage.get_messages()
    chat_invisible_msgs = storage.get_messages(include_invisible=True)

    assert [m.body for m in chat_visible_msgs] == ["hi"]
    assert len(chat_invisible_msgs) == 2
    assert chat_invisible_msgs[-1].body == "error"


non_existent_cursor_test_data = [
    ("none"),
    (None)
]


@pytest.mark.parametrize("non_existent_cursor", non_existent_cursor_test_data)
def test_messages_after_for_non_existing_cursor_returns_full_history(storage: MessagesStorage, non_existent_cursor: str | None) -> None:

    messages = ["first", "second", "third"]
    fill_human_msg_storage(storage, *messages)

    new_msgs_after = storage.messages_after(
        non_existent_cursor, include_invisible=True)  # even with invisible turned on
    assert [m.body for m in new_msgs_after] == messages


def test_messages_after_specified_cursor_returns_only_new_messages(storage: MessagesStorage) -> None:
    messages = ["first", "second", "third", "fourth"]
    ids = fill_human_msg_storage(storage, *messages)

    cursor_position = 1

    new_msgs_after = storage.messages_after(ids[cursor_position])
    assert [m.body for m in new_msgs_after] == messages[cursor_position + 1:]


def test_messages_survive_reload(tmp_path: Path) -> None:
    s1 = MessagesStorage(tmp_path, "test")
    fill_human_msg_storage(s1, "first", "second")

    # errors also survive
    s1.add_message(error_msg("error"))

    # fresh instance, same dir, same chat name
    s2 = MessagesStorage(tmp_path, "test")
    s2.load()

    # no error here because it is invisible
    assert [m.body for m in s2.get_messages()] == ["first", "second"]
    assert [m.body for m in s2.get_messages(include_invisible=True)] == [
        "first", "second", "error"]
