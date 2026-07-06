import json
from datetime import datetime
from pathlib import Path

from manylogue.chat import ChatMetaModel, ChatMetaStorage


def test_meta_round_trips(tmp_path: Path) -> None:
    storage = ChatMetaStorage(tmp_path)
    meta = ChatMetaModel(id="alpha-abc123", name="Alpha",
                         created_at=datetime(2026, 6, 1, 12, 0),
                         updated_at=datetime(2026, 6, 2, 9, 30))
    storage.save(meta)

    assert storage.load() == meta


def test_meta_missing_updated_at_still_loads(tmp_path: Path) -> None:
    # A meta.json written before `updated_at` existed must still load: an additive field
    # defaults, it does not become a required-field validation error (the load crash we hit).
    (tmp_path / "meta.json").write_text(
        json.dumps({
            "schema_version": 1,
            "id": "alpha-abc123",
            "name": "Alpha",
            "mode": "round_robin",
            "created_at": "2026-06-01T12:00:00",
        }),
        encoding="utf-8",
    )

    meta = ChatMetaStorage(tmp_path).load()

    assert meta.id == "alpha-abc123"
    assert meta.name == "Alpha"
    assert meta.updated_at is not None  # populated by default, not missing


def test_meta_loads_with_legacy_participants_key(tmp_path: Path) -> None:
    # participants used to live on ChatMetaModel; they now have their own participants.json.
    # An old meta.json still carries the key — pydantic ignores extras, so it must still
    # load rather than crash on an unexpected field.
    (tmp_path / "meta.json").write_text(
        json.dumps({
            "schema_version": 2,
            "id": "alpha-abc123",
            "name": "Alpha",
            "mode": "round_robin",
            "created_at": "2026-06-01T12:00:00",
            "updated_at": "2026-06-01T12:00:00",
            "default_project_dir": "/work/project",
            "participants": [{"name": "Claude", "directory": "/x"}],
        }),
        encoding="utf-8",
    )

    meta = ChatMetaStorage(tmp_path).load()

    assert meta.id == "alpha-abc123"
    assert meta.name == "Alpha"
