# Technical design

## Components and state

Use a small Python package with `cli`, `deck`, `draw`, `art`, `display`, `readings`, `meanings`, `providers`, and `storage` modules. The implementation uses Python 3.12+ and its standard library only: ANSI RGB cell rendering, termios input, asyncio event handling/subprocesses, Unicode width checks, and TOML configuration. External artwork is validated to contain only single-cell non-combining glyphs; other inputs receive cell-aware clipping and wrapping. No runtime packages or full-screen framework are needed.

`Draw` contains schema/algorithm version, immutable ordered card IDs, orientations, spread, deck fingerprint, date/timezone when applicable, and source mode. `Session` adds selected card, visibility, terminal size, question in memory, and provider state. Provider states: idle, pending, complete, failed, cancelled. Each request carries a generation ID; discard late results from a replaced draw. Visibility is independent of provider completion.

The rendering function consumes Session and terminal size. It downscales art cells to fit width and height, with endpoint sampling to retain borders and no upscaling of glyphs; original grids remain immutable. Wide revealed layouts use a reading column, while narrower layouts reserve a reading region below the cards. Scroll position is clamped against the actual reading width after reflow. The terminal file descriptor is authoritative for pane size, even when COLUMNS/LINES are stale. It never draws cards or launches a provider. The draw engine never reads terminal state. Provider adapters never modify Draw. These boundaries make hide/reveal and retry safe.

## Deck discovery and provenance

Resolution order: `--art-dir`, configured art directory, known arttime installation directories. Do not run shell startup files to discover paths. Missing art produces a useful path diagnostic and a text-only fallback with original local meanings; never silently download assets.

Verified on the local arttime installation on 2026-10-19: 78 `textart/tarot-*` files. Filenames encode major arcana `00..21`, then wands, cups, swords, coins `01..14`. Each file starts with a message/header line; the following rows combine the illustration on the left with title and upright/reversed meanings on the right. These are ANSI truecolor files using Unicode Symbols for Legacy Computing, not plain ASCII images.

The runtime manifest has stable IDs, names, source filenames, source SHA-256, and illustration grids. Artwork provenance and unresolved individual credits are recorded in CREDITS.md; no asset is distributed. Sort by documented suit/rank order, never filesystem enumeration. Validate every file before display. Derive bounds using parsed terminal cells, with per-file overrides if necessary. Do not assume byte offsets or a universal fixed width. Do not rotate the entire combined art-and-meaning panel.

The local launcher references LICENSE_CODE, LICENSE_ART, and LICENSE_ADDENDUM_CFLA; the installed share directory lacks them. Their exact current terms were not verified during scoping. Upstream asset redistribution and derivative-art permissions remain a packaging prerequisite. A fork is authorized by the user if needed; first prefer a companion app loading the existing deck. Forking alone does not resolve licensing.

## Real reversed art

Parse ANSI SGR into a rectangular grid of grapheme cells with foreground/background attributes. Allow only supported SGR color/style sequences; reject or strip cursor movement, OSC, links, and other terminal controls. Preserve padding and reset styling at boundaries.

Rotate the illustration grid 180 degrees, transform directional glyphs through an explicit rotation table, and retain cell colors. Blocks, quadrants, legacy-computing mosaics, and box-drawing characters need correct partners; reversing strings is insufficient. Keep the external title, position, orientation, and meaning upright. Characters with no exact rotated form need an explicitly reviewed approximation or authored reversed variant. Avoid silently claiming fidelity for unmapped glyphs.

Inventory glyphs across all 78 cards first. The renderer spike must resolve the full inventory, double-width/combining characters, and terminal font support before committing to this method. If faithful cell rotation is not viable, prepare reviewed reversed assets after verifying derivative-art permissions. A reversed label alone does not meet v1's visual requirement.

## Deterministic draw v1

Specify the algorithm in code and publish golden fixtures. Serialize seed input as UTF-8 canonical JSON: sorted keys, compact separators, NFC-normalized strings, explicit algorithm version, deck fingerprint, count, reversal policy, mode, and date/timezone only for daily mode. Seed material is the normalized word for seeded mode, a stored random install identity for unseeded daily mode, or 32 fresh OS-random bytes for fresh mode. Encode binary material as lowercase hex with an explicit material-kind field.

Derive a 32-byte key with SHA-256 over the canonical payload, prefixed by `arcana/draw/v1` plus a NUL byte. Expand a byte stream using HMAC-SHA256(key, domain || uint64be(counter)), starting counter at zero. Use separate domains for shuffle and orientation. Read unsigned 32-bit big-endian integers; sample bounded integers by rejection, discarding values >= floor(2^32 / bound) * bound. Fisher–Yates shuffle the canonical deck from the last index down; take the first N. Orientation uses one unbiased bounded integer in [0,2) per selected card, with 1 meaning reversed. Disabling reversals leaves all upright. Do not depend on Python's random implementation or hash().

Full-deck and major-only manifests have different fingerprints. Version any change to ordering, normalization, serialization, or algorithm. Card reproducibility is guaranteed for identical inputs and version; AI prose is not guaranteed reproducible.

## Provider boundary

Define a custom provider as an executable plus argument vector and a transport contract: UTF-8 prompt on stdin, UTF-8 answer on stdout, success exit status zero. Launch with `shell=False` from an empty private temporary working directory, with stdin closed after writing. Keep terminal input attached to Arcana, never to the provider. No repository inspection, tool permissions, or agent sandbox bypasses are required for a reading.

The generic adapter is tested with local fixture executables. Named Claude and Codex adapters use contracts checked against installed CLI help; tested versions and remaining live-service checks are in VERIFICATION.md. Claude disables tools, customizations, MCP, and persistence. Codex uses ephemeral read-only execution, disables the shell-tool feature and web search, and skips user config/rules. These settings constrain agent behavior but are not an OS sandbox for the provider itself. Codex JSON events are parsed to retain only completed agent messages. Users who require strict tool-free provider behavior should use Claude or a custom plain-completion CLI.

Use a 45-second default timeout, 64 KiB stdout cap, bounded stderr capture, output sanitation, and no raw errors in the UI. Cancel the whole child process group on quit, retry, or new draw; terminate then kill after a short grace period. No orphan requests. Do not claim generic executables are sandboxed: configured commands are trusted user configuration. Avoid shell-string command configuration.

The prompt supplies only structured card data, original Arcana reflection prompts, positions, style/length rules, and an optional question. Delimit question text as user content, never executable instructions. Never include seed material or surrounding project files. Final output is buffered before display; hidden mode never prints it.

## Files and failure handling

Use platform-appropriate XDG config/data locations on Linux and conventional user application locations on macOS, with explicit overrides. Configuration holds provider argv and deck paths, never credentials. Protect created data directories and files with user-only permissions. Write daily state atomically under a file lock so concurrent panes agree. Corrupt state gets a clear diagnostic; never silently replace a persisted daily draw.

No runtime files live in the source checkout. Pipe mode prints card names/orientations without ANSI or providers by default. `--json` emits versioned card data and exits; private text and seed material are excluded. `--once --interpret` is an explicit exception that waits for and prints interpretation; reject its combination with `--private`.

## Frame, centering, and interpretation content

`display` reserves the frame’s cells before computing the inner layout. ANSI-aware visible widths center both labels and art within each card panel, and the spread within its entire region. Card blocks are vertically centered when space permits. Very small panes omit the border. Color is confined to the original artwork and a muted violet frame; the terminal background is untouched.

`meanings` contains original upright/reversed prompts for each of the 56 minor cards. `readings` supplies the offline synthesis, suit relationships, and card-specific or suit-specific optional practices and questions. Providers receive that structured content as suggestions, with instructions to write a connected, evocative reflection rather than reproduce a template. These prose changes do not alter card IDs, deck fingerprints, seed material, or daily selections.
