"""Listen for the Call Key, Trigger Keys and Direct Keys, and make Calls."""

import random
import threading
import time
import winsound
from pathlib import Path

from . import winkeys

winkeys.make_dpi_aware()

import keyboard  # noqa: E402
import mss  # noqa: E402
import numpy as np  # noqa: E402

from .arming import ArmingWindow  # noqa: E402
from .reader import REFERENCE_HEIGHT, read_menu, region_size  # noqa: E402
from .settings import Settings, load  # noqa: E402
from .winkeys import Key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Reading the menu before it has started to slide in is wasted work.
FIRST_READING_DELAY = 0.15
READING_INTERVAL = 0.02


class App:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.call_key = Key.named(settings.call_key)
        self.direction_keys = {d: Key.named(k) for d, k in settings.direction_keys.items()}
        self.trigger_keys = {Key.named(k): slot for k, slot in settings.trigger_keys.items()}
        self.direct_keys = {Key.named(k): code for k, code in settings.direct_keys.items()}

        self._lock = threading.Lock()
        self._window: ArmingWindow | None = None
        self._window_trigger: Key | None = None
        # Set while the tool is typing, so it doesn't react to its own keys.
        self._sending = threading.Event()
        self._send_lock = threading.Lock()
        self._paused = False
        self._held: set[tuple[int, bool]] = set()
        self._swallowed: set[tuple[int, bool]] = set()

    # --- keyboard hook (must return quickly; True lets the key through) ---

    def on_event(self, event: keyboard.KeyboardEvent) -> bool:
        ident = (event.scan_code, event.is_keypad)
        if event.event_type == keyboard.KEY_UP:
            self._held.discard(ident)
            if ident in self._swallowed:
                self._swallowed.discard(ident)
                return False
            return True
        repeat = ident in self._held
        self._held.add(ident)
        if repeat:
            return ident not in self._swallowed
        if self._sending.is_set() or self._paused:
            return True
        if winkeys.foreground_title() != self.settings.window_title:
            return True

        if self.call_key.matches(event):
            self._on_call_key()
            return True
        for key, code in self.direct_keys.items():
            if key.matches(event):
                self._swallowed.add(ident)
                with self._lock:
                    # Inside the Arming Window the player has just opened the
                    # Stratagem Menu, and pressing the Call Key would close it.
                    menu_open = self._window is not None and self._window.is_open(
                        time.monotonic()
                    )
                    self._window = None
                threading.Thread(
                    target=self._direct_call, args=(code, not menu_open), daemon=True
                ).start()
                return False
        for key, slot in self.trigger_keys.items():
            if key.matches(event):
                with self._lock:
                    taken = self._window is not None and self._window.press(
                        slot, time.monotonic()
                    )
                    if taken:
                        self._window_trigger = key
                if taken:
                    self._swallowed.add(ident)
                    return False
        return True

    def _on_call_key(self) -> None:
        with self._lock:
            if self._window is not None:
                # The Call Key toggles: a second press closes the menu.
                self._window = None
                return
            window = ArmingWindow(time.monotonic(), self.settings.arming_window_ms / 1000)
            self._window = window
            self._window_trigger = None
        threading.Thread(target=self._watch_menu, args=(window,), daemon=True).start()

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
                with self._lock:
                    if self._window is not window:
                        return
                    outcome = window.offer(codes, time.monotonic())
                if outcome is None:
                    time.sleep(READING_INTERVAL)
        with self._lock:
            trigger = self._window_trigger
            if self._window is window:
                self._window = None
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

    def _direct_call(self, code: str, press_call_key: bool) -> None:
        with self._send_lock:
            self._sending.set()
            try:
                if press_call_key:
                    self._tap(self.call_key, gap=self.settings.direct_key_pause_ms)
                self._tap_code(code)
            finally:
                self._sending.clear()
        with self._lock:
            self._window = None

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
        self._paused = not self._paused
        with self._lock:
            self._window = None
        winsound.Beep(440 if self._paused else 880, 120)
        print("paused" if self._paused else "resumed")


def main() -> None:
    settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
    app = App(settings)
    with mss.MSS() as sct:
        height = sct.monitors[1]["height"]
    print(f"Stratagem Caller running. Screen height {height}.")
    if height != REFERENCE_HEIGHT:
        print(f"  Warning: only tested at {REFERENCE_HEIGHT}; Trigger Keys may not read the menu.")
    print(f"  Call Key [{settings.call_key}] then {', '.join(settings.trigger_keys)} for Slots")
    for key, code in settings.direct_keys.items():
        print(f"  Direct Key [{key}] -> {code}")
    print(f"  [{settings.pause_key}] pause/resume, Ctrl+C here to quit")
    keyboard.hook(app.on_event, suppress=True)
    keyboard.add_hotkey(settings.pause_key, app.toggle_pause)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
