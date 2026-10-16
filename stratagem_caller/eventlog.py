"""A plain-text log of Trigger Key presses and Calls, written off the keyboard hook's path."""

import queue
import threading
from datetime import datetime
from pathlib import Path


class EventLog:
    def __init__(self, path: Path):
        self.path = path
        self._lines: queue.SimpleQueue[str | None] = queue.SimpleQueue()
        self._writer = threading.Thread(target=self._write, daemon=True)
        self._writer.start()

    def write(self, text: str) -> None:
        """Safe to call from the keyboard hook: only queues the line."""
        self._lines.put(f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}"[:-3] + f" {text}")

    def close(self) -> None:
        self._lines.put(None)
        self._writer.join(timeout=2)

    def _write(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                while (line := self._lines.get()) is not None:
                    f.write(line + "\n")
                    f.flush()
        except OSError as error:
            # Losing the log must not lose the keyboard.
            print(f"  Warning: not logging to {self.path}: {error}")
            while self._lines.get() is not None:
                pass
