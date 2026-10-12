"""The Arming Window: what to do with a Trigger Key given the Readings so far."""

from dataclasses import dataclass

# The menu needs about a quarter second to slide in; a Slot is not written off
# as uncallable before this long after the Call Key, nor this soon after the
# Trigger Key.
MENU_SETTLE = 0.6
TRIGGER_GRACE = 0.35


@dataclass(frozen=True)
class Outcome:
    # "call": enter `code`. "beep": the Slot can't be called. "pass": no menu was
    # seen, so hand the Trigger Key back to the game. "expired": nothing was pressed.
    kind: str
    code: str | None = None


class ArmingWindow:
    def __init__(self, started: float, length: float):
        self.started = started
        self.deadline = started + length
        self.slot: int | None = None
        self._give_up_at = self.deadline
        self._previous: dict[int, str] | None = None
        self._seen_menu = False

    def press(self, slot: int, now: float) -> bool:
        """A Trigger Key went down. True if the window takes it (swallow the key)."""
        if self.slot is not None or now >= self.deadline:
            return False
        self.slot = slot
        self._give_up_at = min(
            self.deadline, max(now + TRIGGER_GRACE, self.started + MENU_SETTLE)
        )
        return True

    def offer(self, codes: dict[int, str], now: float) -> Outcome | None:
        """Feed the Codes of a new Reading. Returns an Outcome once decided."""
        # One Reading can catch the menu mid-animation; two equal ones in a row can't.
        confirmed = bool(codes) and codes == self._previous
        self._previous = codes
        self._seen_menu = self._seen_menu or bool(codes)
        if self.slot is None:
            return Outcome("expired") if now >= self.deadline else None
        if confirmed and self.slot in codes:
            return Outcome("call", codes[self.slot])
        if now >= self._give_up_at:
            return Outcome("beep" if self._seen_menu else "pass")
        return None
