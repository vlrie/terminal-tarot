<div align="center">

# ✧ terminal tarot ✧

**a little tarot app for a tmux pane.**

[![Checks](https://github.com/vlrie/terminal-tarot/actions/workflows/check.yml/badge.svg)](https://github.com/vlrie/terminal-tarot/actions/workflows/check.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-9989b4)](pyproject.toml)
[![Original code: MIT](https://img.shields.io/badge/original_code-MIT-c6b5ce)](LICENSE)

</div>

so, [arttime](https://github.com/poetaman/arttime) has tarot cards as terminal art. I wanted a mini app that could pull a card of the day or a 3-card spread and just stay on screen. With inverse cards, a border that looks a bit mystical, and optional divination from claude/codex/whatever is plugged in.

The command is `arcana`.

<p align="center">
  <img src="docs/screenshots/three-cards.png" width="560" alt="The Fool, Six of Wands, and reversed Tower centered inside Arcana’s resizing moon-and-star frame, with divination hidden">
</p>

*The Fool, Six of Wands, and The Tower reversed. Divination is hidden here.*

## what's in here

| | |
| --- | --- |
| **Card of the day** | Pull it again that day and you get the same card. |
| **3-card spread** | Situation → Tension → Invitation. No duplicate cards. |
| **A word to seed the draw** | `--ritual` asks for a word, without showing what you type. Works for both 1 and 3 cards. |
| **All 78 cards** | Major and minor arcana. `--major` if you only want the major ones. |
| **Inverse cards** | The art actually rotates. The labels stay readable, and the interpretation accounts for the reversal. |
| **It stays on screen** | Leave it in a tmux pane. Resize it; the cards and border follow. |
| **A joint reading** | The 3 cards get read together, with a small optional ritual and a question to think about. |
| **Optional AI** | Local readings work without it. Claude Code, Codex CLI, or a custom CLI can do the divination in the background. |
| **Show/hide** | `d` toggles the reading. `h` hides it immediately. `--private` keeps it to artwork only. |
| **Small app** | Python standard library at runtime. No account, database, daemon, or web server. |

## get it running

You need **Python 3.12+**, [uv](https://docs.astral.sh/uv/), and Linux. Install [arttime](https://github.com/poetaman/arttime#installation) for the card art. Without it, you still get card names and local readings.

```sh
git clone https://github.com/vlrie/terminal-tarot.git
cd terminal-tarot
uv tool install .

arcana 1
```

You can also run `./arcana 1` from the repo without installing the package. The launcher uses `uv`; there are no runtime dependencies to download.

The art wants a UTF-8 terminal with truecolor and a font that supports Unicode Symbols for Legacy Computing. If the cards look odd, check the font. A dark background helps too.

If your arttime files live somewhere else:

```sh
arcana 3 --art-dir /path/to/arttime/textart
```

## pull some cards

```sh
arcana 1                         # card of the day
arcana 1 --ritual                # ask for a word to seed today's card
arcana 3                         # 3-card spread
arcana 3 --ritual                # same idea, with a word
arcana 3 --major                 # major arcana only
arcana 1 --upright-only          # no inverse cards
arcana 1 --private               # just the art, no divination
arcana 1 --once                  # print it and exit
arcana 3 --json                  # card data for scripts
```

The seed word isn't echoed or saved, and it doesn't go to the AI. Same word and deck version give you the same spread. For `arcana 1`, the date is part of the seed too. For `arcana 3`, it isn't.

Leave the word empty for an unseeded draw. The daily card still stays the same for that day; a 3-card spread is fresh each time.

Open a tmux split and leave it there. The app won't move your panes or swap your card at midnight. Cards shrink to fit, and the reading moves beside or below them depending on the space. Very narrow panes let you browse one card at a time.

<details>
<summary>the daily card looks like this</summary>

![The reversed Chariot as a daily card, centered inside Arcana’s frame](docs/screenshots/daily-card.png)

*The Chariot, reversed. 2026-10-20.*

</details>

| Key | What it does |
| --- | --- |
| `d` | Show/hide the divination |
| `h` | Hide it immediately |
| `j` / `k`, `→` / `←` | Move between cards in a narrow pane |
| `↑` / `↓` | Scroll the reading |
| `r` | Ask for another reading of the same cards |
| `n` | Draw again; daily and seeded rules still apply |
| `q`, Ctrl-C | Quit and cancel the background request |

## the divination bit

Press `d` for the built-in local reading. Every minor card has its own upright and reversed meaning. A 3-card reading also looks at the suits and how the cards relate to each other.

The reading has a thread, a small optional ritual, and a question to carry. The ritual is something ordinary you can try; no shopping list or special objects required.

![The same three-card spread with its joined offline reading revealed below the cards](docs/screenshots/joint-reading.png)

*This is the local reading. Scroll with `↑` / `↓` for the rest, or `h` when you want it out of sight.*

For an AI reading, use a CLI you're already logged into:

```sh
arcana 1 --provider claude
arcana 3 --ritual --provider codex
arcana 3 --provider claude --question   # asks for a question, also hidden as you type
arcana 1 --once --interpret            # print the local reading and exit
```

Cards show up first; the request runs in the background. The answer stays hidden until you reveal it. Resizing or hiding/showing it doesn't send another request. If the provider fails, you still have your cards and local reading.

The provider gets the cards, their positions and orientations, reflection prompts, and a question if you entered one. **It never gets your seed word.** Running a CLI locally doesn't mean the model is local; it may send the request to its service.

The draw is repeatable. The AI's wording might not be.

## privacy

- `--private` doesn't start a provider and doesn't let you reveal a reading. Just cards.
- Arcana doesn't save words, questions, or readings. Hidden readings aren't printed before you reveal them.
- Hiding something won't remove it from a screenshot, tmux capture history, or recording made while it was visible.
- The saved daily state is a random install identity and public card draws, with user-only permissions.
- `--no-color` if you'd prefer the whole thing in monochrome.

<details>
<summary>config and other CLIs</summary>

On Linux, config lives at `~/.config/arcana/config.toml` (`XDG_CONFIG_HOME` is respected). Or pass `--config PATH`. CLI flags win over config.

```toml
provider = "claude"       # none, claude, codex, custom
# art_dir = "/path/to/arttime/textart"
# timezone = "Asia/Dubai"
timeout = 45
```

For another CLI, give it an argument array:

```toml
provider = "custom"
argv = ["my-reading-cli", "--plain"]
timeout = 60
```

The command reads a UTF-8 prompt from stdin and writes its answer to stdout. It runs in an empty temporary directory. Use absolute paths for scripts outside `PATH`. A custom command is something you trust; its own tools, logs, and privacy are up to that command.

The named adapters were checked against Claude Code 2.1.302 and Codex CLI 0.163.0 help. Claude runs with tools disabled, safe mode, no MCP servers, and no session persistence. Codex uses an ephemeral read-only session, skips user config/rules, and disables web search and the shell-tool feature. That limits agent behavior; it doesn't sandbox the provider itself. Your CLI version and authentication still matter.

Daily state lives at `~/.local/share/arcana/` (`XDG_DATA_HOME` is respected). Use `--data-dir PATH` to change it, or `--date YYYY-MM-DD` and `--timezone IANA/Zone` to set the daily identity explicitly.

Linux is tested. macOS paths and terminal handling are there, but still need an on-device check. Native Windows isn't supported.

</details>

## if you want to poke at it

```sh
PYTHONPATH=src uv run --no-project python -m unittest discover -s tests -v
uv build
```

Tests cover the draws, concurrent daily state, locally available artwork, resizing, centering, hidden input, privacy, and provider failure/cancellation. The interactive bits are tested through pseudo-terminals too.

[Spec](docs/SPEC.md) · [Architecture](docs/ARCHITECTURE.md) · [Verification](docs/VERIFICATION.md) · [Screenshot notes](docs/screenshots/README.md)

## credit where it's due

The art comes from **[arttime](https://github.com/poetaman/arttime)**, authored and maintained by **Aman Mehra**, and the individual artists whose work it collects. Go look at arttime as well. This is an independent companion app; there's no affiliation or endorsement.

Arcana's original code and prose are [MIT](LICENSE). The deck files aren't bundled; the app reads your arttime installation. The screenshots show selected artwork for this personal, noncommercial project. That artwork keeps its own rights and isn't covered by Arcana's MIT license. [Credits and upstream notices are here.](CREDITS.md)
