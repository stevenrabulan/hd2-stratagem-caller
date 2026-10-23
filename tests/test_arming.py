import numpy as np

from stratagem_caller.arming import SAFETY_LIMIT, ArmingWindow, Outcome, Press
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


def test_slot_that_cannot_be_called_beeps_on_the_next_reading_and_a_second_key_is_accepted():
    s = Script().open_for_a_while()
    assert s.window.press(3, now=1.0) == Press(True, None)
    assert s.see(OPEN, 1.05) == Outcome("beep")
    assert s.window.press(1, now=1.5) == Press(True, Outcome("call", "DDUR"))


def test_slot_that_becomes_callable_as_its_key_is_pressed_is_called_not_beeped():
    # The Readings so far say Slot 3 cannot be called, but it comes off cooldown just as its
    # Trigger Key goes down: the Readings taken after the press decide.
    s = Script().open_for_a_while()
    assert s.window.press(3, now=1.0) == Press(True, None)
    ready = Reading(codes={**CODES, 3: "URR"}, menu_open=True)
    assert s.see(ready, 1.05) is None
    assert s.see(ready, 1.1) == Outcome("call", "URR")


def test_slot_beyond_the_last_beeps():
    s = Script().open_for_a_while()
    assert s.window.press(9, now=1.0) == Press(True, None)
    assert s.see(OPEN, 1.05) == Outcome("beep")


def test_open_menu_with_nothing_callable_beeps():
    s = Script()
    assert s.see(ALL_ON_COOLDOWN, 0.3, 0.35, 0.6, 0.8) is None
    assert s.window.press(1, now=0.85) == Press(True, None)
    assert s.see(ALL_ON_COOLDOWN, 0.9) == Outcome("beep")


def test_beeping_does_not_end_the_watch():
    s = Script().open_for_a_while()
    s.window.press(3, now=1.0)
    assert s.see(OPEN, 1.05) == Outcome("beep")
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


def see_until_decided(s, reading, start, stop=10.0, every=0.05):
    """Keep showing `reading`; returns (outcome, time it was decided)."""
    t = start
    while t < stop:
        outcome = s.see(reading, t)
        if outcome is not None:
            return outcome, t
        t += every
    return None, t


def test_closed_menu_with_no_key_pending_ends_the_watch():
    s = Script().open_for_a_while()
    outcome, t = see_until_decided(s, CLOSED, 1.0)
    assert outcome == Outcome("closed")
    assert t < 3.0


def test_after_the_watch_ends_trigger_keys_are_not_touched():
    s = Script().open_for_a_while()
    outcome, t = see_until_decided(s, CLOSED, 1.0)
    assert s.window.press(1, now=t + 0.05) == Press(False, None)


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
    outcome, _ = see_until_decided(s, CLOSED, 5.0)
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


def keep_seeing_open(s, start, stop, every=0.25):
    t, outcome = start, None
    while t < stop and outcome is None:
        outcome = s.see(OPEN, t)
        t += every
    return outcome


def test_watch_that_runs_far_too_long_ends():
    s = Script().open_for_a_while()
    assert keep_seeing_open(s, 0.5, 600) == Outcome("limit")
    assert s.window.press(1, now=601) == Press(False, None)


def test_watch_still_works_after_half_a_minute():
    s = Script().open_for_a_while()
    assert keep_seeing_open(s, 0.5, 30) is None
    assert s.window.press(1, now=30.1).outcome == Outcome("call", "DDUR")


def test_call_key_press_starts_the_safety_limit_afresh():
    s = Script().open_for_a_while()
    keep_seeing_open(s, 0.5, 50)
    s.window.restart(now=50.0)
    s.see(OPEN, 50.3, 50.35)
    assert keep_seeing_open(s, 50.4, 100) is None


def test_reading_is_modest_while_the_menu_is_confirmed_open_and_no_key_waits():
    s = Script().open_for_a_while()
    modest = s.window.reading_delay()
    s2 = Script()
    s2.see(OPEN, 0.25)  # one Reading is not a confirmation
    opening = s2.window.reading_delay()
    s3 = Script().open_for_a_while()
    s3.window.press(2, now=0.4)  # called at once: nothing waiting, watch over
    s4 = Script()
    s4.see(unreadable(2), 0.25, 0.3)
    s4.window.press(2, now=0.31)
    waiting = s4.window.reading_delay()
    assert opening < modest
    assert waiting < modest


def test_reading_is_fast_right_after_the_call_key_is_pressed_again():
    s = Script().open_for_a_while()
    modest = s.window.reading_delay()
    s.window.restart(now=3.0)
    assert s.window.reading_delay() < modest


def test_reading_is_fast_while_a_held_key_waits_for_a_closed_menu_to_open():
    s = Script()
    fast = s.window.reading_delay()
    s.window.press(1, now=0.05)
    assert s.window.reading_delay() == fast


# --- an open menu hidden for a moment (fire in front of it) ---


def test_open_menu_hidden_behind_fire_for_a_moment_is_not_judged_closed():
    s = Script().open_for_a_while()
    t = 1.0
    while t < 1.4:
        assert s.see(CLOSED, t) is None
        t += 0.05
    assert s.see(OPEN, 1.45, 1.5) is None
    assert s.window.press(1, now=1.55) == Press(True, Outcome("call", "DDUR"))


def test_trigger_key_pressed_while_the_menu_is_hidden_is_held_then_called():
    s = Script().open_for_a_while()
    s.see(CLOSED, 1.0, 1.05, 1.1)
    assert s.window.press(2, now=1.12) == Press(True, None)
    assert s.see(CLOSED, 1.15) is None
    assert s.see(OPEN, 1.2) is None
    assert s.see(OPEN, 1.25) == Outcome("call", "DLRDLR")


def test_missing_slot_pressed_while_hidden_beeps_only_once_the_menu_is_back():
    s = Script().open_for_a_while()
    s.see(CLOSED, 1.0, 1.05, 1.1)
    assert s.window.press(3, now=1.12) == Press(True, None)
    s.see(OPEN, 1.2, 1.25)
    outcome, _ = see_until_decided(s, OPEN, 1.3, stop=3.0)
    assert outcome == Outcome("beep")


def test_menu_hidden_for_good_is_judged_closed_and_the_held_key_is_handed_back():
    s = Script().open_for_a_while()
    s.see(CLOSED, 1.0)
    assert s.window.press(2, now=1.02) == Press(True, None)
    outcome, t = see_until_decided(s, CLOSED, 1.05)
    assert outcome == Outcome("pass")
    assert t > 1.3  # not on the first signs of fire
    assert t < 3.0


def test_reading_is_fast_while_the_menu_is_hidden():
    s = Script().open_for_a_while()
    modest = s.window.reading_delay()
    s.see(CLOSED, 1.0)
    assert s.window.reading_delay() < modest


# --- the Call Key pressed while the menu is open: the player is closing it ---


def closing(s, at=2.0):
    s.window.restart(now=at)
    return s


def test_digit_pressed_while_the_menu_is_closing_is_held_not_called_or_beeped():
    s = closing(Script().open_for_a_while())
    assert s.window.press(1, now=2.02) == Press(True, None)
    assert s.see(OPEN, 2.05, 2.1, 2.15) is None  # the animation still shows the menu
    s2 = closing(Script().open_for_a_while())
    assert s2.window.press(3, now=2.02) == Press(True, None)
    assert s2.see(OPEN, 2.05, 2.1, 2.15) is None


def test_held_key_is_handed_back_when_the_menu_is_confirmed_closed():
    s = closing(Script().open_for_a_while())
    s.window.press(1, now=2.02)
    assert s.see(OPEN, 2.05, 2.1) is None
    assert s.see(CLOSED, 2.15) is None
    assert s.see(CLOSED, 2.2) == Outcome("pass")


def test_menu_still_open_long_after_the_call_key_is_treated_as_open():
    s = closing(Script().open_for_a_while())
    s.window.press(1, now=2.02)
    outcome, t = see_until_decided(s, OPEN, 2.05, stop=4.0)
    assert outcome == Outcome("call", "DDUR")
    assert t > 2.3  # not while the close animation could still be showing


def test_slot_missing_from_a_menu_still_open_after_the_call_key_beeps_in_the_end():
    s = closing(Script().open_for_a_while())
    s.window.press(3, now=2.02)
    outcome, _ = see_until_decided(s, OPEN, 2.05, stop=4.0)
    assert outcome == Outcome("beep")


# --- a held Trigger Key survives another Call Key press ---


def test_held_key_stays_held_when_the_call_key_is_pressed_again_before_the_menu_shows():
    s = Script()
    assert s.window.press(2, now=0.05) == Press(True, None)
    s.window.restart(now=0.1)
    assert s.see(OPEN, 0.2) is None
    assert s.see(OPEN, 0.25) == Outcome("call", "DLRDLR")


def test_held_key_is_handed_back_when_the_call_key_closes_the_menu():
    s = Script().open_for_a_while()
    s.see(unreadable(2), 0.35)
    assert s.window.press(2, now=0.36) == Press(True, None)
    s.window.restart(now=1.0)
    assert s.see(CLOSED, 1.1) is None
    assert s.see(CLOSED, 1.15) == Outcome("pass")


# --- rows that have not slid in yet ---


def test_slot_whose_row_has_not_slid_in_yet_is_held_and_called_when_it_arrives():
    s = Script()
    s.see(OPEN, 0.25, 0.3)
    assert s.window.press(3, now=0.31) == Press(True, None)
    arrived = Reading(codes={**CODES, 3: "UDUD"}, menu_open=True)
    assert s.see(arrived, 0.36) is None
    assert s.see(arrived, 0.41) == Outcome("call", "UDUD")


def test_slot_that_never_arrives_beeps_after_a_short_settle():
    s = Script()
    s.see(OPEN, 0.25, 0.3)
    assert s.window.press(3, now=0.31) == Press(True, None)
    outcome, t = see_until_decided(s, OPEN, 0.35, stop=3.0)
    assert outcome == Outcome("beep")
    assert t < 1.0


def test_confirmed_callable_slot_is_called_at_once_on_a_fresh_menu():
    s = Script()
    s.see(OPEN, 0.25, 0.3)
    assert s.window.press(1, now=0.31) == Press(True, Outcome("call", "DDUR"))


def test_menu_counts_as_shown_while_opening_and_once_open():
    s = Script()
    assert s.window.menu_shown()
    s.open_for_a_while()
    assert s.window.menu_shown()


def test_menu_does_not_count_as_shown_while_a_call_key_press_is_closing_it():
    s = Script().open_for_a_while()
    s.window.restart(1.0)
    assert not s.window.menu_shown()


def test_menu_does_not_count_as_shown_once_a_call_is_made():
    s = Script().open_for_a_while()
    s.window.press(1, now=0.31)
    assert not s.window.menu_shown()


# --- Key Caps: when they show, and on which Slots ---

ICON = np.zeros((86, 86, 3), np.uint8)


def listed(*slots, codes=CODES, menu_open=True):
    """A Reading of a menu that lists `slots` (an Icon in place at each), callable or not."""
    return Reading(
        codes={s: c for s, c in codes.items() if s in slots},
        icons={s: ICON for s in slots},
        menu_open=menu_open,
    )


MENU_OF_FOUR = listed(1, 2, 3, 4)  # Slot 3 is on cooldown: no Code, but an Icon


def key_cap_script():
    """A watch that has just confirmed MENU_OF_FOUR open."""
    s = Script()
    s.see(MENU_OF_FOUR, 0.25, 0.3)
    return s


def test_key_caps_wait_for_the_menu_to_be_confirmed_open():
    s = Script()
    assert s.window.key_cap_slots() == frozenset()
    s.see(MENU_OF_FOUR, 0.25)
    assert s.window.key_cap_slots() == frozenset()
    s.see(MENU_OF_FOUR, 0.3)
    assert s.window.key_cap_slots() == {1, 2, 3, 4}


def test_key_caps_include_slots_on_cooldown():
    assert key_cap_script().window.key_cap_slots() == {1, 2, 3, 4}
    assert 3 not in CODES


def test_slot_without_an_icon_in_place_gets_no_key_cap():
    s = Script()
    s.see(listed(1, 2), 0.25, 0.3)
    assert s.window.key_cap_slots() == {1, 2}


def test_key_caps_follow_the_slots_the_menu_lists_now():
    s = key_cap_script()
    s.see(listed(1, 2, 3, 4, 5, 6), 0.35, 0.4)
    assert s.window.key_cap_slots() == {1, 2, 3, 4, 5, 6}
    s.see(listed(1, 2, 3, 4, 5), 0.45, 0.5)
    assert s.window.key_cap_slots() == {1, 2, 3, 4, 5}


def test_key_caps_stay_while_the_menu_is_hidden_behind_fire():
    s = key_cap_script()
    assert s.see(CLOSED, 0.4) is None
    assert s.window.key_cap_slots() == {1, 2, 3, 4}
    assert s.see(CLOSED, 0.55) is None
    assert s.window.key_cap_slots() == {1, 2, 3, 4}


def test_key_caps_come_back_unchanged_when_the_menu_returns_from_hiding():
    s = key_cap_script()
    s.see(CLOSED, 0.4)
    s.see(MENU_OF_FOUR, 0.45)
    assert s.window.key_cap_slots() == {1, 2, 3, 4}


def test_key_caps_hide_when_the_menu_is_confirmed_closed():
    s = key_cap_script()
    outcome, _ = see_until_decided(s, CLOSED, 0.35, stop=3.0)
    assert outcome == Outcome("closed")
    assert s.window.key_cap_slots() == frozenset()


def test_key_caps_hide_when_a_call_is_made():
    s = key_cap_script()
    assert s.window.press(1, now=0.31).outcome == Outcome("call", "DDUR")
    assert s.window.key_cap_slots() == frozenset()


def test_key_caps_hide_when_a_held_key_is_called_on_a_later_reading():
    s = Script()
    s.see(MENU_OF_FOUR, 0.25, 0.3)
    s.see(CLOSED, 0.35)
    assert s.window.press(2, now=0.4) == Press(True, None)
    assert s.window.key_cap_slots() == {1, 2, 3, 4}
    assert s.see(MENU_OF_FOUR, 0.45) is None
    assert s.window.key_cap_slots() == {1, 2, 3, 4}
    assert s.see(MENU_OF_FOUR, 0.5) == Outcome("call", "DLRDLR")
    assert s.window.key_cap_slots() == frozenset()


def test_key_caps_stay_after_a_beep():
    s = key_cap_script()
    assert s.window.press(3, now=1.0) == Press(True, None)
    assert s.see(MENU_OF_FOUR, 1.05) == Outcome("beep")
    assert s.window.key_cap_slots() == {1, 2, 3, 4}


def test_key_caps_hide_when_the_call_key_closes_the_menu():
    s = key_cap_script()
    s.window.restart(1.0)
    assert s.window.key_cap_slots() == frozenset()


def test_key_caps_stay_hidden_after_a_close_until_the_menu_is_confirmed_open_again():
    s = key_cap_script()
    s.window.restart(1.0)
    s.see(MENU_OF_FOUR, 1.02)
    assert s.window.key_cap_slots() == frozenset()
    s.see(MENU_OF_FOUR, 1.4, 1.5)  # still open past the closing period: the press did not close it
    assert s.window.key_cap_slots() == {1, 2, 3, 4}


def test_key_caps_hide_when_the_safety_limit_ends_the_watch():
    s = key_cap_script()
    assert s.see(MENU_OF_FOUR, SAFETY_LIMIT) == Outcome("limit")
    assert s.window.key_cap_slots() == frozenset()


def test_key_caps_hide_when_the_call_key_is_pressed_while_the_menu_is_in_doubt():
    # Fire hides the menu, then the Call Key is pressed: nothing seen so far is trusted.
    s = key_cap_script()
    s.see(CLOSED, 0.4)
    assert s.window.key_cap_slots() == {1, 2, 3, 4}
    s.window.restart(0.5)
    assert s.window.key_cap_slots() == frozenset()
