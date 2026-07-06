# Manylogue — Workspace Instructions

See [`README.md`](README.md) for what Manylogue is, how to run it, and the adapter/skill
parity notes. Keep the two in their lanes: the README is for users of the public repo,
this file is for agents working on the code — link to the README rather than duplicating
it here.

## Tools

- **Type check**: `uv run pyright`. Strict mode via `[tool.pyright]` in `pyproject.toml`.
  CLI output matches the in-editor Pylance warnings — same engine. Run after non-trivial
  code changes.
- **Tests**: `uv run pytest`. Includes a packaging tripwire
  (`tests/test_wheel_contents.py`) that builds the wheel/sdist and fails on any
  non-allowlisted file — extend its allowlist when adding new package data; never delete
  the test.
- **Run**: `uv run manylogue` (single-command CLI — there is no `run` subcommand).
  `fastapi dev` autoreload is unreliable on Windows; restart instead.
- **While Manylogue is running**, its launched `manylogue.exe` is locked, so `uv sync`
  (including the implicit sync in `uv run`) fails with os error 32. Use
  `uv run --no-sync ...` and do a real `uv sync` after the app stops.
