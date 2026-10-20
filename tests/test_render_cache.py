"""Repeated frames reuse art and prose while reflecting relevant changes."""

from dataclasses import replace
import unittest
from unittest.mock import patch

from arcana.art import Cell, ansi_row
from arcana.deck import Deck, load
from arcana.display import Renderer
from arcana.draw import create
from arcana.state import Session
from arcana.text import wrap


class RenderCacheTests(unittest.TestCase):
    def setUp(self):
        with patch('arcana.deck.discover', return_value=None):
            deck = load()
        art = tuple(tuple(Cell('#') for _ in range(17)) for _ in range(25))
        self.deck = Deck(tuple(replace(card, artwork=art) for card in deck.cards), deck.fingerprint, None, ())
        self.state = Session(create(self.deck, 3, 'cache', 'seeded'))

    def test_status_changes_reuse_art_and_scroll_changes_reuse_wrapping(self):
        renderer = Renderer(self.deck)
        with patch('arcana.display.ansi_row', wraps=ansi_row) as encode:
            initial = renderer.frame(self.state, 120, 40)
            encoded = encode.call_count
            self.assertGreater(encoded, 0)
            renderer.frame(replace(self.state, status='reading ready'), 120, 40)
            self.assertEqual(encode.call_count, encoded)
            self.assertEqual(renderer.frame(self.state, 120, 40), initial)
        visible = replace(self.state, visible=True, reading='A fairly long reading. ' * 100)
        with patch('arcana.display.wrap', wraps=wrap) as wrapping:
            renderer.frame(visible, 120, 40)
            self.assertEqual(wrapping.call_count, 1)
            renderer.frame(replace(visible, scroll=2), 120, 40)
            self.assertEqual(wrapping.call_count, 1)
            renderer.frame(visible, 121, 40)
            self.assertEqual(wrapping.call_count, 2)
            renderer.frame(replace(visible, reading='A new answer.'), 121, 40)
            self.assertEqual(wrapping.call_count, 3)
            renderer.frame(replace(visible, visible=False), 121, 40)
            self.assertEqual(wrapping.call_count, 3)

    def test_metadata_only_layout_never_parses_undisplayed_art(self):
        # Invalid artwork is harmless in a view with no space to render it.
        deck = replace(self.deck, cards=tuple(replace(card, artwork=b'not valid art') for card in self.deck.cards))
        renderer = Renderer(deck)
        frame = renderer.frame(self.state, 20, 7)
        self.assertIn('Situation', frame.full())
        with self.assertRaises(ValueError):
            renderer.frame(self.state, 120, 40)
