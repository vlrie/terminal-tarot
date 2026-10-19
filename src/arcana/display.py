"""A persistent alternate-screen terminal view, without runtime dependencies."""

import asyncio
import contextlib
from dataclasses import dataclass
import os
import shutil
import signal
import sys
import termios
import tty
from typing import Callable

from .art import ansi_row, rotate
from .deck import Deck
from .draw import Draw
from .providers import ProviderError, interpret, prompt
from .text import clean, clip, width, wrap


@dataclass
class Session:
    draw: Draw
    selected: int = 0
    visible: bool = False
    private: bool = False
    reading: str = ""
    status: str = "local reflection"
    new_day: bool = False
    scroll: int = 0


def local_reading(draw: Draw, deck: Deck) -> str:
    return "\n\n".join(f"{p.position} · {deck.by_id(p.card_id).name} ({'reversed' if p.reversed else 'upright'})\n{deck.by_id(p.card_id).meaning(p.reversed)}" for p in draw.picks) + "\n\nWhat would it look like to give this a little attention today?"


def render(session: Session, deck: Deck, columns: int, rows: int, color: bool = True) -> str:
    columns, rows = max(1, columns - 1), max(1, rows)
    if columns < 12 or rows < 5:
        return "\x1b[H\x1b[2J" + clip("arcana · q quit", columns)
    title = "a r c a n a" + ("   ·   " + session.draw.date if session.draw.date else "   ·   three cards")
    lines = [clip(title, columns), ""]
    sizes = [len(deck.by_id(p.card_id).grid[0]) if deck.by_id(p.card_id).grid else 23 for p in session.draw.picks]
    heights = [len(deck.by_id(p.card_id).grid) for p in session.draw.picks]
    panel = max(25, *sizes)
    all_fit = columns >= (panel + 3) * len(sizes) - 3
    chosen = list(range(len(sizes))) if all_fit else [session.selected]
    art_height = max(heights)
    show_art = art_height > 0 and rows >= art_height + 9 and columns >= panel
    # Keep enough room for prose, using compact cards in a very short pane.
    for line_index in range((art_height if show_art else 0) + 3):
        pieces = []
        for index in chosen:
            pick = session.draw.picks[index]
            card = deck.by_id(pick.card_id)
            if line_index == 0:
                text = clip(pick.position + f"  {index + 1}/{len(sizes)}", panel)
            elif line_index == 1:
                text = clip(card.name, panel)
            elif line_index == 2:
                text = "reversed ↓" if pick.reversed else "upright ↑"
            else:
                grid = rotate(card.grid) if pick.reversed else card.grid
                art_index = line_index - 3
                if art_index < len(grid):
                    raw = ansi_row(grid[art_index], color)
                    # The SGR bytes do not occupy terminal cells.
                    text = raw + " " * max(0, panel - len(grid[art_index]))
                    pieces.append(text)
                    continue
                text = ""
            pieces.append(text + " " * max(0, panel - width(text)))
        if all_fit:
            lines.append("   ".join(pieces).rstrip())
        else:
            # Every generated line is within panel width, but panel may exceed
            # a small terminal. Compact title lines have no escapes to clip.
            lines.append(pieces[0] if show_art and line_index >= 3 else clip(pieces[0], columns))
    if not all_fit:
        lines.append(clip(" · ".join(f"{i+1} {deck.by_id(p.card_id).name}{' ↓' if p.reversed else ''}" for i, p in enumerate(session.draw.picks)), columns))
    lines.append("")
    footer = ("artwork only · q quit · j/k cards" if session.private else "d reveal/hide · h hide · j/k cards · ↑/↓ text · r retry · n draw · q quit")
    if session.new_day:
        footer = "new day available · n to draw · " + footer
    content_limit = rows - 2
    if session.visible and not session.private:
        prose = wrap(session.reading or local_reading(session.draw, deck), columns)
        available = max(0, content_limit - len(lines) - 1)
        max_scroll = max(0, len(prose) - available)
        offset = min(session.scroll, max_scroll)
        lines += prose[offset:offset + available]
        if available and len(prose) > available:
            lines.append(clip(f"reading {offset + 1}–{min(offset + available, len(prose))}/{len(prose)} · ↑/↓ scroll", columns))
    else:
        lines.append(clip("artwork only" if session.private else f"{session.status} · divination hidden", columns))
    lines = lines[:content_limit]
    lines += [""] * max(0, content_limit - len(lines))
    lines += [clip(footer, columns)]
    # Home + clear explicitly removes formerly revealed text even after resize.
    return "\x1b[H\x1b[2J" + "\r\n".join(lines) + "\x1b[0m"


async def run(session: Session, deck: Deck, new_draw: Callable[[], Draw], day_changed: Callable[[Draw], bool], provider: str, argv: tuple[str, ...], timeout: float, question: str | None, color: bool):
    loop = asyncio.get_running_loop()
    events: asyncio.Queue[tuple[str, bytes | tuple[int, str] | None]] = asyncio.Queue()
    provider_task = None
    generation = 0
    terminal = sys.stdin.fileno()
    saved = termios.tcgetattr(terminal)

    def repaint():
        size = shutil.get_terminal_size()
        sys.stdout.write(render(session, deck, size.columns, size.lines, color))
        sys.stdout.flush()

    async def cancel():
        nonlocal provider_task
        if provider_task:
            provider_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await provider_task
            provider_task = None

    async def request(request_id: int, draw: Draw):
        try:
            answer = await interpret(provider, argv, prompt(draw, deck, question), timeout)
            await events.put(("reading", (request_id, answer)))
        except ProviderError as error:
            await events.put(("failure", (request_id, str(error))))

    def start():
        nonlocal provider_task
        if provider != "none" and not session.private:
            session.status = "reading in progress"
            provider_task = asyncio.create_task(request(generation, session.draw))

    def input_ready():
        try:
            data = os.read(terminal, 128)
        except OSError:
            data = b""
        events.put_nowait(("key", data))

    try:
        tty.setcbreak(terminal)
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        loop.add_reader(terminal, input_ready)
        loop.add_signal_handler(signal.SIGWINCH, lambda: events.put_nowait(("resize", None)))
        loop.add_signal_handler(signal.SIGTERM, lambda: events.put_nowait(("key", b"q")))
        repaint()  # Artwork is visible before the background request starts.
        start()
        if provider_task:
            repaint()
        while True:
            try:
                event, payload = await asyncio.wait_for(events.get(), 1)
            except TimeoutError:
                changed = day_changed(session.draw)
                if changed != session.new_day:
                    session.new_day = changed
                    repaint()
                continue
            if event in ("reading", "failure"):
                assert isinstance(payload, tuple)
                request_id, value = payload
                if request_id != generation:
                    continue
                if event == "reading":
                    session.reading, session.status = value, "reading ready"
                else:
                    session.status = value
                repaint()
                continue
            if event == "key":
                assert isinstance(payload, bytes)
                data = payload
                if data in (b"", b"q", b"\x03", b"\x04"):
                    break
                if data == b"d" and not session.private:
                    session.visible = not session.visible
                elif data == b"h":
                    session.visible = False
                elif data in (b"j", b"\x1b[C"):
                    session.selected = (session.selected + 1) % len(session.draw.picks)
                elif data in (b"k", b"\x1b[D"):
                    session.selected = (session.selected - 1) % len(session.draw.picks)
                elif data == b"\x1b[B":
                    session.scroll = min(session.scroll + 1, len(wrap(session.reading or local_reading(session.draw, deck), max(1, shutil.get_terminal_size().columns - 1))) - 1)
                elif data == b"\x1b[A":
                    session.scroll = max(0, session.scroll - 1)
                elif data == b"r" and provider != "none" and not session.private:
                    generation += 1
                    await cancel()
                    session.reading = ""
                    start()
                elif data == b"n":
                    generation += 1
                    session.visible = False
                    session.reading, session.scroll, session.selected = "", 0, 0
                    repaint()  # Hide before waiting for subprocess cancellation.
                    await cancel()
                    session.draw = new_draw()
                    session.new_day = False
                    session.status = "local reflection"
                    start()
            repaint()
    finally:
        # Restore the user's terminal before potentially slow child cleanup.
        loop.remove_reader(terminal)
        loop.remove_signal_handler(signal.SIGWINCH)
        loop.remove_signal_handler(signal.SIGTERM)
        termios.tcsetattr(terminal, termios.TCSADRAIN, saved)
        sys.stdout.write("\x1b[0m\x1b[2J\x1b[H\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        await cancel()
