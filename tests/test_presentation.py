"""Frame geometry, card alignment, and card-specific offline guidance."""

from dataclasses import replace
import re
import unittest
from unittest.mock import patch

from arcana.art import Cell
from arcana.deck import Deck, load
from arcana.display import Session, _cards, render
from arcana.draw import Draw, Pick, create
from arcana.meanings import MINOR_MEANINGS
from arcana.providers import prompt
from arcana.readings import local_reading
from arcana.text import clean, width


class PresentationTests(unittest.TestCase):
    def setUp(self):
        with patch("arcana.deck.discover", return_value=None):
            plain = load()
        grid = tuple(tuple(Cell("#", (50, 80, 120)) for _ in range(17)) for _ in range(25))
        self.deck = Deck(tuple(replace(card, grid=grid) for card in plain.cards), plain.fingerprint, None, ())
        self.draw = create(self.deck, 3, "presentation", "seeded")

    def test_frame_follows_pane_and_holds_privacy(self):
        session = Session(self.draw, reading="HIDDEN_SENTINEL")
        for columns, rows in [(24, 12), (44, 18), (80, 24), (120, 40)]:
            for color in (False, True):
                with self.subTest(size=(columns, rows), color=color):
                    output = render(session, self.deck, columns, rows, color)
                    lines = clean(output).splitlines()
                    self.assertEqual(len(lines), rows)
                    self.assertTrue(lines[0].startswith("╭") and lines[0].endswith("╮"))
                    self.assertTrue(lines[-1].startswith("╰") and lines[-1].endswith("╯"))
                    self.assertIn("✦", lines[0])
                    self.assertTrue(all(line.startswith("│") and line.endswith("│") for line in lines[1:-1]))
                    self.assertTrue(all(width(line) == columns - 1 for line in lines))
                    self.assertNotIn("HIDDEN_SENTINEL", output)
                    self.assertEqual("\x1b[38;2;153;137;180m" in output, color)
        self.assertNotIn("✦", render(session, self.deck, 12, 6, False))

    def test_each_card_and_the_whole_spread_are_centered(self):
        for count in (1, 3):
            draw = create(self.deck, count, "center", "seeded")
            lines = [clean(line) for line in _cards(Session(draw), self.deck, 100, 35, True)]
            art_row = next(line for line in lines if "#" in line)
            runs = list(re.finditer(r"#+", art_row))
            self.assertEqual(len(runs), count)
            self.assertLessEqual(abs(runs[0].start() - (100 - runs[-1].end())), 1)
            panel = 25
            group_start = (100 - (count * panel + (count - 1) * 3)) // 2
            for index, run in enumerate(runs):
                actual_center = (run.start() + run.end() - 1) / 2
                expected_center = group_start + index * (panel + 3) + (panel - 1) / 2
                self.assertLessEqual(abs(actual_center - expected_center), 0.5)
            self.assertEqual(len(lines), 35)

    def test_all_minor_cards_have_distinct_orientation_specific_meanings(self):
        pairs = [pair for suit in MINOR_MEANINGS.values() for pair in suit]
        self.assertEqual(len(pairs), 56)
        self.assertEqual(len({meaning for pair in pairs for meaning in pair}), 112)
        self.assertTrue(all(len(suit) == 14 for suit in MINOR_MEANINGS.values()))
        self.assertIn("possibilities", self.deck.by_id("cups-07").upright)
        self.assertIn("departure", self.deck.by_id("cups-08").upright)
        self.assertIn("worry", self.deck.by_id("swords-09").upright)

    def test_reading_has_a_specific_thread_action_and_question(self):
        for card_id in ("major-00", "major-13", "cups-08", "swords-09", "coins-08"):
            draw = Draw("arcana/draw/v1", self.deck.fingerprint, "seeded", None, None, (Pick(card_id, True, "Today"),))
            text = local_reading(draw, self.deck)
            self.assertIn(self.deck.by_id(card_id).reversed, text)
            self.assertIn("A small ritual\n", text)
            self.assertIn("A question to carry\n", text)
            self.assertTrue(text.endswith("?"))
            self.assertIn("reversed", text)
        model_prompt = prompt(self.draw, self.deck, "a private question")
        self.assertIn("one vivid image", model_prompt)
        self.assertIn("under five minutes", model_prompt)
        self.assertIn("without inventing details", model_prompt)
        self.assertIn("a private question", model_prompt)

