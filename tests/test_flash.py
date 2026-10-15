from stratagem_caller.flash import red_slots, start_flash


def reds(start, times):
    """Whether Slot 4 is red at each of `times`, for a flash begun at `start`."""
    return [4 in red_slots({4: start}, t) for t in times]


def test_a_flash_is_red_normal_red_normal_red_normal_then_stays_normal():
    steps = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 5.0]
    assert reds(10.0, [10.0 + t for t in steps]) == [
        True, True, False, False, True, True, False, False, True, True, False, False, False, False, False,
    ]  # fmt: skip


def test_steps_change_at_exact_hundredths_despite_float_error():
    # 1.3 - 1.0 is 0.30000000000000004 and 0.3 / 0.1 is 2.9999999999999996.
    assert reds(1.0, [1.0 + 0.1, 1.0 + 0.2, 1.0 + 0.3, 1.0 + 0.4]) == [False, True, False, True]
    assert reds(0.0, [0.1, 0.2, 0.3, 0.4, 0.5]) == [False, True, False, True, False]


def test_nothing_is_red_before_the_flash_begins():
    assert reds(10.0, [9.99]) == [False]


def test_each_slot_flashes_on_its_own_clock():
    flashes = {1: 10.0, 2: 10.1}
    assert red_slots(flashes, 10.05) == {1}
    assert red_slots(flashes, 10.15) == {2}
    assert red_slots(flashes, 10.25) == {1}
    assert red_slots({}, 10.0) == frozenset()


def test_starting_a_flash_restarts_that_slots_and_drops_flashes_that_are_over():
    flashes = {1: 10.0, 2: 10.5, 3: 9.0}
    assert start_flash(flashes, 2, 10.55) == {1: 10.0, 2: 10.55}  # Slot 3's flash ended long ago
    assert start_flash({}, 4, 1.0) == {4: 1.0}
