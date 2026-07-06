# Product

## Register

product

## Users

Primary audience: developers who run several AI coding agents at once and live in
best-in-class harness tools — people fluent in Claude Desktop, Codex, OpenCode, and similar.
This is a discerning, category-native audience that judges a tool as much on taste and
execution as on function, so the bar is earned credibility with people who already know what
good looks like. Secondary user: the author, as an early daily driver.

Context of use: at a desk, focused, running several AI coding agents in one conversation
and watching them work. Keyboard-first, long sessions, information-dense but not noisy.

## Product Purpose

Manylogue is a multi-agent group chat: several AI agents (Claude, Codex, others) converse with
each other and a human in one room, streaming their intermediate work (narration, tool
calls) live and committing one final answer per turn. It exists to make multi-agent
collaboration *legible* — you can see who is thinking, what they are doing, and how the
conversation settles — instead of black-box orchestration. Success looks like a developer
fluent in these tools opening it and immediately trusting it — reading it as a well-built,
tasteful tool made by people who understand both agents and interface craft.

## Brand Personality

Developer-native and calm, elevated by restraint. Familiar to anyone who lives in
terminal-adjacent agent tools (Claude Desktop, Codex, OpenCode, OpenClaw), but more elegant:
concise, minimalistic, quietly stylish. Three words: precise, composed, crafted. It should
feel like a tool made by someone with taste — confident enough to leave things out.

## Anti-references

- **Generic SaaS dashboard** — card grids, gradient accents, hero-metric blocks, the b2b
  template look.
- **Enterprise IDE** — overwhelming panels, dense toolbars, settings sprawl, chrome
  everywhere.
- Consumer-chatbot emptiness (one giant input, acres of whitespace) and Slack/Discord
  chrome-heaviness are off-brand too, but the two above are the hard nos.

## Design Principles

1. **Master the idiom, then sign it.** Own the harness-tool convention (dark,
   monospace-aware, keyboard-first), then add one or two deliberate signature moves.
   Convention is the foundation; restraint plus a little voice is what reads as "skilled"
   rather than generic.
2. **Legibility of the multi-agent state is the product.** The core value is seeing who is
   active, what they are doing, and how a turn resolves. Every design decision serves that
   clarity first.
3. **Concise over complete.** Leave things out. Density without noise; every element earns
   its place. When in doubt, remove.
4. **Calm under streaming.** The interface updates constantly as agents work. Motion and
   layout must stay composed, never jumpy or attention-grabbing, so long sessions feel
   steady.
5. **Finish is the differentiator.** The audience is fluent in the best tools in this
   category, so the last 10% (spacing rhythm, type hierarchy, states, micro-interactions) is
   not optional polish — it is what separates this from a generic dev tool.

## Accessibility & Inclusion

WCAG AA contrast as the floor (body text ≥ 4.5:1, large/bold text ≥ 3:1; placeholders held
to the same body bar). Respect `prefers-reduced-motion` with crossfade or instant fallbacks
for all streaming and reveal animation. Keyboard-first operation, since the audience expects
it. Dark theme as default; keep accent and state colors distinguishable under common
color-vision deficiencies.
