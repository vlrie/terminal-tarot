"""Read external arttime ANSI art into cells; rotate the illustration only."""

from dataclasses import dataclass, replace
import re
import unicodedata

RGB = tuple[int, int, int]
SGR = re.compile(r"\x1b\[([0-9;]*)m")


@dataclass(frozen=True)
class Cell:
    glyph: str = " "
    fg: RGB | None = None
    bg: RGB | None = None


# Paired 180-degree shapes, including the deck's legacy-computing blocks.
_PAIRS = [
    ("╭", "╯"), ("╮", "╰"), ("┌", "┘"), ("┐", "└"),
    ("├", "┤"), ("┬", "┴"), ("←", "→"), ("↑", "↓"),
    ("▁", "▔"), ("▂", "🮂"), ("▃", "🮃"), ("▄", "▀"),
    ("▌", "▐"), ("▍", "🮈"), ("▎", "🮇"), ("▏", "▕"),
    ("▖", "▝"), ("▗", "▘"), ("▙", "▜"), ("▛", "▟"),
    ("◤", "◢"), ("◥", "◣"), ("🭰", "🭵"), ("🭱", "🭴"),
    ("🭲", "🭳"), ("🭶", "🭻"), ("🭷", "🭺"), ("🭸", "🭹"),
    ("🭼", "🭾"), ("🭽", "🭿"), ("🮌", "🮍"), ("🮏", "🮎"),
    ("(", ")"), ("[", "]"), ("<", ">"), (".", "˙"),
    (",", "‘"), ("'", "‚"), ("!", "¡"), ("?", "¿"),
    ("A", "∀"), ("C", "Ɔ"), ("E", "Ǝ"), ("F", "Ⅎ"),
    ("G", "⅁"), ("J", "ſ"), ("L", "⅂"), ("M", "W"),
    ("P", "Ԁ"), ("R", "ᴚ"), ("T", "⊥"), ("U", "∩"),
    ("V", "Λ"), ("Y", "⅄"), ("1", "⇂"), ("7", "Ɫ"),
    (";", "؛"), ("£", "ⅎ"),
]
ROTATION = {a: b for a, b in _PAIRS} | {b: a for a, b in _PAIRS}
# These shapes are rotationally symmetric or intentionally approximated. Text
# without a usable one-cell inverse (e.g. B/D/K, suits) retains its glyph.
IDENTITY = set(' "#%*+-/0:5=@BDHIKNOQSXZ│┼╱╲╳▒▚○●♠♣♥♦🮖🮘')


def rotate(grid: tuple[tuple[Cell, ...], ...]) -> tuple[tuple[Cell, ...], ...]:
    return tuple(tuple(replace(c, glyph=ROTATION.get(c.glyph, c.glyph)) for c in reversed(row)) for row in reversed(grid))


def parse(source: str) -> tuple[tuple[tuple[Cell, ...], ...], list[str]]:
    """Reject all controls except SGR; require a consistent one-cell art grid."""
    lines = source.splitlines()
    if len(lines) < 3:
        raise ValueError("art file is too short")
    parsed = []
    plain = []
    for line in lines[1:]:
        fg = bg = None
        cells = []
        pos = 0
        while pos < len(line):
            match = SGR.match(line, pos)
            if match:
                values = [int(x) if x else 0 for x in match[1].split(";")]
                i = 0
                while i < len(values):
                    code = values[i]
                    if code == 0:
                        fg = bg = None
                    elif code in (38, 48) and i + 4 < len(values) and values[i + 1] == 2:
                        color = (values[i + 2], values[i + 3], values[i + 4])
                        if any(x > 255 for x in color):
                            raise ValueError("invalid RGB color")
                        if code == 38:
                            fg = color
                        else:
                            bg = color
                        i += 4
                    elif code in (39, 49):
                        if code == 39:
                            fg = None
                        else:
                            bg = None
                    else:
                        raise ValueError("unsupported SGR in art")
                    i += 1
                pos = match.end()
                continue
            c = line[pos]
            if unicodedata.category(c).startswith("C") or unicodedata.combining(c) or unicodedata.east_asian_width(c) in ("W", "F"):
                raise ValueError("unsupported control or non-single-cell glyph in art")
            cells.append(Cell(c, fg, bg))
            pos += 1
        parsed.append(cells)
        plain.append("".join(c.glyph for c in cells))
    # The external panel starts at the right edge of the first border.
    border = plain[0].find("╮")
    if border < 0:
        border = plain[-1].find("╯")
    if not plain[0].startswith("╭") or border < 3:
        raise ValueError("unrecognized arttime card border")
    size = border + 1
    if any(len(row) < size for row in parsed):
        raise ValueError("truncated art row")
    grid = tuple(tuple(row[:size]) for row in parsed)
    if any(c.glyph not in ROTATION and c.glyph not in IDENTITY for row in grid for c in row):
        raise ValueError("unreviewed glyph in artwork; use a supported deck version")
    return grid, [row[size:].strip() for row in plain]


def ansi_row(row: tuple[Cell, ...], color: bool = True) -> str:
    if not color:
        return "".join(c.glyph for c in row)
    result = []
    previous = None
    for cell in row:
        style = (cell.fg, cell.bg)
        if style != previous:
            seq = ["0"]
            if cell.fg:
                seq += ["38", "2", *map(str, cell.fg)]
            if cell.bg:
                seq += ["48", "2", *map(str, cell.bg)]
            result.append("\x1b[" + ";".join(seq) + "m")
            previous = style
        result.append(cell.glyph)
    return "".join(result) + "\x1b[0m"
