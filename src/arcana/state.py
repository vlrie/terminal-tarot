"""Session state and keyboard transitions, independent of terminal I/O."""

from dataclasses import dataclass, replace
from enum import Enum, auto

from .draw import Draw


@dataclass(frozen=True)
class Session:
    draw: Draw
    selected: int = 0
    visible: bool = False
    private: bool = False
    reading: str = ""
    status: str = "local reflection"
    new_day: bool = False
    scroll: int = 0


class Action(Enum):
    NONE = auto()
    QUIT = auto()
    RETRY = auto()
    DRAW = auto()


@dataclass(frozen=True)
class Transition:
    session: Session
    action: Action = Action.NONE


def on_key(session: Session, key: bytes, can_retry: bool) -> Transition:
    """Return a new state and any requested I/O action; never mutate the input."""
    if key in (b"", b"q", b"\x03", b"\x04"):
        return Transition(session, Action.QUIT)
    if key == b"d" and not session.private:
        return Transition(replace(session, visible=not session.visible))
    if key == b"h" and session.visible:
        return Transition(replace(session, visible=False))
    if key in (b"j", b"k", b"\x1b[C", b"\x1b[D"):
        step = 1 if key in (b"j", b"\x1b[C") else -1
        selected = (session.selected + step) % len(session.draw.picks)
        if selected != session.selected:
            return Transition(replace(session, selected=selected))
    if session.visible and not session.private:
        if key == b"\x1b[B":
            return Transition(replace(session, scroll=session.scroll + 1))
        if key == b"\x1b[A" and session.scroll:
            return Transition(replace(session, scroll=max(0, session.scroll - 1)))
    if key == b"r" and can_retry and not session.private:
        return Transition(replace(session, reading="", scroll=0, status="reading in progress"), Action.RETRY)
    if key == b"n":
        return Transition(replace(session, visible=False, reading="", scroll=0, selected=0, status="local reflection"), Action.DRAW)
    return Transition(session)
