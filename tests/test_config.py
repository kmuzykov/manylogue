import os
from pathlib import Path

import pytest

from manylogue import config


# --- first-run seeding ---

def test_seeding_copies_packaged_defaults(tmp_path: Path) -> None:
    home = config.ensure_home_seeded(tmp_path)

    assert home == tmp_path
    assert (tmp_path / ".manylogue" / "agents" / "Claude.toml").is_file()
    assert (tmp_path / ".manylogue" / "roles" / "empty_role.md").is_file()


def test_seeding_never_overwrites_user_edits(tmp_path: Path) -> None:
    config.ensure_home_seeded(tmp_path)
    target = tmp_path / ".manylogue" / "agents" / "Claude.toml"
    target.write_text("user-edited", encoding="utf-8")

    config.ensure_home_seeded(tmp_path)

    assert target.read_text(encoding="utf-8") == "user-edited"


def test_seeding_does_not_create_storage(tmp_path: Path) -> None:
    # storage/ is runtime data, never shipped — seeding must not conjure it.
    config.ensure_home_seeded(tmp_path)

    assert not (tmp_path / ".manylogue" / "storage").exists()


# --- layered .env loading ---
#
# load_env writes into os.environ via load_dotenv, which monkeypatch can't see on its
# own. _track registers each var with monkeypatch first (setenv records the original
# absent state, delenv clears it again), so teardown restores a clean environment even
# for values set by the code under test.

def _track(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    for name in names:
        monkeypatch.setenv(name, "__tracked__")
        monkeypatch.delenv(name)


def _write_envs(tmp_path: Path, home_lines: str, cwd_lines: str) -> Path:
    """Lay out <home>/.manylogue/.env and <cwd>/.env; returns the home dir."""
    home = tmp_path / "home"
    (home / ".manylogue").mkdir(parents=True)
    (home / ".manylogue" / ".env").write_text(home_lines, encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / ".env").write_text(cwd_lines, encoding="utf-8")
    return home


def test_load_env_process_env_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = _write_envs(tmp_path, "MLTEST_A=from_home\n", "MLTEST_A=from_cwd\n")
    monkeypatch.chdir(tmp_path / "cwd")
    monkeypatch.setenv("MANYLOGUE_HOME", home.as_posix())
    monkeypatch.setenv("MLTEST_A", "from_process")

    config.load_env()

    assert os.environ["MLTEST_A"] == "from_process"


def test_load_env_home_beats_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = _write_envs(tmp_path, "MLTEST_A=from_home\n", "MLTEST_A=from_cwd\n")
    monkeypatch.chdir(tmp_path / "cwd")
    monkeypatch.setenv("MANYLOGUE_HOME", home.as_posix())
    _track(monkeypatch, "MLTEST_A")

    config.load_env()

    assert os.environ["MLTEST_A"] == "from_home"


def test_load_env_cwd_is_fallback_and_may_set_home(tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    # MANYLOGUE_HOME comes from the launch-dir .env; the home .env it points at is then
    # loaded too, and still outranks the launch-dir file for other vars.
    home = _write_envs(tmp_path, "MLTEST_A=from_home\n", "")
    (tmp_path / "cwd" / ".env").write_text(
        f"MANYLOGUE_HOME={home.as_posix()}\nMLTEST_A=from_cwd\nMLTEST_B=from_cwd\n",
        encoding="utf-8")
    monkeypatch.chdir(tmp_path / "cwd")
    _track(monkeypatch, "MANYLOGUE_HOME", "MLTEST_A", "MLTEST_B")

    config.load_env()

    assert os.environ["MLTEST_A"] == "from_home"   # home wins where both set it
    assert os.environ["MLTEST_B"] == "from_cwd"    # cwd fills the gaps
    assert os.environ["MANYLOGUE_HOME"] == home.as_posix()
