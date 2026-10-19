# Verification and release limits

## Supported environment

The first implementation is exercised on Linux, including pseudo-terminal integration tests. Python 3.12+ is required. CI runs on Python 3.12, 3.13, and 3.14. macOS paths and POSIX terminal handling are implemented, but macOS has not been tested on-device. Windows is unsupported.

## Artwork

The installed arttime deck contains 78 cards, each with a 17-column by 25-row illustration. The parser derives the border rather than cutting bytes, excludes the upstream meaning panel, validates the single-cell glyph inventory, and preserves RGB colors. The Knight of Wands has a nonstandard top corner; its lower border supplies the width.

All 78 files parse, and rotating twice returns every original glyph, position, and foreground/background color. Directional arrows, corners, block fractions, and legacy-computing bars have explicit partners. Diagonal fills and rotationally symmetric shapes retain their glyph. Lettering uses one-cell upside-down approximations where available. B/D/K, quotation marks, some digits, and suit symbols retain their original shapes when no suitable one-cell partner exists. These are deliberate terminal-art approximations, not pixel-perfect bitmap rotation. The external card title and orientation are always upright. Exact glyph appearance depends on the terminal font.

Source SHA-256 values are recorded in memory and contribute to a deck fingerprint in the public draw. The code contains no upstream artwork, source code, or copied meaning text. Fallback reflections are original Arcana prose.

## Draw algorithm

`arcana/draw/v1` uses canonical NFC-normalized JSON, SHA-256, domain-separated HMAC streams, rejection sampling, and Fisher–Yates without replacement. No Python random/hash behavior is involved. A golden fixture for the built-in text deck draws, from the word `lantern` in seeded three-card mode: Nine of Coins upright, Six of Cups reversed, Seven of Coins upright. The source-art deck has a different fingerprint and different draws.

## Privacy and providers

PTY tests verify a completed background reading is absent from terminal output before reveal, show/hide works, resizing after hide does not leak it, and a new draw starts hidden. Artwork-only mode never invokes a configured provider. Ritual input is not echoed, and Escape restores the terminal. Static output is finite and contains no ANSI or interpretation unless explicitly requested.

Provider tests use deterministic local fixture executables to check stdin delivery, no seed in the prompt, output sanitation, malformed output, exit failures, missing binaries, timeout, bounded output, and process-group cancellation including descendants. CLI help was inspected for Claude Code 2.1.302 and Codex CLI 0.163.0. A live authenticated model response is not part of the offline test suite; authentication, network, model availability, and CLI version remain external dependencies. The custom adapter is not a sandbox.

No program can remove already revealed text from another process's recordings. Use `--private` when that matters. The provider itself may keep service-side records according to its configuration.

## Checks to repeat before public release

Run the suite and build a wheel in a clean environment. Inspect wheel contents to ensure no third-party art or private runtime data is included. Test tmux at wide/narrow sizes and inspect upright/reversed art with the intended font. Validate any provider version you intend to advertise with a live authenticated request. A full human aesthetic review of all reversed illustrations remains advisable before publishing screenshots or bundling artwork. Verify upstream licensing before any redistribution of assets.

## Local completion record

- 20 offline tests pass, including fail-before/pass-after regressions for batched privacy keys, Unicode Backspace, and wide text in one-column panes.
- `ty check src` passes.
- An isolated tmux server passed persistent full-art rendering at 110×45, a three-position spread, resize to 38×18, and clean quit. It did not use or change the user's existing tmux sessions.
- Independent Standards and Spec reviews found three distinct defects; all were fixed, covered by regressions, and confirmed resolved by the reviewers.
