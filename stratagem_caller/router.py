"""Decide what happens to each key event, apart from the keyboard hook itself."""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .arming import ArmingWindow, Outcome
from .reader import Reading

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
    # Set when a Trigger Key was decided at once: the Call or beep to make now.
    outcome: Outcome | None = None


class KeyRouter:
    def __init__(
        self,
        *,
        call_key: "Key",
        direct_keys: "dict[Key, str]",
        trigger_keys: "dict[Key, int]",
        window_title: str,
        clock: Callable[[], float],
        foreground_title: Callable[[], str],
        is_sending: Callable[[], bool],
        log: Callable[[str], None],
    ):
        self.call_key = call_key
        self.direct_keys = direct_keys
        self.trigger_keys = trigger_keys
        self.window_title = window_title
        self.paused = False
        self._clock = clock
        self._foreground_title = foreground_title
        self._is_sending = is_sending
        self._log = log

        self._lock = threading.Lock()
        self._window: ArmingWindow | None = None
        self._window_trigger: "Key | None" = None  # the Trigger Key it holds (its Slot is the window's)
        self._reading: Reading | None = None
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
            trigger = self._trigger_for(event)
            if trigger is not None:
                self._log_trigger(trigger[1], "ignored as repeat")
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
        trigger = self._trigger_for(event)
        if trigger is not None:
            return self._on_trigger_key(ident, *trigger)
        return Decision(True)

    def _is_repeat(self, ident: Ident, now: float) -> bool:
        # Windows waits at most a second before the first repeat, then repeats many
        # times a second. A key-down later than that after the last one is a new press
        # whose key-up was never seen.
        last = self._held.get(ident)
        return last is not None and now - last <= REPEAT_GAP

    def _trigger_for(self, event: KeyEvent) -> "tuple[Key, int] | None":
        for key, slot in self.trigger_keys.items():
            if key.matches(event):
                return key, slot
        return None

    def _on_call_key(self) -> ArmingWindow | None:
        with self._lock:
            if self._window is not None and not self._window.done:
                # Already watching: the Call Key opens or closes the menu, and what is
                # on screen decides which. The worker thread carries on, and a held
                # Trigger Key stays held until the menu settles.
                self._window.restart(self._clock())
                self._reading = None
                return None
            window = ArmingWindow(self._clock())
            self._window = window
            self._window_trigger = None
            self._reading = None
        return window

    def _on_trigger_key(self, ident: Ident, key: "Key", slot: int) -> Decision:
        outcome = None
        with self._lock:
            window = self._window
            press = window.press(slot, self._clock()) if window is not None else None
            if press is None:
                taken, why = False, "not in the Arming Window"
            elif not press.taken:
                taken, why = False, "not taken, the Arming Window has made its Call"
            else:
                taken = True
                outcome = press.outcome
                why = "taken, waiting for Reading" if outcome is None else "taken"
                self._window_trigger = key
            reading = self._describe_reading()
        self._log(f"trigger key {key.name} Slot {slot}: {why}; latest Reading: {reading}")
        if not taken:
            return Decision(True)
        self._swallowed.add(ident)
        if outcome is not None:
            self.finish(window, outcome)
        return Decision(False, outcome=outcome)

    def _log_trigger(self, slot: int, decision: str) -> None:
        with self._lock:
            reading = self._describe_reading()
        self._log(f"trigger key Slot {slot}: {decision}; latest Reading: {reading}")

    def describe(self) -> str:
        """The watch and the latest Reading in words, for a mark in the log."""
        with self._lock:
            window = self._window
            if self.paused:
                state = "paused"
            elif window is None:
                state = "not watching"
            elif window.slot is not None:
                state = f"watching, Trigger Key held for Slot {window.slot}"
            else:
                state = "watching"
            reading = self._describe_reading()
        return f"{state}; latest Reading: {reading}"

    def _describe_reading(self) -> str:
        reading = self._reading
        if reading is None:
            return "none yet"
        if not reading.menu_open:
            return "menu not open"
        text = "menu open, Slots " + (",".join(str(n) for n in sorted(reading.codes)) or "none")
        if reading.unreadable:
            text += "; unreadable " + ",".join(str(n) for n in sorted(reading.unreadable))
        return text

    # --- the worker thread's view of the Arming Window ---

    def offer(self, window: ArmingWindow, reading: Reading) -> Outcome | None:
        """Feed a Reading to `window`. None while undecided, or if `window` was replaced."""
        with self._lock:
            if self._window is not window:
                return None
            if self._foreground_title() != self.window_title:
                return Outcome("focus")
            self._reading = reading
            return window.offer(reading, self._clock())

    def reading_delay(self, window: ArmingWindow) -> float:
        """Seconds the worker should wait before its next Reading."""
        with self._lock:
            return window.reading_delay()

    def end_watch(self, reason: str, only: ArmingWindow | None = None) -> "Key | None":
        """End the watch from outside its normal course (pause, a failed Reading). With `only`,
        end it just if that is still the current one. Returns the Trigger Key that was held,
        if any, for the caller to hand back to the game."""
        with self._lock:
            window = self._window
            if window is None or (only is not None and window is not only):
                return None
            held = self._window_trigger if window.slot is not None else None
            self._window = None
            self._window_trigger = None
            reading = self._describe_reading()
        suffix = ", held Trigger Key handed back" if held is not None else ""
        self._log(f"watch ended: {reason}{suffix}; latest Reading: {reading}")
        return held

    def is_current(self, window: ArmingWindow) -> bool:
        with self._lock:
            return self._window is window

    def finish(self, window: ArmingWindow, outcome: Outcome) -> "Key | None":
        """Log `outcome`, and end the watch unless it is a beep. Returns the Trigger Key it
        took. A window that is no longer the current one takes nothing: the Trigger Key
        now held belongs to the new watch."""
        with self._lock:
            current = self._window is window
            trigger = self._window_trigger if current else None
            reading = self._describe_reading()
            if current:
                self._window_trigger = None
                if outcome.ends_watch:
                    self._window = None
        slot = self.trigger_keys.get(trigger) if trigger is not None else None
        prefix = f"Slot {slot}: " if slot else ""
        self._log(f"{prefix}{outcome.description}; latest Reading: {reading}")
        return trigger

    def close_window(self) -> None:
        with self._lock:
            self._window = None

