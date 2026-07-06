# Security

**Read this before running Manylogue.** Manylogue is a personal playground project
intended to run locally, by you, for you. It gives frontier coding agents (Claude Code,
Codex) unattended read/write/execute access to parts of your machine. It is not a
hardened product and makes no security guarantees — use it at your own risk.

## What you are opting into

- **Permission prompts are disabled — nothing asks you before an action.** The Claude
  adapter runs with `permission_mode="bypassPermissions"`, and Codex runs equivalently
  unattended. Every action an agent decides to take — editing or deleting files, running
  arbitrary shell commands, installing packages, making network requests — executes
  immediately, with no per-action review. If an agent misunderstands you, hallucinates,
  or gets manipulated, it can do real damage before you notice.
- **Agents act on your real filesystem.** Each chat points agents at a working directory
  of your choice; there is no sandbox, container, or worktree in between (working on the
  live tree is the point of the tool). Anything the underlying CLIs can reach from that
  directory is fair game — including paths outside it, if a command reaches out.
- **Prompt injection is a real vector.** Agents read files in the working directory and
  everything in the chat, including each other's output. Malicious — or just unfortunate —
  content in a repo, dependency, or fetched page can steer an agent into actions you never
  intended.
- **The server is unauthenticated.** It binds to `127.0.0.1` by default and has no auth:
  anyone who can reach the port can drive your agents — and through them, your filesystem
  and your paid subscriptions. Never bind it to a public interface or expose it through a
  tunnel or reverse proxy.

## Sensible precautions

- Point chats only at directories you'd hand to an unattended agent — a scratch clone of
  a repo is a good default; a directory holding secrets or irreplaceable files is not.
- Keep the working directory under version control and commit before long agent sessions,
  so damage is a `git reset` away.
- Keep real secrets in `<home>/.manylogue/.env` (see `.env.example`) or your environment,
  never in committed config. Manylogue itself stores no API keys; adapters inherit auth
  from your installed CLIs.
- If in doubt, run it in a VM or under a dedicated user account.

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories rather than
opening a public issue.
