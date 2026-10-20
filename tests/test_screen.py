"""Apply emitted terminal commands to check the final screen, including erasure."""

from dataclasses import replace
import re
import unittest
from unittest.mock import patch

from arcana.deck import load
from arcana.display import Renderer
from arcana.draw import create
from arcana.screen import Frame, Line, ScreenWriter
from arcana.state import Action, Session, on_key


class TerminalGrid:
    """Small test terminal for cursor positioning, SGR, erase-line, and clear."""

    CSI = re.compile(r'\x1b\[([0-9;?]*)([@-~])')

    def __init__(self, columns, rows):
        self.columns, self.rows = columns, rows
        self.cells = [[' '] * columns for _ in range(rows)]
        self.x = self.y = 0

    def feed(self, text):
        index = 0
        while index < len(text):
            match = self.CSI.match(text, index)
            if match:
                args, command = match.groups()
                if command == 'H':
                    positions = [int(s or 1) for s in args.split(';')] if args else [1, 1]
                    self.y = positions[0] - 1
                    self.x = (positions[1] if len(positions) > 1 else 1) - 1
                elif command == 'J' and args == '2':
                    self.cells = [[' '] * self.columns for _ in range(self.rows)]
                elif command == 'K':
                    self.cells[self.y][self.x:] = [' '] * (self.columns - self.x)
                index = match.end()
                continue
            char = text[index]
            if char == '\r':
                self.x = 0
            elif char == '\n':
                self.y += 1
            else:
                self.cells[self.y][self.x] = char
                self.x += 1
            index += 1

    def snapshot(self):
        return '\n'.join(''.join(row) for row in self.cells)


class ScreenTests(unittest.TestCase):
    def test_diff_erases_shortened_and_removed_rows(self):
        writer = ScreenWriter()
        before = Frame((Line.plain('PRIVATE_SENTINEL'), Line.plain('unchanged'), Line.plain('MORE_SECRET')), 20, 3)
        after = Frame((Line.plain('safe'), Line.plain('unchanged')), 20, 3)
        terminal = TerminalGrid(21, 3)
        terminal.feed(writer.paint(before))
        delta = writer.paint(after)
        self.assertNotIn('\x1b[2J', delta)
        self.assertNotIn('unchanged', delta)
        self.assertEqual(delta.count('\x1b[K'), 2)
        terminal.feed(delta)
        self.assertNotIn('SECRET', terminal.snapshot())
        self.assertNotIn('PRIVATE', terminal.snapshot())
        self.assertEqual(terminal.snapshot().splitlines(), ['safe' + ' ' * 17, 'unchanged' + ' ' * 12, ' ' * 21])
        self.assertEqual(writer.paint(after), '')
        resized = Frame(after.lines, 25, 4)
        self.assertIn('\x1b[2J', writer.paint(resized))

    def test_reveal_hide_and_scroll_match_full_screen_output(self):
        with patch('arcana.deck.discover', return_value=None):
            deck = load()
        draw = create(deck, 3, 'screen', 'seeded')
        renderer, writer = Renderer(deck), ScreenWriter()
        terminal = TerminalGrid(120, 40)
        hidden = Session(draw, reading='PRIVATE_SENTINEL ' + 'a longer reading. ' * 100)
        sessions = [hidden, replace(hidden, visible=True), replace(hidden, visible=True, scroll=3), hidden]
        for session in sessions:
            frame = renderer.frame(session, 120, 40)
            terminal.feed(writer.paint(frame))
            reference = TerminalGrid(120, 40)
            reference.feed(frame.full())
            self.assertEqual(terminal.snapshot(), reference.snapshot())
        self.assertNotIn('PRIVATE_SENTINEL', terminal.snapshot())

    def test_hidden_provider_completion_changes_only_status(self):
        with patch('arcana.deck.discover', return_value=None):
            deck = load()
        state = Session(create(deck, 3, 'status', 'seeded'), status='reading in progress')
        renderer, writer = Renderer(deck), ScreenWriter()
        writer.paint(renderer.frame(state, 120, 40))
        delta = writer.paint(renderer.frame(replace(state, reading='PRIVATE_SENTINEL', status='reading ready'), 120, 40))
        self.assertEqual(delta.count('\x1b[K'), 1)
        self.assertNotIn('PRIVATE_SENTINEL', delta)
        self.assertLess(len(delta.encode()), 250)

    def test_state_transitions_are_pure_and_ignore_irrelevant_keys(self):
        with patch('arcana.deck.discover', return_value=None):
            deck = load()
        state = Session(create(deck, 3, 'keys', 'seeded'))
        for key in (b'x', b'h', b'r', b'\x1b[B'):
            transition = on_key(state, key, False)
            self.assertIs(transition.session, state)
            self.assertEqual(transition.action, Action.NONE)
        visible = on_key(state, b'd', True).session
        self.assertTrue(visible.visible)
        self.assertFalse(state.visible)
        new_draw = on_key(visible, b'n', True)
        self.assertEqual(new_draw.action, Action.DRAW)
        self.assertFalse(new_draw.session.visible)
        self.assertTrue(visible.visible)
        private = replace(visible, private=True)
        self.assertIs(on_key(private, b'd', True).session, private)
        self.assertEqual(on_key(private, b'r', True).action, Action.NONE)
