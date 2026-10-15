"""The fixture capture tool's burst rules: which presses start a burst, when its shots
are taken, and what they are called. The hook and screen code is not tested here."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from burst_plan import CALL_KEY_BURST, USE_KEY_BURST, BurstTrigger  # noqa: E402


def test_a_use_key_burst_covers_the_walk_up_and_the_code_appearing():
    delays = USE_KEY_BURST.delays_ms
    assert delays == tuple(sorted(delays))
    assert delays[0] <= 500
    assert delays[-1] >= 4000
    assert 1000 in delays and 2000 in delays and 3000 in delays


def test_a_call_key_burst_keeps_its_original_timings():
    assert CALL_KEY_BURST.delays_ms == (100, 250, 500)


def test_a_press_starts_a_labelled_burst_and_a_held_key_starts_only_one():
    use_key = BurstTrigger(USE_KEY_BURST)
    first = use_key.key_down()
    assert first is not None
    assert [use_key.key_down() for _ in range(5)] == [None] * 5


def test_releasing_the_key_lets_the_next_press_start_another_burst_with_the_next_number():
    use_key = BurstTrigger(USE_KEY_BURST)
    first = use_key.key_down()
    use_key.key_down()
    use_key.key_up()
    second = use_key.key_down()
    assert second is not None and second != first
    assert (first, second) == ("use001", "use002")


def test_a_release_with_no_press_does_not_use_up_a_number():
    use_key = BurstTrigger(USE_KEY_BURST)
    use_key.key_up()
    assert use_key.key_down() == "use001"


def test_use_key_and_call_key_bursts_are_told_apart_and_numbered_separately():
    use_key, call_key = BurstTrigger(USE_KEY_BURST), BurstTrigger(CALL_KEY_BURST)
    assert call_key.key_down() == "press001"
    assert use_key.key_down() == "use001"
    call_key.key_up()
    assert call_key.key_down() == "press002"
    assert use_key.key_down() is None  # still held, however many Call Key presses happen


def test_call_key_shots_are_named_as_they_were_before():
    name = CALL_KEY_BURST.filename("20261015-120000", "press007", 100)
    assert name == "20261015-120000_press007_100ms.png"


def test_use_key_shots_sort_in_the_order_they_were_taken():
    names = [USE_KEY_BURST.filename("20261015-120000", "use001", d) for d in USE_KEY_BURST.delays_ms]
    assert names == sorted(names)
    assert names[0] == "20261015-120000_use001_0500ms.png"
