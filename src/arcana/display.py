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

from .art import ansi_row, fit, rotate
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
    if len(draw.picks) == 1:
        pick = draw.picks[0]
        card = deck.by_id(pick.card_id)
        return f"{pick.position} · {card.name} ({'reversed' if pick.reversed else 'upright'})\n{card.meaning(pick.reversed)}\n\nWhat would it look like to give this a little attention today?"
    cards = [deck.by_id(p.card_id) for p in draw.picks]
    names = [f"{card.name} ({'reversed' if pick.reversed else 'upright'})" for card, pick in zip(cards, draw.picks)]
    meanings = [card.meaning(pick.reversed) for card, pick in zip(cards, draw.picks)]
    suits = {card.id.split('-')[0] for card in cards}
    if suits == {"major"}:
        thread = "All three are major arcana: consider the larger pattern beneath the immediate question."
    elif len(suits) == 1:
        theme = {"wands": "initiative", "cups": "connection", "swords": "discernment", "coins": "material care"}[next(iter(suits))]
        thread = f"Their shared suit keeps the whole reading close to {theme}; look for one pattern appearing in three forms."
    else:
        thread = "The different parts of the deck ask you to connect perspectives rather than settle on the first explanation."
    reversed_count = sum(pick.reversed for pick in draw.picks)
    pace = " Let the reversed cards mark where a quieter, slower response may help." if reversed_count else " Let the upright cards suggest a small action you can try and then reassess."
    return (f"Read together, {names[0]} frames the situation: {meanings[0]} "
            f"{names[1]} brings the tension into focus: {meanings[1]} "
            f"{names[2]} offers a way to respond: {meanings[2]}\n\n"
            f"{thread}{pace} Treat the invitation as a response to the tension within the situation, rather than a separate prediction. "
            "What small step would honor all three cards together?")


def split_keys(data: bytes) -> tuple[list[bytes], bytes]:
    """Consume every key, retaining incomplete arrow escape sequences."""
    keys = []
    while data:
        if data in (b"\x1b", b"\x1b["):
            break
        size = 3 if data.startswith(b"\x1b[") and len(data) >= 3 else 1
        keys.append(data[:size])
        data = data[size:]
    return keys, data


def terminal_size() -> os.terminal_size:
    """Read the pane itself, even if inherited COLUMNS/LINES values are stale."""
    try:
        return os.get_terminal_size(sys.stdout.fileno())
    except (OSError, ValueError):
        return shutil.get_terminal_size()


def _cards(session: Session, deck: Deck, columns: int, height: int, color: bool) -> list[str]:
    gap = 3
    count = len(session.draw.picks)
    all_fit = count == 1 or columns >= count * 12 + gap * (count - 1)
    chosen = list(range(count)) if all_fit else [session.selected]
    panel = min(25, max(1, (columns - gap * (len(chosen) - 1)) // len(chosen)))
    blocks = []
    for index in chosen:
        pick = session.draw.picks[index]
        card = deck.by_id(pick.card_id)
        lines = [clip(pick.position + f"  {index + 1}/{count}", panel), clip(card.name, panel), clip("reversed ↓" if pick.reversed else "upright ↑", panel)]
        grid = fit(rotate(card.grid) if pick.reversed else card.grid, panel, max(0, height - 3))
        for row in grid:
            lines.append(ansi_row(row, color) + " " * max(0, panel - len(row)))
        blocks.append(lines)
    lines = []
    for row in range(max(map(len, blocks))):
        pieces = []
        for block in blocks:
            text = block[row] if row < len(block) else ""
            # Art rows already include padding; labels are unstyled text.
            pieces.append(text + " " * max(0, panel - width(text)) if row < 3 or not text else text)
        lines.append((" " * gap).join(pieces).rstrip())
    return lines[:height]


def _reading(session: Session, deck: Deck, columns: int, height: int) -> list[str]:
    if height < 1:
        return []
    heading = "The spread, together" if len(session.draw.picks) == 3 else "Your reading"
    prose = wrap(session.reading or local_reading(session.draw, deck), columns)
    if height < 3:
        return [clip(heading + " · enlarge pane to read", columns)]
    available = height - 2
    max_scroll = max(0, len(prose) - available)
    session.scroll = min(max(0, session.scroll), max_scroll)
    offset = session.scroll
    lines = [clip(heading, columns)] + prose[offset:offset + available]
    if len(prose) > available:
        lines.append(clip(f"{offset + 1}–{min(offset + available, len(prose))}/{len(prose)} · ↑/↓ scroll", columns))
    return lines


def render(session: Session, deck: Deck, columns: int, rows: int, color: bool = True) -> str:
    columns, rows = max(1, columns - 1), max(1, rows)
    if columns < 12 or rows < 7:
        return "\x1b[H\x1b[2J" + clip("arcana · q quit", columns)
    title = "a r c a n a" + ("   ·   " + session.draw.date if session.draw.date else "   ·   three cards")
    revealed = session.visible and not session.private
    body_height = rows - 4  # title, spacer, status, and footer
    status = "artwork only" if session.private else f"{session.status} · divination hidden"
    footer = "q quit · j/k cards" if session.private else "d reveal/hide · h hide · j/k cards · ↑/↓ text · r retry · n draw · q quit"
    if session.new_day:
        footer = "new day available · n draw · " + footer
    count = len(session.draw.picks)
    # Reading beside full-size art where possible; below it in other panes.
    cards_width = count * 19 + (count - 1) * 3
    side_by_side = revealed and columns >= cards_width + 3 + 30
    if side_by_side:
        left = _cards(session, deck, cards_width, body_height, color)
        right = _reading(session, deck, columns - cards_width - 3, body_height)
        body = []
        for row in range(max(len(left), len(right))):
            card_line = left[row] if row < len(left) else ""
            # Width of generated SGR art excludes its terminal controls.
            padding = " " * max(0, cards_width - width(clean(card_line)))
            body.append(card_line + padding + "   " + (right[row] if row < len(right) else ""))
    else:
        reading_height = min(max(3, body_height // 3), max(0, body_height - 4)) if revealed else 0
        art_height = body_height - reading_height - (1 if revealed else 0)
        body = _cards(session, deck, columns, art_height, color)
        if revealed:
            body += [""] + _reading(session, deck, columns, body_height - len(body) - 1)
    body += [""] * max(0, body_height - len(body))
    status = ("joint reading" if count == 3 else "reading") + " · h hide" if revealed else status
    lines = [clip(title, columns), ""] + body[:body_height] + [clip(status, columns), clip(footer, columns)]
    # Every resize clears formerly revealed text before repainting.
    return "\x1b[H\x1b[2J" + "\r\n".join(lines) + "\x1b[0m"


async def run(session: Session, deck: Deck, new_draw: Callable[[], Draw], day_changed: Callable[[Draw], bool], provider: str, argv: tuple[str, ...], timeout: float, question: str | None, color: bool):
    loop = asyncio.get_running_loop()
    events: asyncio.Queue[tuple[str, bytes | tuple[int, str] | None]] = asyncio.Queue()
    provider_task = None
    generation = 0
    terminal = sys.stdin.fileno()
    saved = termios.tcgetattr(terminal)
    input_buffer = b""
    last_size = None

    def repaint():
        nonlocal last_size
        size = terminal_size()
        last_size = size
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
        nonlocal input_buffer
        try:
            data = os.read(terminal, 128)
        except OSError:
            data = b""
        if not data:
            events.put_nowait(("key", b""))
            return
        keys, input_buffer = split_keys(input_buffer + data)
        for key in keys:
            events.put_nowait(("key", key))

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
                if changed != session.new_day or terminal_size() != last_size:
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
                    session.scroll += 1  # Rendering clamps to the current reading column.
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
