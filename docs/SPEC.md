# Product specification

## Purpose

Make a terminal pane feel inhabited by a small, beautiful ritual. The card remains visible while the user works elsewhere. Interpretation is available privately, without turning the pane into a chat client.

## First release contract

`arcana` defaults to `arcana 1`. Both `arcana 1` and `arcana 3` open a persistent display. They return only on quit, interruption, or terminal loss. `--once` explicitly selects ordinary printable output. Cards render before any provider is started.

Use all 78 cards by default; `--major` restricts the deck to 22 major arcana. One-card position: “Today.” Three-card positions: “Situation,” “Tension,” “Invitation.” These labels avoid treating the spread as a guaranteed prediction. Other spreads and custom decks come later.

Reversals are enabled by default with independent 50% probability per drawn card; `--upright-only` disables them. Selection is without replacement. Display the orientation in words, including in monochrome and JSON output.

## Daily and seeded behavior

An unseeded single-card invocation retrieves or creates today's local draw. Use the machine's local calendar date and configured timezone, resolved at launch, with an optional `--date YYYY-MM-DD` override. Persist a random per-install identity so separate installations need not receive identical daily cards. Daily identity includes date, timezone, deck version, and reversal policy. Reopening the same identity returns the same draw.

Three-card draws use fresh operating-system randomness by default. `--ritual` asks: “Think of a word. Enter it to weave it into the draw, or press Enter for chance.” Input has no echo. Noninteractive stdin never triggers a prompt; fail clearly if ritual input is requested without a terminal. EOF or Escape cancels before drawing.

A supplied word creates a deterministic seed. Single-card seeded draws incorporate the date; three-card seeded draws do not. Preserve case, normalize Unicode to NFC, and strip leading/trailing whitespace. Do not pass the word in an argument, environment variable, provider prompt, or log. No seed digest is stored: short words can be guessed from hashes. Public JSON output omits seed material; secret-bearing replay export is deferred.

A new date never silently replaces a card already on screen. Show a small “new day available” indicator. `n` explicitly draws for the current day or creates a fresh unseeded spread. Repeating a seeded draw keeps its result; changing the word requires a new ritual. Provider choice, hiding text, resize, and retry never redraw cards.

## Life inside tmux

Default to an alternate-screen interface. Keep artwork visible after interpretation finishes, fails, or times out. Never invoke tmux commands or change pane layout. Compute layout from available terminal cells, handle SIGWINCH, and redraw from state. In a wide pane show three illustrations side by side. In a narrower pane show one full card with `←`/`→` or `j`/`k` navigation and a three-position summary. If height or width cannot contain a complete illustration, use a compact named-card view rather than corrupting art through wrapping.

Color should come from the cards. Surround them with quiet spacing, a restrained title, and one dim help line. Respect `NO_COLOR`, `TERM=dumb`, and unsupported glyphs. Static mode is used for non-TTY output and never waits for input. Reduced-motion behavior is the default; animation is outside v1.

## Divination and privacy

Default provider is `none`. Configuring a provider is authorization to send the selected cards, positions, orientations, and optional explicitly supplied question to that provider. The seed word is never sent. The provider may use a remote service even though Arcana invokes a local CLI.

| Key or option | Behavior |
| --- | --- |
| `d` | Toggle divination; starts hidden, does not redraw or re-request cards |
| `h` | Immediately hide interpretation and any question text |
| `q` / Ctrl-C | Cancel provider process group, restore terminal, exit |
| `r` | Retry interpretation for this exact draw |
| `n` | Explicit new draw; hide text and cancel the previous request first |
| `--private` | Artwork-only session; reveal disabled; skip provider execution |
| `--once` | Print cards and exit; interpretation omitted unless explicitly requested |

Hidden text must not be printed into the terminal before reveal. Store it only in memory. Toggling hide clears and repaints the entire former reading region, including after resize. Status text may say “reading ready,” but must not quote it. Do not render streamed provider tokens while hidden. Every new draw starts hidden.

Alternate-screen rendering keeps the default session out of normal shell scrollback on supported terminals. Hiding cannot retract screenshots, tmux capture history, recordings, or text already observed while revealed. `--private` is the stronger option for those environments. Closing or restarting never restores a previously revealed state.

No journal, question persistence, provider transcripts, or reading cache by default. Daily draw storage contains card IDs and orientation only, plus the nonsecret draw identity. Later explicit save/export must clearly distinguish public card data from question/reading/replay data. Never automatically copy anything to the clipboard.

## Interpretation voice

One card: 60–100 words. Three cards: 120–180 words. Name each card and its orientation, relate the positions, and end with one useful reflective question. Warm, spare, specific prose. No fatalism, certainty, inflated mysticism, or claims to know what another person thinks. Reversal can suggest inwardness, delay, excess, or resistance rather than simple misfortune. These are reflection prompts, not instructions to make consequential decisions.

The draw is authoritative; the model cannot select or replace cards. Provider failure shows a short generic status and leaves local card meanings available when revealed. Raw CLI errors and terminal escapes never appear in the display.

## Scope boundaries

V1 excludes chat, cloud sync, scheduling, notifications, accounts, a journal UI, audio, animated dealing, custom spreads, direct model APIs, automatic provider discovery, and an always-running background service. A provider subprocess is asynchronous within the app, and is cancelled when the app closes.

Release requires all acceptance checks in PLAN.md, including a visually verified reversed deck and privacy behavior inside tmux.
