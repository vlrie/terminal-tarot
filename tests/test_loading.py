"""Art parsing should follow display demand without changing deck identity."""

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arcana.art import parse
from arcana.deck import load

ART = 'message\n╭🭸🭸╮\n🭲  🭲\n╰🭸🭸╯\n'


class LoadingTests(unittest.TestCase):
    def test_manifest_is_eager_but_art_parsing_is_lazy_and_cached(self):
        with patch('arcana.deck.discover', return_value=None):
            definitions = load().cards
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for card in definitions:
                (root / card.filename).write_text(ART)
            with patch('arcana.deck.parse', wraps=parse) as parser:
                deck = load(str(root))
                self.assertEqual(parser.call_count, 0)
                manifest = [(c.id, c.filename, sha256(ART.encode()).hexdigest()) for c in definitions]
                expected = sha256(json.dumps(manifest, separators=(',', ':')).encode()).hexdigest()
                self.assertEqual(deck.fingerprint, expected)
                card = deck.by_id('major-00')
                self.assertTrue(card.grid)
                self.assertEqual(parser.call_count, 1)
                self.assertIs(card.grid, card.grid)
                self.assertEqual(parser.call_count, 1)
                self.assertIs(card.inverted_grid, card.inverted_grid)
                self.assertEqual(parser.call_count, 1)
                self.assertIs(deck.by_id(card.id), card)

    def test_invalid_art_is_rejected_when_first_displayed(self):
        with patch('arcana.deck.discover', return_value=None):
            definitions = load().cards
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for card in definitions:
                (root / card.filename).write_text(ART)
            (root / definitions[1].filename).write_text(ART.replace('  ', '\x1b[2J'))
            deck = load(str(root))
            self.assertTrue(deck.cards[0].grid)
            with self.assertRaisesRegex(ValueError, 'tarot-0major_arcana01'):
                _ = deck.cards[1].grid
