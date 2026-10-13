from stratagem_caller.arming import ArmingWindow, Outcome, Press
from stratagem_caller.reader import Reading

CODES = {1: "DDUR", 2: "DLRDLR", 4: "UUDD"}
OPEN = Reading(codes=CODES, menu_open=True)
CLOSED = Reading()
ALL_ON_COOLDOWN = Reading(menu_open=True)


def unreadable(slot, codes=CODES):
    return Reading(
        codes={s: c for s, c in codes.items() if s != slot},
        unreadable={slot},
        menu_open=True,
    )


class Script:
    """A scripted watch: Readings and key presses at chosen times, decisions out."""

    def __init__(self):
        self.window = ArmingWindow(started=0.0)

    def see(self, reading, *times):
        decided = [self.window.offer(reading, now) for now in times]
        return decided[-1]

    def open_for_a_while(self):
        assert self.see(OPEN, 0.25, 0.3) is None
        return self


def test_trigger_key_calls_at_once_when_the_slot_is_already_confirmed():
    s = Script().open_for_a_while()
    assert s.window.press(2, now=0.31) == Press(True, Outcome("call", "DLRDLR"))


def test_trigger_key_works_many_seconds_after_the_call_key():
    s = Script().open_for_a_while()
    for t in range(1, 40):
        s.see(OPEN, t * 0.5)
    assert s.window.press(1, now=25.0) == Press(True, Outcome("call", "DDUR"))


def test_trigger_key_is_held_until_two_readings_agree_on_the_slot():
    s = Script()
    assert s.window.press(2, now=0.05) == Press(True, None)
    assert s.see(OPEN, 0.25) is None
    assert s.see(OPEN, 0.3) == Outcome("call", "DLRDLR")


def test_disagreeing_readings_are_not_trusted():
    s = Script()
    s.window.press(2, now=0.05)
    shortened = Reading(codes={2: "DLR"}, menu_open=True)
    assert s.see(shortened, 0.2) is None
    assert s.see(OPEN, 0.27) is None
    assert s.see(OPEN, 0.34) == Outcome("call", "DLRDLR")


def test_slot_that_cannot_be_called_beeps_at_once_and_a_second_key_is_accepted():
    s = Script().open_for_a_while()
    assert s.window.press(3, now=1.0) == Press(True, Outcome("beep"))
    assert s.window.press(1, now=1.5) == Press(True, Outcome("call", "DDUR"))


def test_slot_beyond_the_last_beeps():
    s = Script().open_for_a_while()
    assert s.window.press(9, now=1.0) == Press(True, Outcome("beep"))


def test_open_menu_with_nothing_callable_beeps():
    s = Script()
    assert s.see(ALL_ON_COOLDOWN, 0.3, 0.35) is None
    assert s.window.press(1, now=0.4) == Press(True, Outcome("beep"))


def test_beeping_does_not_end_the_watch():
    s = Script().open_for_a_while()
    s.window.press(3, now=1.0)
    assert s.see(OPEN, 1.1, 1.2) is None
    assert s.window.press(2, now=1.3).outcome == Outcome("call", "DLRDLR")


def test_unreadable_slot_is_held_and_called_once_it_clears():
    s = Script()
    s.see(unreadable(2), 0.25, 0.3)
    assert s.window.press(2, now=0.4) == Press(True, None)
    assert s.see(unreadable(2), 0.45) is None
    assert s.see(OPEN, 0.5) is None
    assert s.see(OPEN, 0.55) == Outcome("call", "DLRDLR")


def test_unreadable_slot_beeps_if_it_stays_unreadable():
    s = Script()
    s.see(unreadable(2), 0.25, 0.3)
    s.window.press(2, now=0.4)
    outcome = None
    t = 0.4
    while outcome is None and t < 5:
        t += 0.05
        outcome = s.see(unreadable(2), t)
    assert outcome == Outcome("beep")
    assert t < 2.0  # a short limit


def test_slot_that_is_not_callable_for_one_reading_only_is_not_a_beep():
    s = Script().open_for_a_while()
    s.see(unreadable(2), 0.35)
    assert s.window.press(2, now=0.36) == Press(True, None)


def test_menu_still_opening_holds_the_key_and_waits_for_the_menu():
    s = Script()
    s.window.press(2, now=0.05)
    for t in (0.15, 0.25, 0.35, 0.45):
        assert s.see(CLOSED, t) is None  # slow to open: 500 ms
    assert s.see(OPEN, 0.55) is None
    assert s.see(OPEN, 0.6) == Outcome("call", "DLRDLR")


def test_key_is_handed_back_when_no_menu_ever_appears():
    s = Script()
    s.window.press(2, now=0.05)
    outcome = None
    t = 0.05
    while outcome is None and t < 5:
        t += 0.05
        outcome = s.see(CLOSED, t)
    assert outcome == Outcome("pass")
    assert t < 2.5


def test_closed_menu_with_no_key_pending_ends_the_watch():
    s = Script().open_for_a_while()
    assert s.see(CLOSED, 1.0) is None
    assert s.see(CLOSED, 1.05) == Outcome("closed")


def test_after_the_watch_ends_trigger_keys_are_not_touched():
    s = Script().open_for_a_while()
    s.see(CLOSED, 1.0, 1.05)
    assert s.window.press(1, now=1.1) == Press(False, None)


def test_one_closed_reading_does_not_end_the_watch():
    s = Script().open_for_a_while()
    assert s.see(CLOSED, 1.0) is None
    assert s.see(OPEN, 1.05) is None
    assert s.see(CLOSED, 1.1) is None
    assert s.window.press(1, now=1.12).taken


def test_menu_is_never_judged_closed_during_the_opening_grace():
    s = Script()
    for t in (0.02, 0.04, 0.06, 0.08, 0.1, 0.2, 0.3, 0.4):
        assert s.see(CLOSED, t) is None


def test_after_a_call_trigger_keys_are_not_acted_on():
    s = Script().open_for_a_while()
    assert s.window.press(1, now=0.4).outcome == Outcome("call", "DDUR")
    assert s.window.press(2, now=0.45) == Press(False, None)
    assert s.see(OPEN, 0.5, 0.55) is None


def test_a_held_key_that_is_called_does_not_call_again():
    s = Script()
    s.window.press(1, now=0.1)
    s.see(OPEN, 0.2)
    assert s.see(OPEN, 0.25) == Outcome("call", "DDUR")
    assert s.see(OPEN, 0.3, 0.35) is None


def test_second_call_key_press_forgets_what_was_confirmed():
    s = Script().open_for_a_while()
    s.window.restart(now=2.0)
    assert s.window.press(2, now=2.05) == Press(True, None)  # not called off the old menu


def test_open_close_open_with_the_call_key_follows_the_screen():
    s = Script().open_for_a_while()
    s.window.restart(now=2.0)  # closes the menu
    assert s.see(CLOSED, 2.1, 2.15) == Outcome("closed")
    s = Script()
    s.window.restart(now=0.1)  # opens again while still within the first watch
    assert s.see(OPEN, 0.3, 0.35) is None
    assert s.window.press(2, now=0.4).outcome == Outcome("call", "DLRDLR")


def test_menu_closed_for_a_reason_the_tool_did_not_cause_is_noticed():
    s = Script().open_for_a_while()
    for t in (5.0, 5.05):
        outcome = s.see(CLOSED, t)
    assert outcome == Outcome("closed")


def test_slot_calls_what_the_menu_now_shows_there():
    s = Script().open_for_a_while()
    shifted = Reading(codes={1: "UDUD", 2: "DDUR", 3: "DLRDLR", 4: "UUDD"}, menu_open=True)
    s.see(shifted, 1.0, 1.05)
    assert s.window.press(2, now=1.1).outcome == Outcome("call", "DDUR")


def test_second_trigger_key_while_one_is_held_replaces_it():
    s = Script()
    s.window.press(1, now=0.1)
    assert s.window.press(2, now=0.15).taken
    s.see(OPEN, 0.2)
    assert s.see(OPEN, 0.25) == Outcome("call", "DLRDLR")
