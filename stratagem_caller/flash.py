"""The double pulse of a Beep: when a Key Cap is red and when each tone starts, as pure
functions of time. This module owns the one schedule, so the reds and the tones can't drift apart.

No clock and no drawing: callers pass the time, so tests never sleep.
"""

# Red for this long, then normal for this long, this many times.
FLASH_STEP = 0.15
FLASH_COUNT = 2


def _step(started: float, now: float) -> int | None:
    """Which step of the flash (0 red, 1 normal, 2 red, 3 normal) `now` falls in; None outside it."""
    elapsed = now - started
    if elapsed < 0:
        return None
    # The small allowance keeps a step boundary from landing a step early on float error
    # (1.3 - 1.0 is 0.30000000000000004, and 0.45 / 0.15 is 2.9999999999999996).
    step = int(elapsed / FLASH_STEP + 1e-6)
    return step if step < 2 * FLASH_COUNT else None


def start_flash(flashes: dict[int, float], slot: int, now: float) -> dict[int, float]:
    """`flashes` with a flash begun for `slot` at `now` (restarting any it had), and the
    flashes that are over dropped."""
    live = {s: started for s, started in flashes.items() if _step(started, now) is not None}
    live[slot] = now
    return live


def red_slots(flashes: dict[int, float], now: float) -> frozenset[int]:
    """The Slots whose Key Cap is in a red step at `now`; `flashes` maps Slot -> start time."""
    return frozenset(
        slot for slot, started in flashes.items() if (step := _step(started, now)) is not None and step % 2 == 0
    )


def tone_starts(started: float) -> tuple[float, ...]:
    """When each tone of a Beep that began at `started` starts: as each red step begins."""
    return tuple(started + 2 * n * FLASH_STEP for n in range(FLASH_COUNT))
