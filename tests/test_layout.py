"""Layout transitions must preserve both the draw and the hidden reading."""

from dataclasses import replace
import os
import unittest
from unittest.mock import patch

from arcana.art import Cell, fit, rotate
from arcana.deck import Deck, load
from arcana.display import Renderer, Session, local_reading, render
from arcana.terminal import terminal_size
from arcana.draw import create
from arcana.providers import prompt
from arcana.text import clean, width


class LayoutTests(unittest.TestCase):
    def setUp(self):
        # Original synthetic art keeps these tests independent of external assets.
        with patch("arcana.deck.discover", return_value=None):
            plain = load()
        grid = tuple(tuple(Cell("#", (x * 10, y * 10, 0)) for x in range(17)) for y in range(25))
        self.deck = Deck(tuple(replace(card, artwork=grid) for card in plain.cards), plain.fingerprint, None, ())
        self.draw = create(self.deck, 3, "layout", "seeded")

    def test_art_fits_and_restores_without_mutating_source(self):
        grid = self.deck.cards[0].grid
        for columns, rows in [(17, 25), (11, 14), (30, 50), (1, 1), (0, 5)]:
            fitted = fit(grid, columns, rows)
            self.assertLessEqual(len(fitted), rows)
            self.assertTrue(all(len(row) <= columns for row in fitted))
            source_cells = {cell for row in grid for cell in row}
            self.assertTrue(all(cell in source_cells for row in fitted for cell in row))
        self.assertEqual(fit(grid, 40, 60), grid)
        self.assertEqual(fit(rotate(grid), 17, 25), rotate(grid))
        self.assertEqual(fit(grid, 11, 14)[0][0], grid[0][0])
        self.assertEqual(fit(grid, 11, 14)[-1][-1], grid[-1][-1])

    def test_art_survives_normal_short_panes(self):
        session = Session(self.draw)
        for columns, rows in [(80, 24), (44, 18), (24, 16)]:
            with self.subTest(size=(columns, rows)):
                text = clean(render(session, self.deck, columns, rows))
                self.assertIn("#", text)
                self.assertIn("Situation", text)
                if columns >= 43:
                    self.assertIn("Tension", text)
                    self.assertIn("Invitation", text)
        self.assertEqual(session.draw, self.draw)

    def test_visible_layout_reflows_without_losing_cards_or_privacy(self):
        session = Session(self.draw, visible=True, reading="JOINED_SENTINEL " + "A long joined reflection. " * 30)
        for columns, rows in [(120, 40), (80, 24), (44, 18), (24, 16), (120, 40)]:
            with self.subTest(size=(columns, rows)):
                text = clean(render(session, self.deck, columns, rows))
                self.assertIn("#", text)
                self.assertIn("JOINED_SENTINEL", text)
                self.assertLessEqual(len(text.splitlines()), rows)
                self.assertTrue(all(width(line) <= columns - 1 for line in text.splitlines()))
        session = replace(session, visible=False)
        self.assertNotIn("JOINED_SENTINEL", render(session, self.deck, 120, 40))
        session = replace(session, private=True, visible=True)
        self.assertNotIn("JOINED_SENTINEL", render(session, self.deck, 120, 40))
        self.assertEqual(session.draw, self.draw)

    def test_reading_scroll_reclamps_after_resize(self):
        session = Session(self.draw, visible=True, reading="words " * 1000, scroll=10000)
        renderer = Renderer(self.deck)
        frame = renderer.frame(session, 120, 40)
        self.assertLess(frame.scroll, 10000)
        self.assertEqual(session.scroll, 10000)  # Rendering cannot mutate state.
        session = replace(session, reading="short")
        frame = renderer.frame(session, 80, 24)
        self.assertEqual(frame.scroll, 0)
        self.assertEqual(session.scroll, 10000)

    def test_actual_terminal_size_overrides_stale_environment(self):
        with patch.dict(os.environ, COLUMNS="200", LINES="80"), patch("arcana.terminal.os.get_terminal_size", return_value=os.terminal_size((44, 18))):
            self.assertEqual(terminal_size(), (44, 18))

    def test_joint_reading_uses_every_card_and_orientation(self):
        text = local_reading(self.draw, self.deck)
        self.assertIn("Read together", text)
        self.assertIn("respond", text)
        for pick in self.draw.picks:
            self.assertIn(self.deck.by_id(pick.card_id).name, text)
            self.assertIn(self.deck.by_id(pick.card_id).meaning(pick.reversed), text)
        request = prompt(self.draw, self.deck, None)
        self.assertIn("one cohesive reading", request)
        self.assertIn("how the tension challenges the situation", request)
        single = create(self.deck, 1, "layout", "seeded", "2026-10-19", "UTC")
        self.assertNotIn("three separate", prompt(single, self.deck, None))
