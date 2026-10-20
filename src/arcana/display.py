"""Responsive layout over measured lines, with per-session rendering caches."""

from collections import OrderedDict

from .art import ansi_row, fit
from .deck import Card, Deck
from .readings import local_reading
from .screen import Frame, Line
from .state import Session
from .text import clip, wrap


def _center(text: str, columns: int) -> Line:
    return Line.plain(clip(text, columns)).centered(columns)


def _edge(label: str, columns: int, left: str, right: str) -> str:
    remaining = max(0, columns - 2 - len(label))
    return left + "─" * (remaining // 2) + label + "─" * (remaining - remaining // 2) + right


class Renderer:
    """Build frames without changing session state. Caches stay in this process."""

    def __init__(self, deck: Deck, color: bool = True):
        self.deck = deck
        self.color = color
        self._art: OrderedDict[tuple[str, bool, int, int], tuple[Line, ...]] = OrderedDict()
        self._local_draw = None
        self._local_text = ""
        self._wrapped_key: tuple[str, int] | None = None
        self._wrapped: list[str] = []

    def _art_lines(self, card: Card, reversed: bool, columns: int, height: int) -> tuple[Line, ...]:
        if height < 1:
            return ()
        source = card.inverted_grid if reversed else card.grid
        height = min(height, len(source))
        key = (card.id, reversed, columns, height)
        if key in self._art:
            self._art.move_to_end(key)
            return self._art[key]
        grid = fit(source, columns, height)
        lines = tuple(Line(ansi_row(row, self.color), len(row)).centered(columns) for row in grid)
        self._art[key] = lines
        if len(self._art) > 128:
            self._art.popitem(last=False)
        return lines

    def cards(self, session: Session, columns: int, height: int) -> list[Line]:
        if height < 1:
            return []
        gap = 3
        count = len(session.draw.picks)
        all_fit = count == 1 or columns >= count * 10 + gap * (count - 1)
        chosen = list(range(count)) if all_fit else [session.selected]
        panel = min(25, max(1, (columns - gap * (len(chosen) - 1)) // len(chosen)))
        blocks = []
        for index in chosen:
            pick = session.draw.picks[index]
            card = self.deck.by_id(pick.card_id)
            labels = [pick.position + f"  {index + 1}/{count}", card.name, "reversed ↓" if pick.reversed else "upright ↑"]
            lines = [_center(label, panel) for label in labels]
            lines += self._art_lines(card, pick.reversed, panel, max(0, height - 3))
            blocks.append(lines)
        lines = []
        blank = Line(" " * panel, panel)
        for row in range(max(map(len, blocks))):
            pieces = [block[row] if row < len(block) else blank for block in blocks]
            lines.append(Line.join(pieces, " " * gap).centered(columns))
        lines = lines[:height]
        top = max(0, (height - len(lines)) // 2)
        return [Line()] * top + lines + [Line()] * max(0, height - top - len(lines))

    def _prose(self, session: Session, columns: int) -> list[str]:
        if session.reading:
            text = session.reading
        else:
            if self._local_draw != session.draw:
                self._local_draw = session.draw
                self._local_text = local_reading(session.draw, self.deck)
            text = self._local_text
        key = (text, columns)
        if self._wrapped_key != key:
            self._wrapped_key = key
            self._wrapped = wrap(text, columns)
        return self._wrapped

    def _reading(self, session: Session, columns: int, height: int) -> tuple[list[Line], int]:
        if height < 1:
            return [], session.scroll
        heading = "The spread, together" if len(session.draw.picks) == 3 else "Your reading"
        if height < 3:
            return [Line.plain(clip(heading + " · enlarge pane to read", columns))], session.scroll
        prose = self._prose(session, columns)
        available = height - 2
        offset = min(max(0, session.scroll), max(0, len(prose) - available))
        lines = [Line.plain(clip(heading, columns))] + [Line.plain(s) for s in prose[offset:offset + available]]
        if len(prose) > available:
            lines.append(Line.plain(clip(f"{offset + 1}–{min(offset + available, len(prose))}/{len(prose)} · ↑/↓ scroll", columns)))
        return lines, offset

    def _content(self, session: Session, columns: int, rows: int) -> tuple[list[Line], int]:
        if columns < 12 or rows < 7:
            return [Line.plain(clip("arcana · q quit", columns))], session.scroll
        title = "a r c a n a" + ("   ·   " + session.draw.date if session.draw.date else "   ·   three cards")
        revealed = session.visible and not session.private
        body_height = rows - 4
        status = "artwork only" if session.private else f"{session.status} · divination hidden"
        footer = "q quit · j/k cards" if session.private else "d reveal/hide · h hide · j/k cards · ↑/↓ text · r retry · n draw · q quit"
        if session.new_day:
            footer = "new day available · n draw · " + footer
        count = len(session.draw.picks)
        cards_width = count * 19 + (count - 1) * 3
        scroll = session.scroll
        if revealed and columns >= cards_width + 3 + 30:
            left = self.cards(session, cards_width, body_height)
            right, scroll = self._reading(session, columns - cards_width - 3, body_height)
            body = []
            for row in range(max(len(left), len(right))):
                card_line = left[row] if row < len(left) else Line()
                reading_line = right[row] if row < len(right) else Line()
                body.append(card_line.padded(cards_width) + Line("   ", 3) + reading_line)
        else:
            reading_height = min(max(3, body_height // 3), max(0, body_height - 4)) if revealed else 0
            art_height = body_height - reading_height - (1 if revealed else 0)
            body = self.cards(session, columns, art_height)
            if revealed:
                reading, scroll = self._reading(session, columns, body_height - len(body) - 1)
                body += [Line()] + reading
        body += [Line()] * max(0, body_height - len(body))
        if revealed:
            status = ("joint reading" if count == 3 else "reading") + " · h hide"
        if columns < 70:
            footer = "q quit · j/k cards" if session.private else "d read · h hide · j/k cards · q quit"
        if columns < 36:
            footer = "q quit" if session.private else "d read · h hide · q quit"
        if session.new_day and columns < 70:
            status = "new day available · n draw"
        lines = [_center(title, columns), Line()] + body[:body_height] + [_center(status, columns), _center(footer, columns)]
        return lines, scroll

    def frame(self, session: Session, columns: int, rows: int) -> Frame:
        columns, rows = max(1, columns - 1), max(1, rows)
        if columns < 23 or rows < 12:
            lines, scroll = self._content(session, columns, rows)
        else:
            inner_width = columns - 4
            body, scroll = self._content(session, inner_width, rows - 2)
            def ink(text: str) -> Line:
                styled = "\x1b[38;2;153;137;180m" + text + "\x1b[0m" if self.color else text
                return Line(styled, len(text))
            lines = [ink(_edge(" ✧  ☽  ✦  ☾  ✧ ", columns, "╭", "╮"))]
            left, right = ink("│") + Line(" ", 1), Line(" ", 1) + ink("│")
            for line in body:
                lines.append(left + line.padded(inner_width) + right)
            empty = ink("│") + Line(" " * (columns - 2), columns - 2) + ink("│")
            lines += [empty] * max(0, rows - 1 - len(lines))
            lines.append(ink(_edge(" ✧ ", columns, "╰", "╯")))
        return Frame(tuple(lines), columns, rows, scroll)


def render(session: Session, deck: Deck, columns: int, rows: int, color: bool = True) -> str:
    """One-shot full frame. Interactive sessions reuse a Renderer and ScreenWriter."""
    return Renderer(deck, color).frame(session, columns, rows).full()
