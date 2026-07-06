---
name: Manylogue
description: A multi-agent group chat where AI agents and a human think out loud together.
colors:
  canvas: "#0d1117"
  surface: "#161b22"
  surface-raised: "#21262d"
  code-surface: "#282a36"
  border: "#30363d"
  ink: "#c9d1d9"
  ink-muted: "#8b949e"
  ink-strong: "#f0f6fc"
  accent: "#58a6ff"
  identity-amber: "#e3b341"
  identity-green: "#6cc26c"
  identity-purple: "#d2a8ff"
  identity-teal: "#56d4dd"
  identity-orange: "#ffa657"
  identity-pink: "#f778ba"
typography:
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Inter, 'Helvetica Neue', sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.6
  heading:
    fontSize: "1.3em"
    fontWeight: 600
    lineHeight: 1.25
  mono:
    fontFamily: "ui-monospace, 'SF Mono', 'Cascadia Code', 'JetBrains Mono', Menlo, Consolas, monospace"
    fontSize: "0.875em"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontSize: "0.85em"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
components:
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "12px"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
---

# Design System: Manylogue

## 1. Overview

**Creative North Star: "The Quiet Control Room"**

Manylogue is a room where several minds work at once and you watch the conversation settle.
Many agents are active, but the space stays calm: muted ink on a near-black canvas, surfaces
that recede, a single blue that lights up only what matters right now. It belongs to the
lineage of terminal-adjacent agent tools (Claude Desktop, Codex, OpenCode) and should feel
immediately familiar to anyone who lives in them — then earn a second look through restraint
and finish, not through decoration.

The system is **flat and tonal**. Depth is built from three steps of near-black
(canvas → surface → raised), never from shadow. Type is a single system sans for all UI, with
mono reserved for code and machine identifiers. The accent is rare by doctrine. Information is
dense where it must be (a live multi-agent transcript), quiet everywhere else. The interface's
job is to make the multi-agent state legible — who is thinking, what they are doing, how a
turn resolves — and then disappear into that task.

This system explicitly rejects the **generic SaaS dashboard** (card grids, gradient accents,
hero-metric blocks) and the **enterprise IDE** (overwhelming panels, dense toolbars, settings
sprawl). It is not a metrics console and not a cockpit. It is a reading-room-quiet space for
watching agents collaborate.

**Key Characteristics:**
- Near-black canvas, three-step tonal depth, zero shadows at rest.
- One system-sans family; mono only for code and agent/tool identifiers.
- A single blue interaction accent (≤10% of any screen), plus muted per-agent identity hues confined to avatars.
- Calm under constant streaming: nothing jumps, nothing shouts.
- Keyboard-first, desktop-dense, uncompromising finish.

## 2. Colors

A near-monochrome dark palette — nine steps of blue-grey from near-black to near-white — lit
by exactly one blue accent.

### Primary
- **Signal Blue** (`#58a6ff`): The only chromatic color in the system. Reserved for primary
  actions (the Send button), input focus, current selection, links, and live-state
  indicators. Its rarity is the entire point — see the One Voice Rule below.

### Neutral
- **Canvas** (`#0d1117`): The page background and the deepest layer. Also the text color *on*
  the accent button (dark-on-blue), and the textarea fill.
- **Surface** (`#161b22`): Panels — the chat list, transcript, participants, and input
  shell. One tonal step up from canvas; this is how a panel reads as "raised" without a
  border doing all the work.
- **Surface Raised** (`#21262d`): Table headers and the next step of elevation. Doubles as the
  muted divider color (`border-muted`) for the faintest internal separators.
- **Code Surface** (`#282a36`): Fenced code-block background (Dracula's base), the one place
  the palette borrows an outside system, kept deliberate and contained.
- **Hairline** (`#30363d`): The default 1px border on every panel, input, table cell, and
  divider. The structural line of the whole UI.
- **Ink** (`#c9d1d9`): Body text. Sits at ~9:1 on canvas — comfortably past AA.
- **Ink Muted** (`#8b949e`): Secondary text — timestamps, placeholders, the sidebar, the "is
  working…" stream. Verify it clears 4.5:1 on whatever surface it lands on; on `surface` it is
  borderline for small text, so do not push it onto lighter fills.
- **Ink Strong** (`#f0f6fc`): Headings, author names, strong emphasis. The near-white top of
  the ramp, used sparingly for the few things that should read as loudest.

### Identity hues (the One Voice exception)
Multi-agent legibility is the product, so each agent carries a stable identity color, assigned
by hashing its name into a muted, dark-friendly palette (amber / green / purple / teal /
orange / pink — chosen to dodge accent-blue and error-red). Human is neutral. This is the
**single sanctioned exception** to the One Voice Rule, and it is confined to one place: the
30px avatar chip. It never spreads to text, borders, or fills.

### Named Rules
**The One Voice Rule.** Signal Blue is the only *interaction* chroma — primary action, focus,
current selection, live state — and appears on ≤10% of any screen. If two things are blue, one
is wrong. The lone exception is the per-agent identity hue, confined to avatars: it encodes
*who*, never *act-here*. Keep the two channels separate — identity lives in avatars, Signal
Blue lives in interaction/live.

**The Token-Only Rule.** Every color is a token — a neutral, the accent, or an identity hue.
Raw hex in a component is a defect, not a shade. One sanctioned exception remains: `#f8f8f2` as
the Dracula code foreground, which belongs to the imported highlight theme.

## 3. Typography

**Body / UI Font:** System sans (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
Inter, "Helvetica Neue", sans-serif`)
**Code / Identifier Font:** System mono (`ui-monospace, "SF Mono", "Cascadia Code",
"JetBrains Mono", Menlo, Consolas, monospace`)

**Character:** Native, neutral, invisible. The system font means Manylogue looks like it belongs
on the machine it runs on rather than like a branded web app — the right move for a developer
tool. Personality comes from spacing, weight, and restraint, not from a typeface with a voice.

### Hierarchy
- **Author** (600, 0.95rem): The name heading each committed message, paired with the identity
  avatar. Held at body scale on purpose — the avatar carries identity, so the name stays quiet.
- **Heading** (600, 1.15em–1.5em, 1.25): Markdown headings inside message bodies, in
  Ink Strong. A tight 1.15–1.3 step ratio keeps the scale calm.
- **Body** (400, 15px, 1.6): All prose and UI text, in Ink. Cap reading prose at ~70ch;
  transcript content may run denser.
- **Mono** (400, 0.875em, 1.5): Code, inline code, and machine identifiers only.
- **Label** (400, 0.85em, 1.4): Timestamps, sidebar entries, the agent-stream lines — the
  quiet supporting text, in Ink Muted.

### Named Rules
**The Mono-Means-Machine Rule.** Monospace signals "this is literal machine output" — code,
tool names, identifiers. Never use it for chrome or prose to look "technical"; the sans
already carries that.

## 4. Elevation

The system is **flat**. There is not a single `box-shadow` in the stylesheet, and that is
correct. Depth is expressed tonally: canvas (`#0d1117`) → surface (`#161b22`) → surface-raised
(`#21262d`), each one step lighter, each panel outlined by a 1px Hairline border. A surface
reads as "above" the canvas because it is lighter and bordered, not because it floats.

### Named Rules
**The Flat Room Rule.** Surfaces are flat at rest. Depth is tonal, never a shadow. The only
license to introduce a shadow is a genuinely floating layer that escapes the document flow — a
chat-switcher dropdown, a new-chat dialog — and then it is one restrained, soft shadow, used as
a response to that elevation, never as ambient decoration.

## 5. Components

### Panels / Containers
- **Character:** Quiet frames, not cards. They organize the screen; they never stack or
  decorate.
- **Shape:** 8px radius (`{rounded.lg}`).
- **Background / Border:** Surface (`#161b22`) with a 1px Hairline (`#30363d`) border.
- **Padding:** 12px.
- **Rule:** These are structural regions (chat list, transcript, participants, input shell),
  not a repeatable card component. Never nest one panel inside another, and never multiply them
  into a card grid.

### Buttons
- **Shape:** 6px radius (`{rounded.md}`).
- **Primary** (the only button today): Signal Blue fill, Canvas (dark) text, 600 weight,
  `10px 20px` padding. Dark-on-blue, not white-on-blue.
- **Hover:** `filter: brightness(1.1)`. Functional, instant.
- **Focus:** A 2px Signal-Blue `:focus-visible` outline (2px offset), shared by every
  interactive element — the audience is keyboard-first.
- **Secondary / Ghost:** Not yet defined. When needed, use a transparent fill with a Hairline
  border and Ink text, so the primary stays the only filled, only blue button on screen.

### Inputs / Fields
- **Style:** Canvas (`#0d1117`) fill — recessed below its surrounding Surface panel — 1px
  Hairline border, 6px radius, `10px 12px` padding. The composer is a vertically resizable
  textarea, min-height 80px.
- **Focus:** Border shifts to Signal Blue, plus the shared 2px `:focus-visible` ring. No glow.
- **Placeholder:** Ink Muted.

### Navigation (chat list)
- **Character:** A quiet vertical list in the left Surface panel — the room switcher. Calm, not
  a loud nav rail.
- **Treatment:** Entries read in the neutral ramp at rest (Ink / Ink Muted), reserving Signal
  Blue for the *current* room only. Truncate long names with ellipsis; never let an entry
  wrap or overflow its 200px column. Hover lifts the row one tonal step (toward
  surface-raised), not into color.

### Identity Avatar (signature)
- **Character:** A 30px rounded-square chip (rounded-square = tool, not a consumer-chat circle)
  holding a 2-letter monogram in mono (so `Claude` ≠ `Codex`). Every author — human and agent —
  gets one, in the transcript, the roster, and the live agent-stream.
- **Color:** A 14% tint of the author's identity hue over Surface Raised, a 26%-hue border, the
  initial in the hue. Human is neutral (Ink Muted). This is the only place an identity hue shows.
- **Why:** The cheapest way to make a multi-agent transcript scannable — you track *who* by
  color + monogram, not by reading every name.

### Chat header
- **Character:** A fixed header atop the transcript column with the chat name (Ink Strong, 1rem,
  600), divided from the messages by a 1px muted hairline. The transcript scrolls beneath it;
  the live agent-stream is a pinned tray at the bottom of the column.

### Messages (signature)
- **Character:** The committed transcript. Each message is an envelope: an identity avatar
  beside a main column (Author + timestamp header over a markdown body), divided from the next
  by a 1px muted hairline — never a card, never a bubble.
- **Author:** Ink Strong, 600, body scale (0.95rem), preceded by the identity avatar.
- **Timestamp:** Ink Muted, 0.8em, baseline-aligned opposite the author.
- **Body:** Full markdown — headings, code, tables, blockquotes, footnotes — all rendered in
  the neutral ramp with Signal Blue links.

### Agent Stream (signature)
- **Character:** The ephemeral "thinking out loud" layer — a per-author block of live narration
  and tool calls that appears while an agent works and is dropped when its turn commits. This
  is the most Manylogue-specific component in the system.
- **Treatment:** A faint blue-tinted card (6% accent over Surface, a 22%-accent Hairline) —
  *live*, not loud. The header is the author's avatar + name with a pulsing Signal-Blue dot
  ("live now"); work lines are mono, Ink Muted, with a 🔧 prefix on tool calls. The same pulse
  lights that agent's roster row, so presence reads in two places at once. It stays quieter than
  committed messages so the eye separates "still happening" from "settled."

## 6. Do's and Don'ts

### Do:
- **Do** build surfaces as flat panels: Surface fill (`#161b22`), 1px Hairline (`#30363d`),
  8px radius. Depth is the canvas→surface→raised tonal step, never a shadow (the Flat Room
  Rule).
- **Do** reserve Signal Blue (`#58a6ff`) for primary action, focus, current selection, and
  live state — ≤10% of any screen (the One Voice Rule).
- **Do** keep one system-sans family for all UI; use mono only for code and machine
  identifiers (the Mono-Means-Machine Rule).
- **Do** give every interactive element a visible `:focus-visible` state — buttons, inputs,
  and chat-list entries. The audience navigates by keyboard.
- **Do** keep motion to 150–250ms state transitions, and pair every animation with a
  `prefers-reduced-motion` fallback — critical because the transcript is always streaming.
- **Do** make ephemeral agent output read as quieter and more provisional than committed
  messages.
- **Do** carry agent identity in the avatar hue only; keep Signal Blue for interaction/live so
  the two color channels never collide.

### Don't:
- **Don't** use side-stripe borders — a `border-left` (or right) thicker than 1px as a colored
  accent. (The old `.agent-stream-item` stripe was the violation; it's now a full-bordered tonal
  card.) Use full borders or a background tint.
- **Don't** drift toward a **generic SaaS dashboard**: no card grids, no gradient accents, no
  hero-metric blocks.
- **Don't** drift toward an **enterprise IDE**: no overwhelming panels, dense toolbars, or
  settings sprawl.
- **Don't** introduce gradient text (`background-clip: text`) or glassmorphism. This palette is
  flat and solid by doctrine.
- **Don't** hardcode color outside the tokens (neutrals, accent, identity hues). The `#ccc`
  stray is gone; `#f8f8f2` in `pre code` is the one sanctioned exception (Dracula's foreground,
  from the imported highlight theme).
- **Don't** let one non-content element shout. (The 32px Author is resolved — it now sits at
  body scale, with the avatar carrying identity.) Keep any single element from breaking the calm.
- **Don't** let chat-list names overflow or wrap; truncate with ellipsis inside the fixed
  column.
