<div align="center">

# ✧ terminal tarot ✧

**Daily cards and three-card readings, in your terminal.**

[![Checks](https://github.com/vlrie/terminal-tarot/actions/workflows/check.yml/badge.svg)](https://github.com/vlrie/terminal-tarot/actions/workflows/check.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-9989b4)](pyproject.toml)
[![Original code: MIT](https://img.shields.io/badge/original_code-MIT-c6b5ce)](LICENSE)

</div>

**Arcana** is a terminal tarot app for a card of the day or a three-card spread. Built around the tarot art in [arttime](https://github.com/poetaman/arttime), it stays in a tmux pane with centered cards, inverse artwork, and a resizing moon-and-star border.

Readings work offline, with optional background divination from Claude Code, Codex CLI, or another configured CLI. Keep the cards visible and show or hide the interpretation when you want to. The command is `arcana`.

<p align="center">
  <img src="docs/screenshots/three-cards.png" width="560" alt="The Fool, Six of Wands, and reversed Tower centered inside Arcana’s resizing moon-and-star frame, with divination hidden">
</p>

*The Fool · Six of Wands · The Tower, reversed. Divination is hidden by default.*

## Features

| Feature | Details |
| --- | --- |
| **Card of the day** | A locally saved daily draw, stable when you reopen it. |
| **Three-card spreads** | Situation → Tension → Invitation, drawn without replacement. |
| **Word-seeded draws** | `--ritual` privately asks for a word to seed either a one-card or three-card draw. The word is never sent to an AI provider. |
| **All 78 cards** | Major and minor arcana, with a major-only option. |
| **Inverse cards** | The illustration rotates; external labels stay readable, and the interpretation accounts for the reversal. |
| **Persistent display** | Leave it in a tmux pane. Cards, readings, and the mystical frame adapt as you resize. |
| **Joint readings** | Three cards read together, followed by a small optional ritual and a reflective question. |
| **Optional AI** | Offline reflections, or background requests to Claude Code, Codex CLI, or another configured CLI. |
| **Show/hide controls** | Reveal/hide with `d`, hide immediately with `h`, or use artwork-only `--private` mode. |
| **No runtime dependencies** | Python standard library only at runtime. No account, database, daemon, or web server. |

## Getting started

Requires **Python 3.12+**, [uv](https://docs.astral.sh/uv/), and Linux. Install [arttime](https://github.com/poetaman/arttime#installation) for the illustrated deck. Without it, Arcana still works with named cards and original reflections.

```sh
git clone https://github.com/vlrie/terminal-tarot.git
cd terminal-tarot
uv tool install .

arcana 1
```

Or run `./arcana 1` directly from the checkout without installing the package. That launcher uses `uv`; it downloads no runtime dependencies.

Use a UTF-8 terminal with truecolor and Unicode Symbols for Legacy Computing support. A dark background suits the deck. If your arttime installation is elsewhere:

```sh
arcana 3 --art-dir /path/to/arttime/textart
```

## Drawing cards

```sh
arcana 1                         # card of the day
arcana 1 --ritual                # privately enter a word for today's draw
arcana 3                         # situation · tension · invitation
arcana 3 --ritual                # a repeatable word-seeded spread
arcana 3 --major                 # only the 22 major arcana
arcana 1 --upright-only          # omit reversals
arcana 1 --private               # artwork only; no provider or reveal
arcana 1 --once                  # print the draw and exit
arcana 3 --json                  # public card data for scripts
```

The same word and deck version reproduce the same spread. For `arcana 1`, the date is part of the seed; for `arcana 3`, it isn't. The word is not echoed or saved. Leave it empty for an unseeded draw: daily cards stay the same that day, while three-card spreads are fresh each time.

Open a tmux split, run Arcana, and leave it there. It never rearranges your panes or silently replaces a card at midnight. Artwork shrinks to fit and returns to its original detail on expansion. Readings move beside the spread in wide panes and below it in narrower ones.

<details>
<summary>Card of the day</summary>

![The reversed Chariot as a daily card, centered inside Arcana’s frame](docs/screenshots/daily-card.png)

*The Chariot, reversed, on 2026-10-20. The border and illustration follow the pane size.*

</details>

| Key | Action |
| --- | --- |
| `d` | Reveal or hide the reading |
| `h` | Hide private text immediately |
| `j` / `k`, `→` / `←` | Browse cards when the pane is very narrow |
| `↑` / `↓` | Scroll a revealed reading |
| `r` | Retry the reading for the same cards |
| `n` | Draw again, respecting daily and seeded rules |
| `q`, Ctrl-C | Quit and cancel any background request |

## Readings and divination

Press `d` for a built-in offline reading. Every minor card has its own upright and reversed meaning, and three-card readings connect the spread as a whole, including shared suits and contrasts.

![The same three-card spread with its joined offline reading revealed below the cards](docs/screenshots/joint-reading.png)

*Press `d` to reveal the joined reading; scroll with `↑` / `↓` to reach the ritual and question. This screenshot shows the built-in offline reflection.*

To use an already authenticated CLI:

```sh
arcana 1 --provider claude
arcana 3 --ritual --provider codex
arcana 3 --provider claude --question   # privately prompt for a question
arcana 1 --once --interpret            # explicitly print an offline reflection
```

The cards appear first. The request runs in the background and its answer stays hidden. Resizing, browsing, and toggling visibility never request another reading. If the provider fails, your cards and offline reflection remain available. AI prose may vary even when the draw is reproducible.

Providers receive the cards, positions, orientations, original reflection prompts, and any question you explicitly enter. **They never receive the seed word.** A CLI running locally may still use a remote model service.

## Privacy

- `--private` never starts a provider and disables revealing interpretation.
- Words, questions, and readings are not saved by Arcana. Hidden readings are not printed before reveal.
- Hiding cannot retract screenshots, tmux capture history, or recordings of previously revealed text.
- Daily state contains a random install identity and public card draws, stored locally with user-only permissions.
- `--no-color` keeps the frame and artwork monochrome.

<details>
<summary>Configuration and other CLI providers</summary>

On Linux, use `~/.config/arcana/config.toml` (respects `XDG_CONFIG_HOME`), or pass `--config PATH`. CLI flags take precedence.

```toml
provider = "claude"       # none, claude, codex, custom
# art_dir = "/path/to/arttime/textart"
# timezone = "Asia/Dubai"
timeout = 45
```

For another CLI, supply an argument array:

```toml
provider = "custom"
argv = ["my-reading-cli", "--plain"]
timeout = 60
```

The command reads a UTF-8 prompt from stdin and writes the answer to stdout. It runs in an empty temporary directory. Use absolute paths for scripts outside `PATH`. Custom commands are trusted configuration and are responsible for their own tools, records, and privacy.

The named adapters were checked against Claude Code 2.1.302 and Codex CLI 0.163.0 help. Claude uses tools disabled, safe mode, no MCP servers, and no session persistence. Codex uses an ephemeral read-only session with user config/rules skipped, web search disabled, and the shell-tool feature disabled. These settings constrain agent behavior; they are not an OS sandbox for the provider itself. Live authenticated responses depend on your CLI version and account.

Linux state defaults to `~/.local/share/arcana/` (respects `XDG_DATA_HOME`). Override it with `--data-dir PATH`. `--date YYYY-MM-DD` and `--timezone IANA/Zone` make the daily identity explicit.

Linux is tested. macOS paths and POSIX terminal handling are implemented, but still need an on-device smoke test. Native Windows is unsupported.

</details>

## Development

```sh
PYTHONPATH=src uv run --no-project python -m unittest discover -s tests -v
uv build

# Startup, rendering, and terminal-output measurements
PYTHONPATH=src uv run --no-project python benchmarks/benchmark.py
```

The suite covers deterministic draws, concurrent daily state, all locally available artwork, resizing and centering, privacy, hidden input, provider failure/cancellation, and actual terminal interaction through pseudo-terminals. Runtime dependencies: none.

[Specification](docs/SPEC.md) · [Architecture](docs/ARCHITECTURE.md) · [Verification](docs/VERIFICATION.md) · [Performance](docs/PERFORMANCE.md) · [Screenshot notes](docs/screenshots/README.md)

## Credits

The tarot art comes from **[arttime](https://github.com/poetaman/arttime)**, authored and maintained by **Aman Mehra**, and the individual artists whose work it collects. Thank you for making this collection available. Arcana is an independent companion app, with no affiliation or endorsement.

The original Arcana code and prose use the [MIT license](LICENSE). The deck is loaded from an existing arttime installation; upstream code and deck files are not bundled. Screenshots show selected upstream artwork for this personal, noncommercial project; those illustrations retain their own rights and are excluded from Arcana's MIT grant. See [credits, artwork terms, and preserved notices](CREDITS.md).
