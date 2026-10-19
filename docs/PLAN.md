# Build plan

The deliverable in this repository is a finished scope and implementation handoff. Build in the following order; each milestone leaves something observable. A polished first release is approximately 4–7 focused development days, with reversed-art fidelity and provider behavior the main uncertainties. This estimate is provisional until milestone 1.

## 1. Prove the deck and the pane

Create package metadata and a runnable `arcana` entry point. Build the 78-card source manifest from a local arttime install, inventory glyphs and ANSI sequences, and record upstream provenance and license findings. Render one upright and one genuinely reversed illustration in a persistent alternate screen. Test directly and inside tmux.

Accept when all 78 source files are accounted for; illustration extraction excludes metadata; glyph rotation is complete or an approved derivative-asset route is established; quit restores cursor and terminal state; resize does not wrap or leak art. Manually inspect every reversed card in a contact sheet or terminal gallery. Stop to resolve art fidelity before building around a flawed renderer.

## 2. Make draws trustworthy

Implement the versioned seed algorithm, immutable Draw model, full/major decks, no-replacement selection, reversal policy, hidden ritual input, and daily state with concurrent access protection.

Accept when golden vectors fix exact outputs across process restarts; equal normalized inputs reproduce the same draw; changing provider leaves cards unchanged; daily dates/timezones and midnight are covered; concurrent panes receive the same daily card; 3-card draws never duplicate IDs; fresh draws use OS randomness. Test EOF/cancel, Unicode words, corrupt storage, and non-TTY ritual requests. Export no raw word or digest by default.

## 3. Make it live in tmux

Build the persistent display and input loop. Add adaptive card layouts, card navigation, `d`, `h`, `n`, and default-hidden divination state with placeholder text. Add hard `--private`, static/non-TTY behavior, `NO_COLOR`, and compact layout.

Accept when cards remain on screen indefinitely without busy polling; resize preserves draw and privacy state; hidden regions are fully erased; question text never appears in the footer; new draws start hidden; `--private` cannot reveal private text. Use a PTY capture to verify hidden sentinel text never reaches terminal output. Inspect reveal-then-hide and shrinking a revealed panel manually inside tmux. Explain capture-history limits in help.

## 4. Add a voice in the background

Implement generic argv/stdin provider execution and buffered sanitized output. Add timeout, output bounds, cancellation, generation IDs, retry, and local interpretation fallback. Verify installed Claude and Codex CLI contracts before shipping named adapters; document tested versions. Start the subprocess only after first card paint.

Accept using fake CLIs for success, slow output, failure, missing binary, malformed escapes, excessive output, timeout, and late results. Verify pending work never freezes keys or resize; quit cancels child descendants; retry never changes cards; private mode never invokes a provider. A sentinel seed word must be absent from subprocess argv, prompt, persisted files, and app diagnostics. Perform optional real-provider smoke checks only with configured authentication.

## 5. Package and polish

Write installation and configuration instructions backed by actual tested commands. Add representative screenshots with upright/reversed examples and narrow/wide layouts. Add CI for the supported Python version and focused tests. Validate installation in a clean environment, `--help`, non-TTY mode, and wheel contents. Choose and add a license for original code; keep third-party artwork terms distinct.

Accept when a fresh user can install, point at arttime, draw offline, optionally configure a provider, hide/reveal, and quit using README alone. Verify Linux and macOS or explicitly limit the first supported release. No artwork enters a wheel or Git history without license verification and preserved artist credits. Tag v0.1 only after these checks.

## Later, if the ritual earns it

Explicit journal/export, customizable three-position labels, a user-approved bundled deck, additional providers, and optional tmux launch recipes. Automatic daily replacement, cloud sync, and chat are not prerequisites for a useful release.
