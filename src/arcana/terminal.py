"""POSIX terminal setup, size, and incremental key decoding."""

import os
import shutil
import sys
import termios
import tty


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
    """Prefer the pane itself over possibly stale COLUMNS/LINES variables."""
    try:
        return os.get_terminal_size(sys.stdout.fileno())
    except (OSError, ValueError):
        return shutil.get_terminal_size()


class Terminal:
    """Restore terminal attributes and screen even when rendering or I/O fails."""

    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.saved = termios.tcgetattr(self.fd)

    def __enter__(self) -> "Terminal":
        try:
            tty.setcbreak(self.fd)
            self.write("\x1b[?1049h\x1b[?25l")
        except BaseException:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)
            raise
        return self

    def write(self, commands: str):
        if commands:
            sys.stdout.write(commands)
            sys.stdout.flush()

    def __exit__(self, *_):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)
        self.write("\x1b[0m\x1b[2J\x1b[H\x1b[?25h\x1b[?1049l")
