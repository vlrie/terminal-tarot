import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arcana.art import Cell, ansi_row, parse, rotate
from arcana.deck import load
from arcana.display import Session, render
from arcana.draw import create
from arcana.storage import daily, load_config
from arcana.text import clean, width, wrap


def daily_worker(root):
    with patch("arcana.deck.discover", return_value=None):
        deck = load()
    return daily(deck, "2026-10-19", "Asia/Dubai", False, Path(root)).public()


class CoreTests(unittest.TestCase):
    def setUp(self):
        with patch("arcana.deck.discover", return_value=None):
            self.deck = load()

    def test_canonical_deck_and_golden_vector(self):
        self.assertEqual(len(self.deck.cards), 78)
        draw = create(self.deck, 3, "lantern", "seeded")
        self.assertEqual([(p.card_id, p.reversed) for p in draw.picks], [("coins-09", False), ("cups-06", True), ("coins-07", False)])
        self.assertEqual(draw, create(self.deck, 3, " lantern ", "seeded"))
        self.assertNotIn("lantern", json.dumps(draw.public()))

    def test_unicode_daily_and_unique_draws(self):
        self.assertEqual(create(self.deck, 3, "café", "seeded"), create(self.deck, 3, "cafe\u0301", "seeded"))
        self.assertNotEqual(create(self.deck, 1, "word", "seeded", "2026-10-19", "UTC"), create(self.deck, 1, "word", "seeded", "2026-10-20", "UTC"))
        for i in range(100):
            draw = create(self.deck, 3, str(i), "seeded", upright_only=True)
            self.assertEqual(len({p.card_id for p in draw.picks}), 3)
            self.assertFalse(any(p.reversed for p in draw.picks))

    def test_daily_concurrent_and_corrupt_state(self):
        with tempfile.TemporaryDirectory() as root:
            with multiprocessing.get_context("fork").Pool(4) as pool:
                draws = pool.map(daily_worker, [root] * 8)
            self.assertTrue(all(d == draws[0] for d in draws))
            path = Path(root) / "daily.json"
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.write_text("not json")
            with self.assertRaises(ValueError):
                daily_worker(root)
            self.assertEqual(path.read_text(), "not json")

    def test_art_rotation_and_ansi_security(self):
        source = 'message\n\x1b[38;2;10;20;30m╭▂▂╮ TITLE\n╰🮂🮂╯ word'
        grid, panel = parse(source)
        self.assertEqual(panel, ["TITLE", "word"])
        inverted = rotate(grid)
        self.assertEqual(rotate(inverted), grid)
        self.assertEqual(inverted[0][1].glyph, "▂")
        self.assertEqual(grid[0][0].fg, (10, 20, 30))
        self.assertNotIn("TITLE", ansi_row(grid[0]))
        with self.assertRaises(ValueError):
            parse(source.replace("TITLE", "\x1b[2J"))
        with self.assertRaises(ValueError):
            parse(source.replace("▂", "🙂"))

    def test_all_local_art(self):
        path = Path.home() / ".local/share/arttime/textart"
        if not path.is_dir():
            self.skipTest("local arttime deck is optional")
        deck = load(str(path))
        self.assertEqual(len(deck.cards), 78)
        for card in deck.cards:
            with self.subTest(card=card.id):
                self.assertEqual(len(card.grid), 25)
                self.assertEqual(len(card.grid[0]), 17)
                self.assertEqual(rotate(rotate(card.grid)), card.grid)
                self.assertTrue(card.source_sha256)

    def test_render_privacy_resize_and_width(self):
        session = Session(create(self.deck, 3, "word", "seeded"), reading="SECRET_SENTINEL")
        for columns, rows in [(1, 1), (10, 5), (30, 12), (80, 24), (120, 50)]:
            result = render(session, self.deck, columns, rows)
            self.assertNotIn("SECRET_SENTINEL", result)
            self.assertLessEqual(len(clean(result).splitlines()), rows)
            self.assertTrue(all(width(line) <= max(1, columns - 1) for line in clean(result).splitlines()))
        session.visible = True
        self.assertIn("SECRET_SENTINEL", render(session, self.deck, 120, 40))
        session.private = True
        self.assertNotIn("SECRET_SENTINEL", render(session, self.deck, 120, 40))

    def test_terminal_text_sanitization(self):
        self.assertEqual(clean("a\x1b]52;c;secret\x07b\x1b[2Jc\x07"), "abc")
        self.assertTrue(all(width(s) <= 4 for s in wrap("你好你好你好abcdefg", 4)))

    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "config.toml"
            path.write_text('provider="custom"\nargv=["echo", "hello"]\ntimeout=2')
            self.assertEqual(load_config(path).argv, ("echo", "hello"))
            for bad in ['argv="echo unsafe"', 'timeout=-1', 'unknown="value"']:
                path.write_text(bad)
                with self.assertRaises(ValueError):
                    load_config(path)
