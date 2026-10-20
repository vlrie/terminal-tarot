"""Run with PYTHONPATH=src uv run --no-project python benchmarks/benchmark.py."""

import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import replace

from arcana.deck import load
from arcana.display import Renderer, render
from arcana.draw import create
from arcana.screen import ScreenWriter
from arcana.state import Session


def median_ms(operation, samples=100):
    durations = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        operation()
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    return round(statistics.median(durations), 3)


def main():
    deck = load()
    draw = create(deck, 3, 'benchmark', 'seeded')
    hidden, visible = Session(draw), Session(draw, visible=True)
    renderer = Renderer(deck)
    renderer.frame(visible, 120, 40)  # Warm the artwork and wrapping caches.
    writer = ScreenWriter()
    initial = renderer.frame(hidden, 120, 40)
    full = writer.paint(initial)
    ready = renderer.frame(replace(hidden, reading='Private sample text', status='reading ready'), 120, 40)
    delta = writer.paint(ready)
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root / 'src'))
    report = {
        'python': platform.python_version(),
        'platform': platform.system(),
        'external_artwork': deck.art_dir is not None,
        'median_ms': {
            'deck_manifest': median_ms(load, 20),
            'one_shot_visible_frame': median_ms(lambda: render(visible, deck, 120, 40)),
            'cached_visible_frame': median_ms(lambda: renderer.frame(visible, 120, 40)),
            'unchanged_frame_diff': median_ms(lambda: writer.paint(ready)),
            'cli_json_startup': median_ms(lambda: subprocess.run(
                [sys.executable, '-m', 'arcana', '3', '--json'], cwd=root,
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True), 10),
        },
        'bytes': {'initial_hidden_frame': len(full.encode()), 'hidden_reading_ready_update': len(delta.encode())},
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
