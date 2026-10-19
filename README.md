<div align="center">

# arcana

**A small ritual, held open in your terminal.**

One card for the day. Three for a question. A quiet place among your panes.

</div>

Arcana is a proposed terminal tarot app built around the artwork in [arttime](https://github.com/poetaman/arttime). Draw a card, leave it beside your work, and return to it when something catches your eye. An optional AI reading offers a few words to sit with. Keep those words hidden until you want them.

**Status: scoped and ready to build.** This repository contains the product specification, technical design, and implementation plan. The commands below describe the intended interface; the application is not implemented yet.

```sh
arcana 1                         # today's card, held open in this pane
arcana 3                         # situation · tension · invitation
arcana 3 --ritual                # quietly ask for a seed word before drawing
arcana 1 --provider claude       # cards first; interpretation arrives in the background
arcana 3 --private               # artwork only; interpretation never enters the terminal
arcana 1 --once                  # print a static draw and exit
```

Think of a word. You may enter it without echo, or leave it unspoken and let chance choose. Arcana can hash that word into a repeatable draw. The word stays on your machine and is never included in the interpretation request.

The whole deck belongs here: 78 cards, including reversals. A reversed card changes both the illustration's orientation and the reading. The title remains readable.

Arcana lives in a tmux pane by default. It does not disappear when the reading finishes, and it does not change tomorrow's card underneath you. Press `d` to reveal or hide the divination, `h` to hide all private text immediately, and `q` to leave. Reading text starts hidden. `--private` disables revealing it for the entire session.

> A card is an invitation to notice. The interpretation should leave room for your own answer.

### The shape of the first release

- A persistent, resize-aware terminal display; side-by-side cards when they fit, one card at a time when they do not.
- Daily single-card draws and three-card spreads without duplicate cards.
- Optional word-seeded draws, with a versioned algorithm for replay.
- Upright and reversed artwork, with readable titles and explicit orientation labels.
- Background interpretations through an explicitly selected CLI provider; no provider is required to draw.
- Hidden-by-default divination, a hard artwork-only mode, and no journal unless you explicitly save.

The intended stack is Python 3.12+, Rich for rendering, and a small event loop. No database, account, web server, or daemon. Linux and macOS are the initial targets. tmux is a host, not a dependency.

### Read the project

[Product specification](docs/SPEC.md) · [Technical design](docs/ARCHITECTURE.md) · [Build plan](docs/PLAN.md) · [Credits and artwork policy](CREDITS.md)

### Thanks, arttime

This project starts with admiration for [arttime](https://github.com/poetaman/arttime), authored and maintained by **Aman Mehra**, and the artists represented in its collection. Its tarot artwork is the visual foundation of Arcana's intended first deck. Arcana is an independent companion project, with no claim of affiliation or endorsement.

No arttime code or artwork is redistributed here. The first implementation will read an existing local installation. Artwork licensing, individual credits, and any requirements for modified or bundled assets must be verified before vendoring or release packaging; see [CREDITS.md](CREDITS.md).

### Publish this repository

This is an independent Git repository on branch `main`. Once you create an empty remote:

```sh
git remote add origin <your-repository-url>
git push -u origin main
```

The repository has no runtime dependencies to install yet. Build milestones and their acceptance checks are in [the plan](docs/PLAN.md).
