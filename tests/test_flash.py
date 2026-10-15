import pytest

from stratagem_caller.flash import red_slots, start_flash, tone_starts


def reds(start, times):
    """Whether Slot 4 is red at each of `times`, for a flash begun at `start`."""
    return [4 in red_slots({4: start}, t) for t in times]


def test_a_flash_is_red_normal_red_normal_then_stays_normal():
    steps = [0.0, 0.07, 0.14, 0.15, 0.22, 0.29, 0.3, 0.37, 0.44, 0.45, 0.52, 0.59, 0.6, 0.65, 5.0]
    assert reds(10.0, [10.0 + t for t in steps]) == [
        True, True, True, False, False, False, True, True, True, False, False, False, False, False, False,
    ]  # fmt: skip


def test_steps_change_at_exact_multiples_of_a_step_despite_float_error():
    # 1.3 - 1.0 is 0.30000000000000004; 0.45 / 0.15 is 2.9999999999999996 and 0.3 / 0.15 is 2.0.
    assert reds(1.0, [1.0 + 0.15, 1.0 + 0.3, 1.0 + 0.45, 1.0 + 0.6]) == [False, True, False, False]
    assert reds(0.0, [0.15, 0.3, 0.45, 0.6]) == [False, True, False, False]


def test_a_beeps_tones_start_at_0_and_0_3_seconds_each_as_a_red_step_begins():
    assert tone_starts(10.0) == pytest.approx((10.0, 10.3))
    assert reds(10.0, tone_starts(10.0)) == [True, True]
    assert reds(10.0, [at - 0.01 for at in tone_starts(10.0)[1:]]) == [False]  # the second follows a normal step


def test_no_tone_is_due_before_the_flash_begins():
    assert min(tone_starts(10.0)) >= 10.0


def test_nothing_is_red_before_the_flash_begins():
    assert reds(10.0, [9.99]) == [False]


def test_each_slot_flashes_on_its_own_clock():
    flashes = {1: 10.0, 2: 10.1}
    assert red_slots(flashes, 10.05) == {1}
    assert red_slots(flashes, 10.15) == {2}
    assert red_slots(flashes, 10.25) == frozenset()
    assert red_slots(flashes, 10.35) == {1}
    assert red_slots({}, 10.0) == frozenset()


def test_starting_a_flash_restarts_that_slots_and_drops_flashes_that_are_over():
    flashes = {1: 10.0, 2: 10.5, 3: 9.0}
    assert start_flash(flashes, 2, 10.55) == {1: 10.0, 2: 10.55}  # Slot 3's flash ended long ago
    assert start_flash({}, 4, 1.0) == {4: 1.0}
