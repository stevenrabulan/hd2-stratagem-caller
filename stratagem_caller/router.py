"""Decide what happens to each key event, apart from the keyboard hook itself."""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .arming import ArmingWindow, Kind, Outcome
from .flash import is_red, red_slots, start_flash
from .keycaps import TerminalKeyCap
from .reader import Reading
from .terminal_code import CodeReading, CodeStatus
from .terminal_prompt import TerminalPrompt
from .terminal_watch import TerminalWatch, code_waits

if TYPE_CHECKING:
    from .winkeys import Key

Ident = tuple[int, bool]  # scan code, is keypad

# Longest gap between key-downs that can still be one held key auto-repeating.
REPEAT_GAP = 1.0
# While a Code waits, the Terminal Key's Key Cap blinks: on this long, then off a quarter as long.
TERMINAL_CAP_ON = 0.96
TERMINAL_CAP_OFF = TERMINAL_CAP_ON / 4


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
    # False when the tool is watching a menu the player has just opened: pressing the
    # Call Key for the Direct Key would close it.
    direct_presses_call_key: bool = True
    # Set when a Trigger Key was decided at once: the Call or beep to make now.
    outcome: Outcome | None = None
    # Set when a Use Key press started a Terminal watch that needs reading.
    start_terminal_watch: TerminalWatch | None = None
    # Set when the Terminal Key was pressed while a Terminal waits for a Code: the key is
    # swallowed and the tool is to enter the Code (or say it cannot).
    enter_code: bool = False


class KeyRouter:
    def __init__(
        self,
        *,
        call_key: "Key",
        use_key: "Key",
        terminal_key: "Key",
        direct_keys: "dict[Key, str]",
        trigger_keys: "dict[Key, int]",
        window_title: str,
        clock: Callable[[], float],
        foreground_title: Callable[[], str],
        is_sending: Callable[[], bool],
        is_entering_code: Callable[[], bool] = lambda: False,
        log: Callable[[str], None],
    ):
        self.call_key = call_key
        self.use_key = use_key
        self.terminal_key = terminal_key
        self.direct_keys = direct_keys
        self.trigger_keys = trigger_keys
        self.window_title = window_title
        self.paused = False
        self._clock = clock
        self._foreground_title = foreground_title
        self._is_sending = is_sending
        self._is_entering_code = is_entering_code
        self._log = log

        self._lock = threading.Lock()
        self._window: ArmingWindow | None = None
        self._window_trigger: "Key | None" = None  # the Trigger Key it holds (its Slot is the window's)
        self._reading: Reading | None = None
        self._terminal: TerminalWatch | None = None  # the watch for a Terminal's prompt
        self._flashes: dict[int, float] = {}  # Slot -> when its Trigger Key last beeped
        self._terminal_flash: float | None = None  # when the Terminal Key last beeped
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
        if self.terminal_key.matches(event) and self._is_entering_code() and self._foreground_title() == self.window_title:
            # The Code is being read and typed (the tool ignores its own keys meanwhile): the Terminal
            # Key stays held back, so a second press is no weapon switch and starts no second Code.
            self._swallowed.add(ident)
            self._log(f"terminal key {self.terminal_key.name}: swallowed, a Code is being entered")
            return Decision(False)
        if self._is_sending() or self.paused:
            return Decision(True)
        if self._foreground_title() != self.window_title:
            return Decision(True)

        if self.call_key.matches(event):
            return Decision(True, start_watching=self._on_call_key())
        for key, code in self.direct_keys.items():
            if key.matches(event):
                self._swallowed.add(ident)
                with self._lock:
                    # A held Trigger Key is dropped with the watch.
                    menu_shown = self._window is not None and self._window.menu_shown()
                    self._window = None
                    self._window_trigger = None
                skipped = "; menu open, Call Key skipped" if menu_shown else ""
                self._log(f"direct key {key.name}: Call {code}{skipped}")
                return Decision(False, direct_code=code, direct_presses_call_key=not menu_shown)
        if self.use_key.matches(event):
            return Decision(True, start_terminal_watch=self._on_use_key())
        if self.terminal_key.matches(event):
            decision = self._on_terminal_key(ident)
            if decision is not None:
                return decision
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

    def _on_use_key(self) -> TerminalWatch | None:
        with self._lock:
            watch = self._terminal
            if watch is None:
                watch = self._terminal = TerminalWatch(self._clock())
                started = True
            else:
                # Already watching: the 5 s and the safety limit count from this press. The
                # worker thread carries on.
                watch.restart(self._clock())
                started = False
        self._log(f"use key {self.use_key.name}: Terminal watch {'started' if started else 'restarted'}")
        return watch if started else None

    def _on_terminal_key(self, ident: Ident) -> Decision | None:
        """The Decision when the Terminal Key is held back for a Terminal; None when it is not,
        and the key goes on as an ordinary key or a Trigger Key."""
        with self._lock:
            watch = self._terminal
            prompt = watch.prompt if watch is not None else None
            menu_watched = self._window is not None and not self._window.done
        if watch is None:
            return None  # no Terminal to decide about: the key is not this tool's business
        if prompt is not TerminalPrompt.INTERACT:
            why = _describe_prompt(prompt)
        elif menu_watched:
            # The player opened the Stratagem Menu with the Call Key: this is a Slot, not a Code.
            why = "Stratagem Menu watched, Trigger Key rules apply"
        else:
            self._swallowed.add(ident)
            with self._lock:
                watch.drop_code()  # the Code is about to change under the tool's own typing
            self._log(f"terminal key {self.terminal_key.name}: swallowed, {_describe_prompt(prompt)}")
            return Decision(False, enter_code=True)
        self._log(f"terminal key {self.terminal_key.name}: not swallowed, {why}")
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
            self._flashes = {}
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
            terminal = self._terminal
        text = f"{state}; latest Reading: {reading}"
        if terminal is not None:
            text += f"; Terminal watch running, {_describe_prompt(terminal.prompt)}"
        return text

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

    # --- what the Overlay shows ---

    def key_caps(self) -> dict[int, str]:
        """The Key Caps to show now: Slot -> name of its Trigger Key. A Slot without a
        Trigger Key gets none. Empty when no watch is running, and at once, without
        waiting for the watch to notice, when the tool is paused or the game is not
        focused."""
        # Asked of Windows outside the lock: this runs many times a second on the
        # Overlay's thread and the keyboard hook must never wait behind it.
        if self.paused or self._foreground_title() != self.window_title:
            return {}
        with self._lock:
            window = self._window
            listed = window.key_cap_slots() if window is not None else frozenset()
        names: dict[int, str] = {}
        for key, slot in self.trigger_keys.items():
            if slot in listed:
                names.setdefault(slot, key.name)  # two keys for one Slot: the first shown
        return names

    def red_key_caps(self) -> frozenset[int]:
        """The Slots whose Key Cap is in a red step of a flash now: their Trigger Key just
        beeped. Only Key Caps that are showing can be red."""
        shown = self.key_caps()
        with self._lock:
            return red_slots(self._flashes, self._clock()) & shown.keys()

    def terminal_key_cap(self) -> TerminalKeyCap | None:
        """The Key Cap for the Terminal Key to show now, None for none. It shows while a Terminal's
        Code is read with directions left to enter and the Terminal Key would enter it: the prompt
        reads INTERACT, the Stratagem Menu is not being watched (there the key is a Trigger Key),
        the tool is not typing, the game is focused and the tool is not paused. During a flash it
        shows red in each red step, whether or not a Code is read: that is how the player is told
        the Terminal Key beeped for want of a Code. Otherwise it blinks, on for TERMINAL_CAP_ON and off
        for TERMINAL_CAP_OFF, from the moment the Code is first read."""
        # Asked of Windows outside the lock, as key_caps does.
        if self.paused or self._foreground_title() != self.window_title:
            return None
        with self._lock:
            watch, window = self._terminal, self._window
            if watch is None or watch.prompt is not TerminalPrompt.INTERACT:
                return None
            if window is not None and not window.done:
                return None
            now = self._clock()
            red = self._terminal_flash is not None and is_red(self._terminal_flash, now)
            waiting = code_waits(watch.code) and _blink_on(now - watch.code_waits_since)
        if red or (waiting and not self._is_entering_code()):
            return TerminalKeyCap(self.terminal_key.name, red)
        return None

    def flash_terminal_key(self) -> None:
        """The Terminal Key just beeped: its Key Cap flashes red, in step with the Beep's tones."""
        with self._lock:
            self._terminal_flash = self._clock()

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
            slot = self.trigger_keys.get(trigger) if trigger is not None else None
            if current:
                self._window_trigger = None
                if outcome.ends_watch:
                    self._window = None
                elif outcome.kind is Kind.BEEP and slot in window.key_cap_slots():
                    # Only a Slot with a Key Cap flashes; one beyond the menu's end just beeps.
                    self._flashes = start_flash(self._flashes, slot, self._clock())
        prefix = f"Slot {slot}: " if slot else ""
        self._log(f"{prefix}{outcome.description}; latest Reading: {reading}")
        return trigger

    # --- the worker thread's view of the Terminal watch ---

    def offer_terminal(self, watch: TerminalWatch, prompt: TerminalPrompt) -> None:
        """Feed a reading of the Terminal Prompt to `watch`, which ends it when it is over.
        Ignored if `watch` was replaced."""
        with self._lock:
            if self._terminal is not watch:
                return
            had_cap = code_waits(watch.code)
            if self._foreground_title() != self.window_title:
                reason = "game window lost focus"
            else:
                reason = watch.offer(prompt, self._clock())
            if reason is not None:
                self._terminal = None
            lost_cap = had_cap and not code_waits(watch.code)
        if lost_cap:
            self._log(f"Terminal Key Cap hidden: {_describe_prompt(prompt)}")
        if reason is not None:
            self._log(f"Terminal watch ended: {reason}")

    def offer_terminal_code(self, watch: TerminalWatch, reading: CodeReading) -> None:
        """Feed a reading of the Code to `watch`. Ignored if `watch` was replaced, or while the tool
        is typing a Code (a reading taken just before the press, or amid the typing, is out of date)."""
        with self._lock:
            if self._terminal is not watch or self._is_entering_code():
                return
            before = code_waits(watch.code)
            watch.offer_code(reading, self._clock())
            after = code_waits(watch.code)
        if after and not before:
            self._log(f"Terminal Key Cap shown: Code {reading.code}, {reading.entered} entered")
        elif before and not after:
            self._log(f"Terminal Key Cap hidden: {_describe_code(reading)}")

    def terminal_is_current(self, watch: TerminalWatch) -> bool:
        with self._lock:
            return self._terminal is watch

    def end_terminal_watch(self, reason: str, only: TerminalWatch | None = None) -> None:
        """End the Terminal watch from outside its normal course (pause, a failed reading). With
        `only`, end it just if that is still the current one."""
        with self._lock:
            watch = self._terminal
            if watch is None or (only is not None and watch is not only):
                return
            self._terminal = None
        self._log(f"Terminal watch ended: {reason}")

    def close_window(self) -> None:
        with self._lock:
            self._window = None



def _blink_on(elapsed: float) -> bool:
    """Whether the blinking Terminal Key Cap is in its on part, `elapsed` seconds after it began."""
    return elapsed % (TERMINAL_CAP_ON + TERMINAL_CAP_OFF) < TERMINAL_CAP_ON


def _describe_code(reading: CodeReading) -> str:
    if reading.status is CodeStatus.READ:
        return f"Code {reading.code}, all entered"
    return f"{reading.status.value}, {reading.why}"


def _describe_prompt(prompt: TerminalPrompt) -> str:
    return "no Terminal Prompt" if prompt is TerminalPrompt.NONE else f"Terminal Prompt reads {prompt.value}"
