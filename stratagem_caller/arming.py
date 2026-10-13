"""The Arming Window: what to do with a Trigger Key given the Readings so far.

The window is open from a Call Key press until the Stratagem Menu is seen to
close. It holds no keyboard, screen or clock: it is driven by Readings, key
presses and the times they happened.
"""

from dataclasses import dataclass
from enum import Enum

from .reader import Reading

# After a Call Key press the menu may take this long to slide in and become
# readable (the captures show 250 ms to 500 ms); not seeing it is not "closed" yet.
OPENING_GRACE = 0.75
# When the menu was already open the Call Key press is closing it, so there is
# nothing to wait for beyond the closing animation's first frames.
CLOSING_GRACE = 0.05
# A menu still read open this long after the Call Key press cannot be the closing
# animation: the press did not close it, so it is open.
CLOSING_PERIOD = 0.5
# Once the menu has been seen open, fire can hide it. A not-open Reading puts the
# watch in doubt; only this many Readings, spread over this long, all not open,
# make it closed.
DOUBT_PERIOD = 0.6
DOUBT_READINGS = 3
# The menu reports open as soon as four Icons are in place, before the lower rows
# have slid in: a Slot is not "not callable" until the menu has been open this long.
SETTLE_PERIOD = 0.3
# A Slot that stays unreadable this long after the menu opened (or the key was
# pressed, whichever is later) earns a beep.
UNREADABLE_LIMIT = 0.75
# A watch that has run this long since the last Call Key press is given up, so a
# misdetected menu cannot keep the tool reading the screen for a whole session.
SAFETY_LIMIT = 60.0
# Seconds between Readings. Fast while the menu is opening, closing or in doubt, or
# a Trigger Key is waiting to be resolved; modest once the menu is confirmed and
# nothing waits.
FAST_READING_INTERVAL = 0.05
MODEST_READING_INTERVAL = 0.2


class Kind(str, Enum):
    """What an Outcome asks for. The log's wording for each is in `Outcome.description`."""

    CALL = "call"  # enter the Code
    BEEP = "beep"  # the Slot can't be called; the watch goes on
    PASS = "pass"  # the menu is not open: hand the held Trigger Key back; watch over
    CLOSED = "closed"  # the menu closed; watch over
    LIMIT = "limit"  # the safety limit ended the watch (a held key is handed back)
    FOCUS = "focus"  # the game lost focus; watch over (the router decides this)


_DESCRIPTIONS = {
    Kind.BEEP: "beep, Slot cannot be called",
    Kind.PASS: "handed back to the game, menu not open",
    Kind.CLOSED: "menu closed, watch ended",
    Kind.LIMIT: "watch ended, safety limit reached",
    Kind.FOCUS: "watch ended, game window lost focus",
}


@dataclass(frozen=True)
class Outcome:
    kind: Kind
    code: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "kind", Kind(self.kind))

    @property
    def description(self) -> str:
        if self.kind is Kind.CALL:
            return f"Call {self.code}"
        return _DESCRIPTIONS[self.kind]

    @property
    def ends_watch(self) -> bool:
        return self.kind is not Kind.BEEP

    @property
    def sends_keys(self) -> bool:
        """Whether acting on this may type or tap keys."""
        return self.kind is Kind.CALL or self.hands_back

    @property
    def hands_back(self) -> bool:
        """Whether a Trigger Key held by the watch goes back to the game."""
        return self.kind in (Kind.PASS, Kind.LIMIT)


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
        nothing seen so far is trusted. A held Trigger Key stays held."""
        if menu_was_open is None:
            menu_was_open = self._confirmed_open()
        self._started = now
        self._grace_end = now + (CLOSING_GRACE if menu_was_open else OPENING_GRACE)
        # Set while the press is taken to be closing an open menu.
        self._closing_since: float | None = now if menu_was_open else None
        self._previous: Reading | None = None
        self._latest: Reading | None = None
        self._seen_open = False  # confirmed open since the press (and not closing)
        self._open_since: float | None = None  # start of the current confirmed stretch
        self._not_open_readings = 0
        self._doubt_since: float | None = None  # first of a run of not-open Readings
        self._doubt_readings = 0
        if self.slot is not None:
            self._pending_since = now

    def press(self, slot: int, now: float) -> Press:
        """A Trigger Key went down."""
        if self.done:
            return Press(False)
        outcome = self._resolve(slot, now)
        if outcome is not None and outcome.kind is Kind.CALL:
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
            return Outcome(Kind.LIMIT)
        self._previous, self._latest = self._latest, reading
        self._note(reading, now)

        if self._closed_for_good(now):
            self.done = True
            held, self.slot = self.slot, None
            return Outcome(Kind.PASS if held is not None else Kind.CLOSED)
        if self.slot is None:
            return None
        outcome = self._resolve(self.slot, now)
        if outcome is None and self._open_since is not None and not self._in_doubt_or_closing():
            waited_from = max(self._pending_since, self._open_since)
            if now - waited_from >= UNREADABLE_LIMIT:
                outcome = Outcome(Kind.BEEP)
        if outcome is not None:
            self.slot = None
            if outcome.kind is Kind.CALL:
                self.done = True
        return outcome

    def reading_delay(self) -> float:
        """Seconds to wait before the next Reading."""
        if self.slot is not None or self._in_doubt_or_closing() or not self._confirmed_open():
            return FAST_READING_INTERVAL
        return MODEST_READING_INTERVAL

    def _note(self, reading: Reading, now: float) -> None:
        if reading.menu_open:
            self._not_open_readings = 0
            self._doubt_since = None
            self._doubt_readings = 0
        elif self._seen_open:
            if self._doubt_since is None:
                self._doubt_since = now
                self._open_since = None
            self._doubt_readings += 1
        elif now >= self._grace_end:
            self._not_open_readings += 1
        else:
            self._not_open_readings = 0
        if not self._confirmed_open():
            return
        if self._closing_since is not None and now - self._closing_since >= CLOSING_PERIOD:
            self._closing_since = None  # still open: the press did not close it
        if self._closing_since is None:
            self._seen_open = True
            if self._open_since is None:
                self._open_since = now

    def _closed_for_good(self, now: float) -> bool:
        if self._not_open_readings >= 2:
            return True
        return (
            self._doubt_since is not None
            and self._doubt_readings >= DOUBT_READINGS
            and now - self._doubt_since >= DOUBT_PERIOD
        )

    def _in_doubt_or_closing(self) -> bool:
        return self._doubt_since is not None or self._closing_since is not None

    def _confirmed_open(self) -> bool:
        # One Reading can catch the menu mid-animation; two in a row can't.
        return (
            self._previous is not None
            and self._latest is not None
            and self._previous.menu_open
            and self._latest.menu_open
        )

    def _resolve(self, slot: int, now: float) -> Outcome | None:
        """What the last two Readings settle for `slot`, if anything."""
        if self._previous is None or self._latest is None or self._in_doubt_or_closing():
            return None
        code = self._latest.codes.get(slot)
        if code is not None and code == self._previous.codes.get(slot):
            return Outcome(Kind.CALL, code)
        settled = self._open_since is not None and now - self._open_since >= SETTLE_PERIOD
        if (
            settled
            and self._confirmed_open()
            and not any(slot in r.codes or slot in r.unreadable for r in (self._previous, self._latest))
        ):
            return Outcome(Kind.BEEP)
        return None
