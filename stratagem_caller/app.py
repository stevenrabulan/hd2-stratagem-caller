"""Listen for the Call Key, Trigger Keys and Direct Keys, and make Calls."""

import random
import threading
import time
import winsound
from collections.abc import Callable
from pathlib import Path

from . import winkeys

winkeys.make_dpi_aware()

import keyboard  # noqa: E402
import mss  # noqa: E402
import numpy as np  # noqa: E402

from .arming import ArmingWindow  # noqa: E402
from .eventlog import EventLog  # noqa: E402
from .reader import REFERENCE_HEIGHT, read_menu, region_size  # noqa: E402
from .router import KeyEvent, KeyRouter  # noqa: E402
from .settings import Settings, load  # noqa: E402
from .winkeys import Key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "logs" / "stratagem_caller.log"

# Reading the menu before it has started to slide in is wasted work.
FIRST_READING_DELAY = 0.15
READING_INTERVAL = 0.02


class App:
    def __init__(self, settings: Settings, log: Callable[[str], None] = lambda text: None):
        self.settings = settings
        self.call_key = Key.named(settings.call_key)
        self.direction_keys = {d: Key.named(k) for d, k in settings.direction_keys.items()}

        # Set while the tool is typing, so it doesn't react to its own keys.
        self._sending = threading.Event()
        self._send_lock = threading.Lock()
        self.router = KeyRouter(
            call_key=self.call_key,
            direct_keys={Key.named(k): code for k, code in settings.direct_keys.items()},
            trigger_keys={Key.named(k): slot for k, slot in settings.trigger_keys.items()},
            window_title=settings.window_title,
            arming_length=settings.arming_window_ms / 1000,
            clock=time.monotonic,
            foreground_title=winkeys.foreground_title,
            is_sending=self._sending.is_set,
            log=log,
        )

    # --- keyboard hook (must return quickly; True lets the key through) ---

    def on_event(self, event: keyboard.KeyboardEvent) -> bool:
        decision = self.router.handle(
            KeyEvent(event.scan_code, event.is_keypad, event.event_type, event.time)
        )
        if decision.start_watching is not None:
            threading.Thread(
                target=self._watch_menu, args=(decision.start_watching,), daemon=True
            ).start()
        if decision.direct_code is not None:
            threading.Thread(
                target=self._direct_call, args=(decision.direct_code,), daemon=True
            ).start()
        return decision.let_through

    # --- worker threads ---

    def _watch_menu(self, window: ArmingWindow) -> None:
        outcome = None
        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            width, height = region_size(monitor["height"])
            area = {"left": monitor["left"], "top": monitor["top"], "width": width, "height": height}
            time.sleep(FIRST_READING_DELAY)
            while outcome is None:
                region = np.asarray(sct.grab(area))[:, :, :3]
                codes = read_menu(region, monitor["height"]).codes
                if not self.router.is_current(window):
                    return
                outcome = self.router.offer(window, codes)
                if outcome is None:
                    time.sleep(READING_INTERVAL)
        trigger = self.router.finish(window, outcome)
        if outcome.kind == "call":
            self._type(outcome.code)
        elif outcome.kind == "beep":
            winsound.Beep(330, 150)
        elif outcome.kind == "pass" and trigger is not None:
            with self._send_lock:
                self._sending.set()
                try:
                    self._tap(trigger)
                finally:
                    self._sending.clear()

    def _direct_call(self, code: str) -> None:
        with self._send_lock:
            self._sending.set()
            try:
                self._tap(self.call_key, gap=self.settings.direct_key_pause_ms)
                self._tap_code(code)
            finally:
                self._sending.clear()
        self.router.close_window()

    def _type(self, code: str) -> None:
        with self._send_lock:
            self._sending.set()
            try:
                self._tap_code(code)
            finally:
                self._sending.clear()

    def _tap_code(self, code: str) -> None:
        for direction in code:
            self._tap(self.direction_keys[direction])

    def _tap(self, key: Key, gap: tuple[int, int] | None = None) -> None:
        winkeys.send(key, down=True)
        time.sleep(random.uniform(*self.settings.keystroke_ms) / 1000)
        winkeys.send(key, down=False)
        time.sleep(random.uniform(*(gap or self.settings.keystroke_ms)) / 1000)

    # --- pause ---

    def toggle_pause(self) -> None:
        self.router.paused = not self.router.paused
        self.router.close_window()
        winsound.Beep(440 if self.router.paused else 880, 120)
        print("paused" if self.router.paused else "resumed")


def main() -> None:
    settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
    log = EventLog(LOG_PATH)
    app = App(settings, log.write)
    with mss.MSS() as sct:
        height = sct.monitors[1]["height"]
    print(f"Stratagem Caller running. Screen height {height}.")
    if height != REFERENCE_HEIGHT:
        print(f"  Warning: only tested at {REFERENCE_HEIGHT}; Trigger Keys may not read the menu.")
    print(f"  Call Key [{settings.call_key}] then {', '.join(settings.trigger_keys)} for Slots")
    for key, code in settings.direct_keys.items():
        print(f"  Direct Key [{key}] -> {code}")
    print(f"  [{settings.pause_key}] pause/resume, Ctrl+C here to quit")
    print(f"  Logging Trigger Keys and Calls to {LOG_PATH}")
    keyboard.hook(app.on_event, suppress=True)
    keyboard.add_hotkey(settings.pause_key, app.toggle_pause)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
