"""The Beep a missed Trigger Key makes: two short tones, each starting as a red step of the
Flash begins (the schedule lives in flash.py).

Sound plays on its own thread, so the keyboard hook and the reading loop never wait for it.
"""

import threading
import time
from collections.abc import Callable

from .flash import tone_starts

TONE_HZ = 330
TONE_MS = 120


def _spawn_thread(run: Callable[[], None]) -> threading.Thread:
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


class DoubleBeep:
    def __init__(
        self,
        *,
        tone: Callable[[int, int], None],
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        spawn: Callable[[Callable[[], None]], object] = _spawn_thread,
    ):
        """`tone(hz, ms)` sounds one tone and returns when it ends."""
        self._tone = tone
        self._clock = clock
        self._sleep = sleep
        self._spawn = spawn
        self._lock = threading.Lock()
        self._latest = 0  # which Beep is the latest one
        self._sounding = threading.Lock()  # tones take turns

    def play(self) -> None:
        """Start a Beep and return at once. It replaces what is left of an earlier one: that
        one's tones not yet sounded are dropped."""
        started = self._clock()
        with self._lock:
            self._latest += 1
            mine = self._latest
        self._spawn(lambda: self._run(mine, started))

    def _run(self, mine: int, started: float) -> None:
        for at in tone_starts(started):
            wait = at - self._clock()
            if wait > 0:
                self._sleep(wait)
            with self._sounding:  # a tone still sounding from an earlier Beep finishes first
                with self._lock:
                    if self._latest != mine:
                        return  # a newer Beep has begun: this one's tones are no longer wanted
                self._tone(TONE_HZ, TONE_MS)
