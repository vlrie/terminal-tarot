"""Measured lines and terminal frame diffs. ANSI is emitted only at the edge."""

from dataclasses import dataclass

from .text import width

RESET = "\x1b[0m"
CLEAR = "\x1b[H\x1b[2J"


@dataclass(frozen=True, slots=True)
class Line:
    text: str = ""
    columns: int = 0

    @classmethod
    def plain(cls, text: str) -> "Line":
        return cls(text, width(text))

    def __add__(self, other: "Line") -> "Line":
        return Line(self.text + other.text, self.columns + other.columns)

    def padded(self, columns: int) -> "Line":
        extra = max(0, columns - self.columns)
        return Line(self.text + " " * extra, self.columns + extra)

    def centered(self, columns: int) -> "Line":
        extra = max(0, columns - self.columns)
        left = extra // 2
        return Line(" " * left + self.text + " " * (extra - left), self.columns + extra)

    @classmethod
    def join(cls, lines: list["Line"], separator: str = "") -> "Line":
        return cls(separator.join(line.text for line in lines), sum(line.columns for line in lines) + width(separator) * max(0, len(lines) - 1))


@dataclass(frozen=True)
class Frame:
    lines: tuple[Line, ...]
    columns: int
    height: int
    scroll: int = 0

    def full(self) -> str:
        return CLEAR + "\r\n".join(line.text for line in self.lines) + RESET


class ScreenWriter:
    """Produce a full initial/resize frame, otherwise overwrite only changed rows."""

    def __init__(self):
        self.previous: Frame | None = None

    def paint(self, frame: Frame) -> str:
        previous = self.previous
        self.previous = frame
        if previous is None or (frame.columns, frame.height) != (previous.columns, previous.height):
            return frame.full()
        commands = []
        for row in range(max(len(previous.lines), len(frame.lines))):
            before = previous.lines[row].text if row < len(previous.lines) else ""
            after = frame.lines[row].text if row < len(frame.lines) else ""
            if before != after:
                # Reset before painting and before erasing: art backgrounds must
                # never leak into cleared private-text regions or the border.
                commands.append(f"\x1b[{row + 1};1H" + RESET + after + RESET + "\x1b[K")
        return "".join(commands)
