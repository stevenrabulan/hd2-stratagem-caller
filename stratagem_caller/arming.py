"""The Arming Window: what to do with a Trigger Key given the Readings so far.

The window is open from a Call Key press until the Stratagem Menu is seen to
close. It holds no keyboard, screen or clock: it is driven by Readings, key
presses and the times they happened.
"""

from dataclasses import dataclass

from .reader import Reading

# After a Call Key press the menu may take this long to slide in and become
# readable (the captures show 250 ms to 500 ms); not seeing it is not "closed" yet.
OPENING_GRACE = 0.75
# When the menu was already open the Call Key press is closing it, so there is
# nothing to wait for beyond the closing animation's first frames.
CLOSING_GRACE = 0.05
# A Slot that stays unreadable this long after the menu opened (or the key was
# pressed, whichever is later) earns a beep.
UNREADABLE_LIMIT = 0.75
# A watch that has run this long since the last Call Key press is given up, so a
# misdetected menu cannot keep the tool reading the screen for a whole session.
SAFETY_LIMIT = 60.0
# Seconds between Readings. Fast while the menu is opening or a Trigger Key is
# waiting to be resolved; modest once the menu is confirmed and nothing waits.
FAST_READING_INTERVAL = 0.05
MODEST_READING_INTERVAL = 0.2


@dataclass(frozen=True)
class Outcome:
    # "call": enter `code`. "beep": the Slot can't be called, the watch goes on.
    # "pass": no menu appeared, hand the held Trigger Key back to the game; the
    # watch is over. "closed": the menu closed, the watch is over. "limit": the
    # safety limit ended the watch (a held Trigger Key is handed back). "focus":
    # the game lost focus, the watch is over (the router decides this, not the window).
    kind: str
    code: str | None = None


@dataclass(frozen=True)
class Press:
    # taken: the window has the Trigger Key (swallow it). outcome: decided at once.
    taken: bool
    outcome: Outcome | None = None


class ArmingWindow:
    def __init__(self, started: float):
        self.done = False
        self.slot: int | None = None  # the Trigger Key's Slot, while one is held
        self._pending_since = 0.0
        self.restart(started, menu_was_open=False)

    def restart(self, now: float, menu_was_open: bool | None = None) -> None:
        """The Call Key was pressed again: the menu is opening or closing, so
        nothing seen so far is trusted and any held Trigger Key is dropped."""
        if menu_was_open is None:
            menu_was_open = self._confirmed_open()
        self._started = now
        self._grace_end = now + (CLOSING_GRACE if menu_was_open else OPENING_GRACE)
        self._previous: Reading | None = None
        self._latest: Reading | None = None
        self._open_since: float | None = None
        self._not_open_readings = 0
        self.slot = None

    def press(self, slot: int, now: float) -> Press:
        """A Trigger Key went down."""
        if self.done:
            return Press(False)
        outcome = self._resolve(slot)
        if outcome is not None and outcome.kind == "call":
            self.done = True
        if outcome is None:
            self.slot = slot
            self._pending_since = now
        else:
            self.slot = None
        return Press(True, outcome)

    def offer(self, reading: Reading, now: float) -> Outcome | None:
        """Feed a new Reading. Returns an Outcome once something is decided."""
        if self.done:
            return None
        if now - self._started >= SAFETY_LIMIT:
            self.done = True
            self.slot = None
            return Outcome("limit")
        self._previous, self._latest = self._latest, reading
        if reading.menu_open:
            self._not_open_readings = 0
        elif now >= self._grace_end:
            self._not_open_readings += 1
        else:
            self._not_open_readings = 0
        if self._open_since is None and self._confirmed_open():
            self._open_since = now

        if self._not_open_readings >= 2:
            self.done = True
            held, self.slot = self.slot, None
            return Outcome("pass" if held is not None else "closed")
        if self.slot is None:
            return None
        outcome = self._resolve(self.slot)
        if outcome is None and self._open_since is not None:
            waited_from = max(self._pending_since, self._open_since)
            if now - waited_from >= UNREADABLE_LIMIT:
                outcome = Outcome("beep")
        if outcome is not None:
            self.slot = None
            if outcome.kind == "call":
                self.done = True
        return outcome

    def reading_delay(self) -> float:
        """Seconds to wait before the next Reading."""
        if self.slot is not None or not self._confirmed_open():
            return FAST_READING_INTERVAL
        return MODEST_READING_INTERVAL

    def _confirmed_open(self) -> bool:
        # One Reading can catch the menu mid-animation; two in a row can't.
        return (
            self._previous is not None
            and self._latest is not None
            and self._previous.menu_open
            and self._latest.menu_open
        )

    def _resolve(self, slot: int) -> Outcome | None:
        """What the last two Readings settle for `slot`, if anything."""
        if self._previous is None or self._latest is None:
            return None
        code = self._latest.codes.get(slot)
        if code is not None and code == self._previous.codes.get(slot):
            return Outcome("call", code)
        if self._confirmed_open() and not any(
            slot in r.codes or slot in r.unreadable for r in (self._previous, self._latest)
        ):
            return Outcome("beep")
        return None
