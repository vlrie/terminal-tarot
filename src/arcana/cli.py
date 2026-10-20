"""Command line entry point; optional private ritual precedes the display."""

import argparse
import asyncio
from datetime import date
import json
import os
from pathlib import Path
import secrets
import sys
import termios
import tty
from zoneinfo import ZoneInfoNotFoundError

from . import __version__
from .art import ansi_row, rotate
from .deck import load
from .display import Session, run
from .draw import create, normalize
from .providers import ProviderError, command, interpret, prompt
from .storage import daily, load_config, today
from .text import clean


def hidden_input(message: str) -> str:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("private input requires an interactive terminal")
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    data = bytearray()
    sys.stdout.write(message)
    sys.stdout.flush()
    try:
        tty.setraw(fd)
        while True:
            c = os.read(fd, 1)
            if c in (b"\x1b", b"\x03", b"\x04", b""):
                raise KeyboardInterrupt
            if c in (b"\r", b"\n"):
                break
            if c in (b"\x7f", b"\x08"):
                if data:
                    # Edit codepoints rather than bytes; preceding multibyte
                    # characters must survive deletion of an ASCII character.
                    data = bytearray(data.decode("utf-8", errors="ignore")[:-1].encode())
            elif len(data) < 4096:
                data.extend(c)
        return clean(data.decode("utf-8", errors="replace"))
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        sys.stdout.write("\n")
        sys.stdout.flush()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arcana", description="A small tarot ritual, held open in your terminal.", epilog="Pane keys: d reveal/hide, h hide, j/k cards, arrows scroll/navigate, r retry, n draw, q quit. Hiding cannot retract recordings or tmux capture history; --private never prints a reading.")
    p.add_argument("count", nargs="?", type=int, choices=(1, 3), default=1, help="1 daily card (default) or 3-card spread")
    p.add_argument("--version", action="version", version=f"arcana {__version__}")
    p.add_argument("--ritual", action="store_true", help="privately ask for a word to seed either draw")
    p.add_argument("--question", action="store_true", help="privately prompt for a question to send to the provider")
    p.add_argument("--private", action="store_true", help="artwork only; never invoke a provider or reveal divination")
    p.add_argument("--once", action="store_true", help="print cards and exit")
    p.add_argument("--json", action="store_true", help="emit versioned public card data and exit")
    p.add_argument("--interpret", action="store_true", help="explicitly print interpretation with --once (or piped output)")
    p.add_argument("--major", action="store_true", help="draw only from the 22 major arcana")
    p.add_argument("--upright-only", action="store_true", help="disable reversals")
    p.add_argument("--date", type=date.fromisoformat, help="daily date override, YYYY-MM-DD")
    p.add_argument("--timezone", help="IANA timezone for daily draws")
    p.add_argument("--provider", choices=("none", "claude", "codex", "custom"), help="background reading provider; defaults to config or none")
    p.add_argument("--art-dir", help="path to arttime's textart directory")
    p.add_argument("--config", type=Path, help="TOML config path")
    p.add_argument("--data-dir", type=Path, help="override private daily-state directory")
    p.add_argument("--no-color", action="store_true", help="disable artwork colors")
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    interactive = sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get("TERM") != "dumb"
    static = args.once or args.json or not interactive
    if args.private and (args.interpret or args.question):
        p.error("--private cannot be combined with --interpret or --question")
    if args.json and (args.interpret or args.question or args.ritual):
        p.error("--json cannot prompt or include interpretation; omit --ritual, --question, --interpret")
    if args.date and args.count != 1:
        p.error("--date applies only to one-card daily draws")
    if args.interpret and not static:
        p.error("--interpret prints private text; use --once or reveal with d in the pane")
    if (args.ritual or args.question) and not interactive:
        p.error("private prompts require an interactive terminal")
    try:
        config = load_config(args.config)
        provider = args.provider if args.provider is not None else config.provider
        if provider not in ("none", "claude", "codex", "custom"):
            raise ValueError("unknown provider in configuration")
        if provider != "none" and not args.private:
            command(provider, config.argv)
        deck = load(args.art_dir if args.art_dir is not None else config.art_dir, args.major)
        timezone = args.timezone or config.timezone
        today(timezone)  # Validate the zone before asking for private input.
        for notice in deck.notices:
            print(notice, file=sys.stderr)
        word = normalize(hidden_input("Think of a word. Enter it to weave it into the draw, or Enter for chance: ")) if args.ritual else ""
        question = hidden_input("Your question (hidden; sent only to the selected provider): ").strip() if args.question else None
        if question and provider == "none":
            raise ValueError("--question needs a provider; choose --provider claude, codex, or custom")

        def new_draw():
            current_day, current_zone = today(timezone)
            if args.date:
                current_day = args.date.isoformat()
            if word:
                return create(deck, args.count, word, "seeded", current_day if args.count == 1 else None, current_zone if args.count == 1 else None, args.upright_only)
            if args.count == 1:
                return daily(deck, current_day, current_zone, args.upright_only, args.data_dir)
            return create(deck, 3, secrets.token_bytes(32), "fresh", upright_only=args.upright_only)

        draw = new_draw()
        if args.json:
            print(json.dumps(draw.public(), ensure_ascii=False, indent=2))
            return 0
        color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
        if static:
            for pick in draw.picks:
                card = deck.by_id(pick.card_id)
                print(f"{pick.position} · {card.name} ({'reversed' if pick.reversed else 'upright'})")
                if sys.stdout.isatty() and card.grid:
                    for row in rotate(card.grid) if pick.reversed else card.grid:
                        print(ansi_row(row, color))
                print()
            if args.interpret:
                if provider == "none":
                    from .readings import local_reading
                    print(local_reading(draw, deck))
                else:
                    try:
                        print(asyncio.run(interpret(provider, config.argv, prompt(draw, deck, question), config.timeout)))
                    except ProviderError as error:
                        print(str(error), file=sys.stderr)
                        return 1
            return 0
        session = Session(draw, private=args.private)
        asyncio.run(run(session, deck, new_draw, lambda d: bool(d.date and not args.date and today(timezone)[0] != d.date), provider, config.argv, config.timeout, question, color))
        return 0
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0
    except ValueError as error:
        # Domain errors have controlled messages; sanitize any external art
        # filename/OS diagnostics before presenting them outside the screen.
        print("arcana: " + clean(str(error))[:240], file=sys.stderr)
        return 1
    except ZoneInfoNotFoundError:
        print("arcana: unknown timezone; use an IANA name such as Asia/Dubai.", file=sys.stderr)
        return 1
    except OSError:
        print("arcana: cannot access the terminal or state directory; check permissions or use --once.", file=sys.stderr)
        return 1
