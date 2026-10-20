"""Coordinate state, providers, and terminal events without doing layout work."""

import asyncio
import contextlib
from dataclasses import dataclass, replace
from enum import Enum, auto
import os
import signal
from typing import Callable

from .deck import Deck
from .display import Renderer
from .draw import Draw
from .providers import ProviderError, interpret, prompt
from .screen import ScreenWriter
from .state import Action, Session, on_key
from .terminal import Terminal, split_keys, terminal_size


@dataclass(frozen=True)
class Key:
    data: bytes


@dataclass(frozen=True)
class ReadingResult:
    generation: int
    text: str
    failed: bool = False


class Signal(Enum):
    RESIZE = auto()
    STOP = auto()


async def run(session: Session, deck: Deck, new_draw: Callable[[], Draw], day_changed: Callable[[Draw], bool], provider: str, argv: tuple[str, ...], timeout: float, question: str | None, color: bool):
    loop = asyncio.get_running_loop()
    events: asyncio.Queue[Key | ReadingResult | Signal] = asyncio.Queue()
    renderer, screen = Renderer(deck, color), ScreenWriter()
    provider_task = None
    generation = 0
    input_buffer = b""
    last_size = None
    resize_pending = False
    can_request = provider != "none" and not session.private

    def repaint(terminal: Terminal):
        nonlocal session, last_size
        last_size = terminal_size()
        frame = renderer.frame(session, last_size.columns, last_size.lines)
        session = replace(session, scroll=frame.scroll)
        terminal.write(screen.paint(frame))

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
            await events.put(ReadingResult(request_id, answer))
        except ProviderError as error:
            await events.put(ReadingResult(request_id, str(error), failed=True))

    def start():
        nonlocal provider_task
        if can_request:
            provider_task = asyncio.create_task(request(generation, session.draw))

    def input_ready():
        nonlocal input_buffer
        try:
            data = os.read(terminal.fd, 128)
        except OSError:
            data = b""
        if not data:
            events.put_nowait(Signal.STOP)
            return
        keys, input_buffer = split_keys(input_buffer + data)
        for key in keys:
            events.put_nowait(Key(key))

    def resize():
        nonlocal resize_pending
        if not resize_pending:
            resize_pending = True
            events.put_nowait(Signal.RESIZE)

    try:
        with Terminal() as terminal:
            loop.add_reader(terminal.fd, input_ready)
            loop.add_signal_handler(signal.SIGWINCH, resize)
            loop.add_signal_handler(signal.SIGTERM, lambda: events.put_nowait(Signal.STOP))
            try:
                if can_request:
                    session = replace(session, status="reading in progress")
                repaint(terminal)  # Paint cards before starting any provider work.
                start()
                while True:
                    try:
                        event = await asyncio.wait_for(events.get(), 1)
                    except TimeoutError:
                        changed = day_changed(session.draw)
                        if changed != session.new_day or terminal_size() != last_size:
                            session = replace(session, new_day=changed)
                            repaint(terminal)
                        continue
                    if event == Signal.STOP:
                        break
                    if event == Signal.RESIZE:
                        resize_pending = False
                        if terminal_size() != last_size:
                            repaint(terminal)
                        continue
                    if isinstance(event, ReadingResult):
                        if event.generation == generation:
                            session = replace(session, status=event.text) if event.failed else replace(session, reading=event.text, status="reading ready")
                            repaint(terminal)
                        continue
                    assert isinstance(event, Key)
                    transition = on_key(session, event.data, can_request)
                    if transition.action == Action.QUIT:
                        break
                    if transition.session == session and transition.action == Action.NONE:
                        continue
                    session = transition.session
                    if transition.action in (Action.RETRY, Action.DRAW):
                        generation += 1
                        # Hiding a previous reading takes effect before cleanup.
                        repaint(terminal)
                        await cancel()
                        if transition.action == Action.DRAW:
                            session = replace(session, draw=new_draw(), new_day=False, status="reading in progress" if can_request else "local reflection")
                        start()
                    repaint(terminal)
            finally:
                loop.remove_reader(terminal.fd)
                loop.remove_signal_handler(signal.SIGWINCH)
                loop.remove_signal_handler(signal.SIGTERM)
    finally:
        # The context manager restores the terminal before child cleanup waits.
        await cancel()
