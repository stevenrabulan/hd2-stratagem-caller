"""The rules behind capture_fixtures.py's bursts, kept free of hooks and screen code
so the normal test suite can check them."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BurstKind:
    """What a press of one key captures: when the shots are taken and what they are called."""

    prefix: str  # starts every label, so bursts of different keys can be told apart
    delays_ms: tuple[int, ...]  # time after the press, ascending
    delay_width: int  # zero-pad the delay to this many digits so files sort in shot order

    def filename(self, stamp: str, label: str, delay_ms: int) -> str:
        return f"{stamp}_{label}_{delay_ms:0{self.delay_width}d}ms.png"


# Several shots per Call Key press, so the fixtures show how long the menu takes to open.
CALL_KEY_BURST = BurstKind("press", (100, 250, 500), 3)

# Use Key presses also pick up samples, ammo and pods, so most bursts will be useless;
# the delays cover the walk-up to a Terminal and the Code appearing.
USE_KEY_BURST = BurstKind("use", (500, 1000, 1500, 2000, 3000, 4000), 4)


class BurstTrigger:
    """Turns one key's down and up events into burst labels. A held key auto-repeats
    key-down, and only the first of those starts a burst."""

    def __init__(self, kind: BurstKind):
        self.kind = kind
        self._held = False
        self._count = 0

    def key_down(self) -> str | None:
        """The label for a new burst, or None when this is a repeat of a held key."""
        if self._held:
            return None
        self._held = True
        self._count += 1
        return f"{self.kind.prefix}{self._count:03d}"

    def key_up(self) -> None:
        self._held = False
