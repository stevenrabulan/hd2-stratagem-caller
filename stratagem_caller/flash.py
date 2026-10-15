"""The red flash of a Key Cap whose Trigger Key beeped: when it is red, as a pure function of time.

No clock and no drawing: callers pass the time, so tests never sleep.
"""

# Red for this long, then normal for this long, this many times.
FLASH_STEP = 0.1
FLASH_COUNT = 3


def _step(started: float, now: float) -> int | None:
    """Which step of the flash (0 red, 1 normal, 2 red, ...) `now` falls in; None outside it."""
    elapsed = now - started
    if elapsed < 0:
        return None
    # The small allowance keeps a step boundary from landing a step early on float error
    # (1.3 - 1.0 is 0.30000000000000004, and 0.3 / 0.1 is 2.9999999999999996).
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
