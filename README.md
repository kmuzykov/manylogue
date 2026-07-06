# Manylogue

Human-chaired, multi-agent group chat. Several AI agents — Claude and Codex today —
converse with each other and with you in one room, streaming their
intermediate work (narration, tool calls) live and committing one final answer per turn.
The point is to make multi-agent collaboration *legible*: you see who is thinking, what
they are doing, and how the conversation settles, instead of black-box orchestration.

It's a FastAPI app: you chair the thread, and each agent's adapter responds in turn
against a project working directory you choose. The transcript is plain JSONL on disk —
readable, diffable, and durable across restarts.

> [!warning]
> Manylogue is a personal project meant to run locally, and it runs agents with their
> permission prompts disabled. Read [Security](#security) before pointing it at anything
> you care about.

## Install & run

Requires Python 3.12+, plus the [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
and/or [Codex](https://developers.openai.com/codex/cli) CLI, installed and authenticated.
Manylogue drives the agents through the official SDKs, so it reuses your subscription
auth — no API keys live in Manylogue. See [Agent parity & skills](#agent-parity--skills).

**Option 1 — no clone**, with [uv](https://docs.astral.sh/uv/):

```
uvx --prerelease allow manylogue        # serves http://127.0.0.1:8000
```

The flag is needed because the Codex SDK is still in beta and pins a pre-release
runtime, which uv won't resolve from an index without an explicit opt-in. It goes
away once the SDK ships a stable release.

Or with pip — no flags needed:

```
pip install manylogue
manylogue
```

**Option 2 — from source:**

```
git clone https://github.com/kmuzykov/manylogue
cd manylogue
uv sync
uv run manylogue
```

Open the URL, create a chat (pick a project directory the agents may work in), add
participants, and send a message. Stop and restart any time — chats and per-agent state
persist.

`manylogue` accepts `--home <dir>`, `--host`, and `--port`.

## Security

Manylogue is a personal playground project, shared because it's useful — not a hardened
product. Run it only if you're comfortable with all of the following:

- **Agents run with permission prompts disabled.** The Claude adapter uses
  `permission_mode="bypassPermissions"`: every file edit and command an agent decides to
  run is auto-approved, with no per-action review. Codex runs equivalently unattended.
- **Agents act on your real filesystem.** They read, write, and run tools in the working
  directory you point a chat at — no sandbox, no worktree, by design. Point chats only at
  directories you trust the agents to operate in (a scratch clone is a good start).
- **Localhost only.** The server binds to `127.0.0.1` and has no authentication. Do not
  expose it to a network or the public internet.

See [SECURITY.md](SECURITY.md) for the full risk model, sensible precautions, and
vulnerability reporting.

## Configuration

Manylogue keeps its config and chat history under `<home>/.manylogue/`, where `<home>`
defaults to your OS user home (so `~/.manylogue`). Point `MANYLOGUE_HOME` elsewhere — or
pass `manylogue --home <dir>` — to relocate it. On first run Manylogue seeds the
config with the bundled default agents and roles; edit them in place, your changes are
never overwritten.

Layout under `<home>/.manylogue/`:

- `agents/*.toml` — agent definitions (adapter, model, role, description)
- `roles/*.md` — role prompts referenced by agents
- `storage/chats/` — chat history; never seeded or touched by updates
- `.env` — optional settings and secrets (see `.env.example`)

Environment variables are read with this precedence (first setter wins):

1. the process environment
2. `<home>/.manylogue/.env` — the place for secrets
3. `./.env` in the directory you launch from — dev fallback; may set `MANYLOGUE_HOME`

Set `MANYLOGUE_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`; defaults to `DEBUG`) to
control log verbosity.

## Capabilities & limitations

- **Claude and Codex** run through their subscription CLIs/SDKs, so agents inherit the real
  Claude Code / Codex runtime — their tools, instruction-file discovery, and (for Claude)
  skills — from your local install. With no local CLI the SDKs fall back to API-key billing
  with default built-in tools and none of your MCP servers; that fallback path is not yet
  verified.
- **An OpenAI-compatible adapter exists (e.g. local models via Ollama) but is
  conversation-only today** — no file read/write/search tools, so local models participate
  as talkers, not actors. Making them first-class participants is on the roadmap.

## Troubleshooting

**Claude turns fail with `401 Invalid authentication credentials` (or "Please run /login").**
Manylogue's Claude adapter authenticates with your Claude subscription login, so test it
directly from a terminal:

```
claude -p "say ok"
```

If that prints `OK`, Claude is authenticated and Manylogue will work. If it returns a 401,
your login has expired — run `claude logout`, then `claude login`, then restart Manylogue so
it picks up the refreshed credential.

## Agent parity & skills

The contract both adapters aim for: an agent's turn should behave like a fresh CLI
session (`claude` / `codex`) opened in the chat's project directory. Instruction files
(`CLAUDE.md` / `AGENTS.md`), tools, MCP servers, and skills are inherited from your local
CLI setup, not configured in Manylogue — so if something works in your terminal, it
should work in the room.

Two discrepancies we hit in practice, and what solved them at the time (as of July 2026 —
SDK and CLI behavior moves fast, so verify against current docs if something looks off):

- **Claude's document skills (DOCX / PDF / PPTX / XLSX) were missing.** Claude Desktop
  had installed them into a GUI-only store that neither the terminal CLI nor SDK-driven
  sessions like Manylogue's could read. Installing them as a CLI plugin fixed it:

  ```
  claude plugin marketplace add anthropics/skills
  claude plugin install document-skills@anthropic-agent-skills
  ```

  Note these skills shell out to Python libraries and LibreOffice (`soffice`) at
  execution time — they need those installed to actually produce documents.

- **Claude agents lacked newer built-in skills.** The `claude` binary bundled with the
  Agent SDK lagged the installed CLI; pointing the adapter at the standalone binary via
  `ClaudeAgentOptions(cli_path=...)` fixed that.
