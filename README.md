<div align="center">

# arcana

**A small ritual, held open in your terminal.**

One card for the day. Three for a question. A quiet place among your panes.

</div>

Arcana brings the tarot artwork in [arttime](https://github.com/poetaman/arttime) into a persistent terminal pane. Draw a card, leave it beside your work, and return when something catches your eye. An optional background AI reading offers a few words to sit with. Those words stay hidden until you ask for them.

## Begin

Requires **Python 3.12+**, [uv](https://docs.astral.sh/uv/), and a Linux terminal. Your existing arttime installation supplies the artwork. Without artwork, Arcana still works with named cards and original reflection prompts.

```sh
git clone <your-repository-url> arcana
cd arcana
./arcana 1
```

Already in this checkout? Just run `./arcana 1`. The launcher needs no package installation and downloads no runtime dependencies. To make `arcana` available everywhere:

```sh
uv tool install .
arcana 1
```

Use a terminal font with Unicode Symbols for Legacy Computing support and a dark background. Arcana preserves the deck's original colors. Set `--art-dir /path/to/arttime/textart` if your installation is elsewhere. Artwork scales down to fit smaller panes and returns to its original detail when you enlarge them. Extremely small panes use readable card names.

## The ritual

```sh
arcana 1                         # today's card; stays open
arcana 1 --ritual                # privately enter a word for today's draw
arcana 3                         # situation · tension · invitation
arcana 3 --ritual                # a repeatable spread from a privately entered word
arcana 3 --major                 # draw only from the major arcana
arcana 1 --upright-only          # omit reversed cards
arcana 1 --private               # artwork only; no reading request or reveal
arcana 1 --once                  # print and leave
arcana 3 --json                  # public card data, without a reading
```

Think of a word. Enter it without echo, or press Enter for chance. The word is hashed into the draw and stays in memory only. A single-card seeded draw includes the date; a three-card seeded spread does not. Identical inputs and deck version reproduce the cards and orientations. Interpretations may differ.

Without a seed word, your daily card is saved locally and remains the same when reopened that day. Three-card spreads use fresh randomness. All draws use the full 78-card deck unless `--major` is set, and three-card spreads never repeat a card. Reversals are enabled by default, including a rotated illustration and a readable external title.

## A pane to live beside

Open a tmux split and run `arcana 1`. Arcana stays there until you quit. It adapts to pane width and height: artwork scales down instead of disappearing in short panes, three cards stay side by side where practical, and very narrow panes let you browse one at a time. A revealed reading moves beside the cards in wide panes and below them in narrower ones. Resizing preserves your draw and hide/reveal state. A violet moon-and-star frame follows the pane edges, and each illustration and label is centered within the spread. The frame gives way to a compact view in tiny panes. `--no-color` keeps the ornament in monochrome. Arcana never changes your tmux layout or silently replaces a card at midnight.

| Key | Action |
| --- | --- |
| `d` | Reveal or hide divination; hidden at launch |
| `h` | Hide private text immediately |
| `j` / `k`, `→` / `←` | Browse cards in a narrow pane |
| `↑` / `↓` | Scroll a revealed reading |
| `r` | Retry the reading for the same cards |
| `n` | Draw again; daily and seeded rules still apply |
| `q`, Ctrl-C | Quit and cancel the background request |

`--private` is an artwork-only session: the provider never starts and reveal is disabled. Questions and readings are never saved by Arcana. The normal display uses the terminal's alternate screen; hidden text is never sent to the screen before reveal. Hiding cannot retract screenshots, tmux capture history, or recordings of text you already revealed.

## Give the cards a voice

No AI provider is required. Press `d` without one for a local reflection. Every minor card has its own upright and reversed meaning; three-card readings also consider the pattern across suits and major arcana.

Readings have three parts: **The thread**, **A small ritual**, and **A question to carry**. The ritual is an optional action for an ordinary day, requiring no purchases or special objects. AI readings use a more evocative, card-specific voice while leaving the interpretation open. To use an already authenticated CLI:

```sh
arcana 1 --provider claude
arcana 3 --ritual --provider codex
arcana 3 --provider claude --question   # privately prompt for a question
arcana 1 --once --interpret            # explicitly print a local reflection
```

The artwork appears first. For three cards, a single request produces one joined reading: how the tension challenges the situation, and how the invitation responds to both. Without a provider, the local reflection also connects the spread as a whole. The request runs in the background, buffers its answer, and leaves it hidden. Resize or browse cards without triggering another reading. A failed or slow provider leaves your cards and local reflection available. The default timeout is 45 seconds.

Providers receive only card names, orientations, positions, original reflection prompts, and an optional question you explicitly enter. **Your seed word is never sent.** A local CLI may contact a remote model service. Arcana does not manage authentication or override your model choice.

Named adapters were checked against Claude Code 2.1.302 and Codex CLI 0.163.0 help. Claude is invoked with tools disabled, safe mode, no MCP servers, and no session persistence. Codex uses an ephemeral read-only session, no user config/rules, disabled web search, and the shell-tool feature disabled. Both run from an empty temporary directory. These settings reduce agent behavior; they are not an OS security boundary. Live authenticated responses still depend on your provider/version. Other CLIs can use the generic adapter below.

### Configuration

Linux: `~/.config/arcana/config.toml` (respects `XDG_CONFIG_HOME`). macOS path: `~/Library/Application Support/arcana/config.toml`. Use `--config PATH` to override. CLI flags take precedence.

```toml
provider = "claude"       # none, claude, codex, custom
# art_dir = "/path/to/arttime/textart"
# timezone = "Asia/Dubai"
timeout = 45
```

For another CLI, use an argument array, never a shell string:

```toml
provider = "custom"
argv = ["my-reading-cli", "--plain"]
timeout = 60
```

The custom command reads the UTF-8 prompt from stdin and writes only the answer to stdout. It runs in a private temporary directory. Use an absolute executable path if it is not on `PATH`; relative script paths must also be absolute. Custom commands are trusted configuration and keep responsibility for their own tools, logs, and privacy.

Daily state lives under `~/.local/share/arcana/` on Linux (respects `XDG_DATA_HOME`). It contains a random install identity and public daily draws, never a word, question, or interpretation. `--data-dir PATH` overrides that location. State is written atomically under a lock. Use `--date YYYY-MM-DD` and `--timezone IANA/Zone` for an explicit daily identity.

## Development

```sh
PYTHONPATH=src uv run --no-project python -m unittest discover -s tests -v
uv build
```

There are no runtime dependencies. Tests cover deterministic draws, concurrent daily storage, terminal controls, background subprocess failure/cancellation, hidden input, and actual reveal/hide/resize behavior through a pseudo-terminal. The installed arttime deck is tested when available. Linux is verified; macOS is a portability target that still needs an on-device smoke test. Windows is not supported.

[Specification](docs/SPEC.md) · [Technical design](docs/ARCHITECTURE.md) · [Build plan and status](docs/PLAN.md) · [Verification notes](docs/VERIFICATION.md)

## Thanks, arttime

This project starts with admiration for [arttime](https://github.com/poetaman/arttime), authored and maintained by **Aman Mehra**, and the artists represented in its collection. Its tarot artwork is the visual foundation of Arcana's first deck. Arcana is an independent companion project, with no claim of affiliation or endorsement.

No arttime code or artwork is redistributed here. Cards are loaded from your local installation. Their credits and license terms remain upstream; see [CREDITS.md](CREDITS.md). Original Arcana code and documentation use the [MIT license](LICENSE). Reversed art rotates the cell grid and directional block glyphs; a few lettering and suit glyphs use deliberate approximations described in the verification notes.

> A card is an invitation to notice. The interpretation leaves room for your own answer.
