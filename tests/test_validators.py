from pathlib import Path

import pytest

from manylogue.util import resolve_existing_dir


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # expanduser reads USERPROFILE on Windows and HOME on POSIX; pin both.
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_tilde_path_expands_to_home_subdir(fake_home: Path) -> None:
    (fake_home / "project").mkdir()
    assert resolve_existing_dir("~/project") == (fake_home / "project").resolve()


def test_missing_tilde_path_is_rejected(fake_home: Path) -> None:
    assert resolve_existing_dir("~/definitely-not-here") is None


def test_absolute_dir_is_accepted(tmp_path: Path) -> None:
    assert resolve_existing_dir(str(tmp_path)) == tmp_path.resolve()


def test_surrounding_whitespace_is_ignored(tmp_path: Path) -> None:
    assert resolve_existing_dir(f"  {tmp_path}  ") == tmp_path.resolve()


def test_file_path_is_rejected(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    assert resolve_existing_dir(str(file_path)) is None


def test_empty_and_none_are_rejected() -> None:
    # Path("") is "."; empty input must not validate as the server's own cwd.
    assert resolve_existing_dir("") is None
    assert resolve_existing_dir("   ") is None
    assert resolve_existing_dir(None) is None
