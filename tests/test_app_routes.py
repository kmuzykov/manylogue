import json
from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

import manylogue.app as app_module


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    home = tmp_path / "home"
    monkeypatch.setenv("MANYLOGUE_HOME", str(home))
    app_module.config.home.cache_clear()
    app_module.chats.clear()
    with TestClient(app_module.app) as test_client:
        yield test_client
    app_module.config.home.cache_clear()
    app_module.chats.clear()


def test_create_chat_missing_form_fields_renders_inline_error(client: TestClient) -> None:
    response = client.post("/chats", data={})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("text/html")
    assert "That project directory doesn&#39;t exist" in response.text


def test_create_chat_expands_tilde_project_directory(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path / "os-home"
    project = fake_home / "project"
    project.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    response = client.post(
        "/chats",
        data={"chat_name": "test-chat", "chat_project_dir": "~/project"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/chat/test-chat-")
    chat_id = response.headers["location"].removeprefix("/chat/")
    meta_path = (
        app_module.config.home()
        / ".manylogue"
        / "storage"
        / "chats"
        / chat_id
        / "meta.json"
    )
    saved_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved_meta["default_project_dir"] == str(project.resolve())


def test_empty_chats_list_renders_empty_state(client: TestClient) -> None:
    response = client.get("/chats-list")

    assert response.status_code == 200
    assert "No chats yet" in response.text
