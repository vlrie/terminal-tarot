"""Terminal-safe text and cell widths (no terminal commands from input)."""

import re
import unicodedata

# OSC, DCS and other strings must be removed before CSI/control bytes.
_STRINGS = re.compile(r"\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)|[PX^_].*?\x1b\\)", re.S)
_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def clean(value: str) -> str:
    value = _CSI.sub("", _STRINGS.sub("", value))
    return "".join(c for c in value if c == "\n" or not unicodedata.category(c).startswith("C"))


def width(value: str) -> int:
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in value)


def clip(value: str, limit: int) -> str:
    result = ""
    used = 0
    for c in value:
        size = width(c)
        if used + size > limit:
            break
        result += c
        used += size
    return result


def wrap(value: str, limit: int) -> list[str]:
    """Wrap sanitized prose by display cells, including unbroken wide words."""
    if limit < 1:
        return []
    lines = []
    for paragraph in clean(value).splitlines():
        line = ""
        for word in paragraph.split():
            if line and width(line + " " + word) > limit:
                lines.append(line)
                line = ""
            while width(word) > limit:
                part = clip(word, limit)
                if line:
                    lines.append(line)
                    line = ""
                # A wide glyph cannot fit in a single-column pane. Consume it
                # with a visible placeholder rather than looping forever.
                if not part:
                    lines.append("?")
                    word = word[1:]
                else:
                    lines.append(part)
                    word = word[len(part):]
            if word:
                line = line + " " + word if line else word
        if line or not paragraph.strip():
            lines.append(line)
    return lines
