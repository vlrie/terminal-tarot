import asyncio
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

from arcana.deck import load
from arcana.draw import create
from arcana.providers import ProviderError, _answer, command, interpret, prompt


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdin_prompt_no_seed_and_sanitized_output(self):
        with patch("arcana.deck.discover", return_value=None):
            deck = load()
        text = prompt(create(deck, 3, "SECRET_WORD", "seeded"), deck, "a question")
        self.assertNotIn("SECRET_WORD", text)
        self.assertIn("a question", text)
        answer = await interpret("custom", (sys.executable, "-c", "import sys; data=sys.stdin.read(); assert 'DRAW_JSON' in data; print('hello\\x1b[2J world')"), text, 2)
        self.assertEqual(answer, "hello world")

    async def test_failures_timeout_and_output_limits(self):
        programs = ["import sys; sys.exit(2)", "import time; time.sleep(2)", "print('a'*70000)", "print('')", "import sys; sys.stderr.write('x'*70000)"]
        for program in programs:
            with self.subTest(program=program):
                with self.assertRaises(ProviderError):
                    await interpret("custom", (sys.executable, "-c", program), "prompt", 0.2)
        with self.assertRaises(ProviderError):
            await interpret("custom", ("/no/such/arcana-provider",), "prompt", 1)

    async def test_cancel_kills_descendants(self):
        with tempfile.TemporaryDirectory() as root:
            pidfile = Path(root) / "pid"
            code = f"import subprocess,time,pathlib; p=subprocess.Popen([{sys.executable!r},'-c','import time; time.sleep(30)']); pathlib.Path({str(pidfile)!r}).write_text(str(p.pid)); time.sleep(30)"
            task = asyncio.create_task(interpret("custom", (sys.executable, "-c", code), "prompt", 10))
            for _ in range(100):
                if pidfile.exists():
                    break
                await asyncio.sleep(0.01)
            self.assertTrue(pidfile.exists())
            pid = int(pidfile.read_text())
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            # In containers PID 1 may leave a dead orphan as a zombie briefly.
            stat = Path(f"/proc/{pid}/stat")
            self.assertTrue(not stat.exists() or stat.read_text().split()[2] == "Z")

    async def test_codex_protocol_and_named_commands(self):
        raw = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "reflection"}}).encode()
        self.assertEqual(_answer(raw, "codex"), "reflection")
        with self.assertRaises(ProviderError):
            _answer(b"not json", "codex")
        self.assertIn("--no-session-persistence", command("claude", ()))
        self.assertIn("read-only", command("codex", ()))
