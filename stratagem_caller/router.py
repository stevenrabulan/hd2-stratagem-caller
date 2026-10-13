"""Decide what happens to each key event, apart from the keyboard hook itself."""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .arming import ArmingWindow, Outcome

if TYPE_CHECKING:
    from .winkeys import Key

Ident = tuple[int, bool]  # scan code, is keypad

# Longest gap between key-downs that can still be one held key auto-repeating.
REPEAT_GAP = 1.0


@dataclass(frozen=True)
class KeyEvent:
    scan_code: int
    is_keypad: bool
    event_type: str  # "down" or "up"
    time: float


@dataclass(frozen=True)
class Decision:
    let_through: bool
    # Set when the Call Key opened an Arming Window that needs watching.
    start_watching: ArmingWindow | None = None
    # Set when a Direct Key was pressed: the Code to Call.
    direct_code: str | None = None


class KeyRouter:
    def __init__(
        self,
        *,
        call_key: "Key",
        direct_keys: "dict[Key, str]",
        trigger_keys: "dict[Key, int]",
        window_title: str,
        arming_length: float,
        clock: Callable[[], float],
        foreground_title: Callable[[], str],
        is_sending: Callable[[], bool],
        log: Callable[[str], None],
    ):
        self.call_key = call_key
        self.direct_keys = direct_keys
        self.trigger_keys = trigger_keys
        self.window_title = window_title
        self.arming_length = arming_length
        self.paused = False
        self._clock = clock
        self._foreground_title = foreground_title
        self._is_sending = is_sending
        self._log = log

        self._lock = threading.Lock()
        self._window: ArmingWindow | None = None
        self._window_trigger: "Key | None" = None
        self._reading: dict[int, str] | None = None
        self._held: dict[Ident, float] = {}  # key -> time of its latest key-down
        self._swallowed: set[Ident] = set()

    # --- the keyboard hook's decision ---

    def handle(self, event: KeyEvent) -> Decision:
        ident = (event.scan_code, event.is_keypad)
        if event.event_type == "up":
            self._held.pop(ident, None)
            if ident in self._swallowed:
                self._swallowed.discard(ident)
                return Decision(False)
            return Decision(True)
        repeat = self._is_repeat(ident, event.time)
        self._held[ident] = event.time
        if repeat:
            slot = self._trigger_slot(event)
            if slot is not None:
                self._log_trigger(slot, "ignored as repeat")
            return Decision(ident not in self._swallowed)
        # A key-down that is not a repeat starts afresh, whatever was recorded before.
        self._swallowed.discard(ident)
        if self._is_sending() or self.paused:
            return Decision(True)
        if self._foreground_title() != self.window_title:
            return Decision(True)

        if self.call_key.matches(event):
            return Decision(True, start_watching=self._on_call_key())
        for key, code in self.direct_keys.items():
            if key.matches(event):
                self._swallowed.add(ident)
                self._log(f"direct key {key.name}: Call {code}")
                return Decision(False, direct_code=code)
        for key, slot in self.trigger_keys.items():
            if key.matches(event):
                return self._on_trigger_key(ident, key, slot)
        return Decision(True)

    def _is_repeat(self, ident: Ident, now: float) -> bool:
        # Windows waits at most a second before the first repeat, then repeats many
        # times a second. A key-down later than that after the last one is a new press
        # whose key-up was never seen.
        last = self._held.get(ident)
        return last is not None and now - last <= REPEAT_GAP

    def _trigger_slot(self, event: KeyEvent) -> int | None:
        for key, slot in self.trigger_keys.items():
            if key.matches(event):
                return slot
        return None

    def _on_call_key(self) -> ArmingWindow | None:
        with self._lock:
            if self._window is not None:
                # The Call Key toggles: a second press closes the menu.
                self._window = None
                return None
            window = ArmingWindow(self._clock(), self.arming_length)
            self._window = window
            self._window_trigger = None
            self._reading = None
        return window

    def _on_trigger_key(self, ident: Ident, key: "Key", slot: int) -> Decision:
        with self._lock:
            if self._window is None:
                taken = False
                why = "not in the Arming Window"
            else:
                taken = self._window.press(slot, self._clock())
                why = "taken, waiting for Reading"
                if not taken:
                    why = "not taken, Arming Window past its end or a Slot already chosen"
            if taken:
                self._window_trigger = key
            reading = self._describe_reading()
        self._log(f"trigger key {key.name} Slot {slot}: {why}; latest Reading: {reading}")
        if taken:
            self._swallowed.add(ident)
            return Decision(False)
        return Decision(True)

    def _log_trigger(self, slot: int, decision: str) -> None:
        with self._lock:
            reading = self._describe_reading()
        self._log(f"trigger key Slot {slot}: {decision}; latest Reading: {reading}")

    def _describe_reading(self) -> str:
        if self._reading is None:
            return "none yet"
        if not self._reading:
            return "no menu"
        return "Slots " + ",".join(str(slot) for slot in sorted(self._reading))

    # --- the worker threads' view of the Arming Window ---

    def offer(self, window: ArmingWindow, codes: dict[int, str]) -> Outcome | None:
        """Feed a Reading to `window`. None while undecided, or if `window` was replaced."""
        with self._lock:
            if self._window is not window:
                return None
            self._reading = codes
            return window.offer(codes, self._clock())

    def is_current(self, window: ArmingWindow) -> bool:
        with self._lock:
            return self._window is window

    def finish(self, window: ArmingWindow, outcome: Outcome) -> "Key | None":
        """Close `window` and log its Outcome. Returns the Trigger Key it took, if any."""
        with self._lock:
            trigger = self._window_trigger
            slot = window.slot
            reading = self._describe_reading()
            if self._window is window:
                self._window = None
        if outcome.kind == "call":
            decision = f"Call {outcome.code}"
        elif outcome.kind == "beep":
            decision = "beep, Slot cannot be called"
        elif outcome.kind == "pass":
            decision = "handed back to the game, no menu seen"
        else:
            return trigger
        self._log(f"Slot {slot}: {decision}; latest Reading: {reading}")
        return trigger

    def close_window(self) -> None:
        with self._lock:
            self._window = None

