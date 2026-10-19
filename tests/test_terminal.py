"""Exercise the actual CLI inside a PTY, including bytes that must never leak."""

import fcntl
import json
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Terminal:
    def __init__(self, args, root, columns=100, rows=45):
        self.master, slave = os.openpty()
        self.slave = slave
        self.original = termios.tcgetattr(slave)
        self.resize(columns, rows)
        env = dict(os.environ, TERM="xterm-256color", PYTHONPATH=str(ROOT / "src"), XDG_DATA_HOME=str(root / "data"), XDG_CONFIG_HOME=str(root / "config"))
        self.process = subprocess.Popen([sys.executable, "-m", "arcana", *args], stdin=slave, stdout=slave, stderr=slave, env=env, start_new_session=True)
        self.output = b""

    def resize(self, columns, rows):
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        if hasattr(self, "process"):
            os.kill(self.process.pid, signal.SIGWINCH)

    def read_until(self, target, timeout=4):
        deadline = time.monotonic() + timeout
        while target not in self.output and time.monotonic() < deadline:
            self.drain(0.05)
        if target not in self.output:
            raise AssertionError(f"terminal never produced {target!r}; tail={self.output[-500:]!r}")

    def drain(self, duration=0.15):
        result = b""
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.master], [], [], max(0, deadline - time.monotonic()))
            if not ready:
                break
            try:
                data = os.read(self.master, 65536)
            except OSError:
                break
            result += data
            self.output += data
        return result

    def send(self, value):
        os.write(self.master, value)

    def close(self):
        if self.process.poll() is None:
            self.send(b"q")
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.drain(0.05)
        restored = termios.tcgetattr(self.slave)
        os.close(self.slave)
        os.close(self.master)
        return restored


class TerminalTests(unittest.TestCase):
    def test_background_hidden_reveal_hide_resize_quit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "provider.toml"
            code = "import sys; data=sys.stdin.read(); print('DIVINATION_SENTINEL')"
            config.write_text('provider="custom"\nargv=' + json.dumps([sys.executable, "-c", code]))
            terminal = Terminal(["3", "--config", str(config)], root)
            try:
                terminal.read_until(b"reading ready")
                self.assertNotIn(b"DIVINATION_SENTINEL", terminal.output)
                self.assertIsNone(terminal.process.poll())
                terminal.send(b"d")
                terminal.read_until(b"DIVINATION_SENTINEL")
                terminal.send(b"h")
                output = terminal.drain()
                self.assertIn(b"\x1b[2J", output)
                self.assertNotIn(b"DIVINATION_SENTINEL", output)
                terminal.resize(38, 15)
                self.assertNotIn(b"DIVINATION_SENTINEL", terminal.drain())
                terminal.send(b"d")
                self.assertIn(b"DIVINATION_SENTINEL", terminal.drain())
                terminal.send(b"n")
                output = terminal.drain(0.3)
                self.assertNotIn(b"DIVINATION_SENTINEL", output)
                terminal.send(b"q")
                self.assertEqual(terminal.process.wait(timeout=3), 0)
            finally:
                restored = terminal.close()
            self.assertEqual(restored, terminal.original)
            self.assertIn(b"\x1b[?1049l", terminal.output)

    def test_private_never_starts_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "started"
            config = root / "provider.toml"
            config.write_text('provider="custom"\nargv=' + json.dumps([sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch(); print('SECRET')"]))
            terminal = Terminal(["1", "--private", "--config", str(config)], root)
            try:
                terminal.read_until(b"artwork only")
                terminal.send(b"d")
                terminal.drain()
                self.assertFalse(marker.exists())
                self.assertNotIn(b"SECRET", terminal.output)
            finally:
                terminal.close()

    def test_single_card_ritual_word_never_echoes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            terminal = Terminal(["1", "--ritual", "--date", "2026-10-19"], root)
            try:
                terminal.read_until(b"Think of a word")
                terminal.send(b"UNSPOKEN_SEED_938\r")
                terminal.read_until(b"divination hidden")
                self.assertNotIn(b"UNSPOKEN_SEED_938", terminal.output)
                terminal.send(b"q")
                self.assertEqual(terminal.process.wait(timeout=3), 0)
                for path in root.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(b"UNSPOKEN_SEED_938", path.read_bytes())
            finally:
                terminal.close()

    def test_ritual_escape_restores_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            terminal = Terminal(["1", "--ritual"], Path(directory))
            try:
                terminal.read_until(b"Think of a word")
                terminal.send(b"\x1b")
                self.assertEqual(terminal.process.wait(timeout=3), 130)
            finally:
                restored = terminal.close()
            self.assertEqual(restored, terminal.original)

    def test_pipe_is_finite_and_private(self):
        result = subprocess.run([sys.executable, "-m", "arcana", "3", "--provider", "custom", "--private"], env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), capture_output=True, timeout=4)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(b"\x1b", result.stdout)
        self.assertIn(b"Situation", result.stdout)

    def test_batched_hide_and_quit(self):
        with tempfile.TemporaryDirectory() as directory:
            terminal = Terminal(["3"], Path(directory))
            try:
                terminal.read_until(b"divination hidden")
                terminal.send(b"d")
                self.assertIn(b"The spread, together", terminal.drain())
                terminal.send(b"hq")
                self.assertEqual(terminal.process.wait(timeout=1), 0)
                self.assertNotIn(b"The spread, together", terminal.drain())
            finally:
                terminal.close()

    def test_resize_keeps_artwork_and_one_joint_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requests = root / "requests"
            config = root / "provider.toml"
            code = f"import sys,json,pathlib; text=sys.stdin.read(); cards=json.loads(next(s for s in text.splitlines() if s.startswith('DRAW_JSON: '))[11:]); assert len(cards)==3; pathlib.Path({str(requests)!r}).open('a').write('one\\n'); print('JOINT_SENTINEL')"
            config.write_text('provider="custom"\nargv=' + json.dumps([sys.executable, "-c", code]))
            terminal = Terminal(["3", "--config", str(config)], root, columns=120, rows=40)
            try:
                terminal.read_until(b"reading ready")
                terminal.send(b"d")
                terminal.read_until(b"JOINT_SENTINEL")
                for columns, rows in [(80, 24), (44, 18), (120, 40)]:
                    terminal.resize(columns, rows)
                    output = terminal.drain(0.2)
                    self.assertIn(b"JOINT_SENTINEL", output)
                    self.assertIn(b"Situation", output)
                    self.assertIn(b"Tension", output)
                    self.assertIn(b"Invitation", output)
                    self.assertIn("╭".encode(), output)  # artwork survives short panes
                    self.assertIn(b"The spread, together", output)
                terminal.send(b"h")
                terminal.drain()
                terminal.resize(80, 24)
                self.assertNotIn(b"JOINT_SENTINEL", terminal.drain())
                self.assertEqual(requests.read_text(), "one\n")
            finally:
                terminal.close()
