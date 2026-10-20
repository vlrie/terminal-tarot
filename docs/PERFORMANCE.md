# Python performance refactor

The application stays in Python and keeps its existing appearance, draw algorithm, CLI options, and privacy behavior. This refactor targets measured repeated work and separates terminal I/O from layout and state transitions.

## Measurements

Local Linux measurements using Python 3.13.12 and the installed 78-card arttime deck. The baseline is commit `d67c7ef`. These are warm-run medians on one workstation, not cross-platform guarantees. Frame construction excludes terminal painting and model calls.

| Operation | Before | After |
| --- | ---: | ---: |
| Load deck metadata and artwork | 153.3 ms | 3.6 ms for metadata and source hashes; artwork parsed on demand |
| Installed CLI startup, `3 --json` | 218.2 ms | 53.2 ms |
| First visible interactive frame, 120 × 40 PTY | 186.7 ms | 63.4 ms |
| Build a 120 × 40 revealed frame, one-shot renderer | 3.56 ms | 1.01 ms |
| Build a revealed frame with the reused renderer | — | 0.18 ms |
| Idle app RSS after first frame | 34.1 MiB | 28.3 MiB |

A representative hidden-provider-completion update writes **188 bytes**, compared with **32,073 bytes** for its initial full frame. Unchanged frames and ignored keys write nothing. Reveal/hide can still change many rows when the layout moves or resizes artwork.

The deck-load comparison intentionally measures the new lazy interface: startup still reads and hashes every source file to retain the exact fingerprint, but it does not parse 78 images. An interactive draw parses the displayed one to three cards. Metadata-only JSON output parses none.

## Changes

- `deck.py`: read and bound-check source bytes, hash all files as before, then parse each illustration on first access. Cache the original and inverse grids. Card lookup uses a cached index. Retaining the original source bytes keeps the fingerprint and displayed image tied to the same content even if the source files later change.
- `display.py`: reuse a renderer with bounded encoded-art caching and a single cached wrapped reading. Measured `Line` values carry visible width beside their ANSI text, eliminating repeated ANSI stripping during alignment. Rendering returns the effective scroll offset instead of changing session state.
- `state.py`: immutable session state and pure keyboard transitions. Effects such as retry and new draw are explicit actions.
- `screen.py`: compare successive frames and overwrite only changed rows. Every changed row resets styles and erases its remaining cells, including when a formerly revealed reading becomes shorter or disappears. First paint and resize still clear and redraw the screen.
- `terminal.py`: own terminal setup/restoration, incremental key decoding, and pane sizing.
- `app.py`: coordinate typed input/provider events and effects. Ignore irrelevant keys and coalesce queued resize signals. Provider execution and process-group cleanup retain their existing behavior.

Caches stay within the process. No question, word, or interpretation is written to disk by the new caching layer. The renderer retains only one wrapped prose entry, and art views use a 128-entry LRU bound.

## Reproduce

```sh
PYTHONPATH=src uv run --no-project python benchmarks/benchmark.py
```

The script reports current startup, frame construction, and emitted-byte measurements. An external arttime installation is required for meaningful art-performance comparisons; the output records whether it was found. No provider requests or private prompts are used.

## Regression checks

During the refactor, 48 baseline frames across card counts, visibility, color, and pane sizes were compared byte for byte with the old renderer. Unit tests exercise deferred validation, cache reuse, pure state transitions, and screen differences. A small test terminal applies cursor/erase commands and checks that reveal, scroll, and hide produce the same final screen as a full render, with no residual private text. Existing PTY tests cover the real interactive app, provider lifecycle, resizing, hidden input, and ignored keys.
