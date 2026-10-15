import numpy as np
import pytest

from stratagem_caller.arming import Outcome
from stratagem_caller.reader import Reading
from stratagem_caller.router import REPEAT_GAP, KeyEvent, KeyRouter
from stratagem_caller.winkeys import Key

W = Key("w", 17, False)
A = Key("a", 30, False)
S = Key("s", 31, False)
D = Key("d", 32, False)
SHIFT = Key("shift", 42, False)
CALL = Key("b", 48, False)
ONE = Key("1", 2, False)
TWO = Key("2", 3, False)
ZERO = Key("0", 11, False)
REINFORCE = Key("page down", 81, True)
USE = Key("e", 18, False)
RETURN = Key("enter", 28, False)
TITLE = "HELLDIVERS 2"
MENU = Reading(codes={1: "DDUR", 2: "DLRDLR"}, menu_open=True)

HELD_KEYS = {
    "w": [W],
    "a": [A],
    "s": [S],
    "d": [D],
    "shift": [SHIFT],
    "w+shift": [W, SHIFT],
    "w+d+shift": [W, D, SHIFT],
    "wasd+shift": [W, A, S, D, SHIFT],
}


class Keyboard:
    """A scripted keyboard: feed it presses and releases at chosen times."""

    def __init__(self, focused=TITLE, terminal_key=ONE):
        self.now = 0.0
        self.focused = focused
        self.sending = False
        self.entering_code = False
        self.lines = []
        self.router = KeyRouter(
            call_key=CALL,
            use_key=USE,
            terminal_key=terminal_key,
            direct_keys={REINFORCE: "DDDUUR"},
            trigger_keys={ONE: 1, TWO: 2, ZERO: 10},
            window_title=TITLE,
            clock=lambda: self.now,
            foreground_title=lambda: self.focused,
            is_sending=lambda: self.sending,
            is_entering_code=lambda: self.entering_code,
            log=self.lines.append,
        )

    def down(self, key, at):
        self.now = at
        return self.router.handle(KeyEvent(key.scan_code, False, "down", at))

    def up(self, key, at):
        self.now = at
        return self.router.handle(KeyEvent(key.scan_code, False, "up", at))

    def hold(self, keys, at):
        for key in keys:
            assert self.down(key, at).let_through

    def repeat(self, keys, start, stop, every=0.033):
        """Held keys auto-repeating between two times."""
        at = start
        while at < stop:
            self.hold(keys, at)
            at += every

    def window_taken(self):
        window = self.router._window
        return window is not None and window.slot is not None


@pytest.fixture(params=HELD_KEYS.values(), ids=HELD_KEYS.keys())
def held(request):
    return request.param


def test_call_key_opens_the_arming_window_and_passes_through():
    kb = Keyboard()
    decision = kb.down(CALL, 0.0)
    assert decision.let_through
    assert decision.start_watching is not None


def test_trigger_key_is_taken_with_movement_keys_held(held):
    kb = Keyboard()
    kb.hold(held, 0.0)
    kb.up(CALL, 0.15)
    kb.down(CALL, 0.2)
    assert not kb.down(ONE, 0.4).let_through
    assert kb.window_taken()


def test_trigger_key_is_taken_while_held_keys_repeat_before_between_and_after(held):
    kb = Keyboard()
    kb.hold(held, 0.0)
    kb.repeat(held, 0.033, 0.2)
    kb.up(CALL, 0.15)
    kb.down(CALL, 0.2)
    kb.repeat(held, 0.233, 0.4)
    assert not kb.down(ONE, 0.4).let_through
    kb.repeat(held, 0.433, 0.7)
    assert kb.window_taken()


def test_trigger_key_is_taken_when_a_held_key_is_released_between_call_and_trigger(held):
    kb = Keyboard()
    kb.hold(held, 0.0)
    kb.repeat(held, 0.033, 0.3)
    kb.down(CALL, 0.3)
    for key in held:
        assert kb.up(key, 0.35).let_through
    assert not kb.down(ONE, 0.5).let_through
    assert kb.window_taken()


def test_trigger_key_is_taken_when_movement_keys_are_pressed_between_call_and_trigger():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    kb.hold([W, SHIFT], 0.2)
    assert not kb.down(ONE, 0.4).let_through


def test_held_keys_reach_the_game_throughout_and_are_released_normally(held):
    kb = Keyboard()
    kb.hold(held, 0.0)
    kb.down(CALL, 0.1)
    kb.down(ONE, 0.2)
    kb.repeat(held, 0.1, 0.5)
    for key in held:
        assert kb.up(key, 0.6).let_through


def test_trigger_key_is_taken_when_its_previous_key_up_was_never_seen():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    assert not kb.down(ONE, 0.2).let_through
    # The Trigger Key's key-up never arrives, then the window closes and the player tries again.
    kb.router.close_window()
    kb.down(CALL, 5.0)
    assert not kb.down(ONE, 5.2).let_through
    assert kb.window_taken()


def test_trigger_key_is_taken_when_its_key_up_was_never_seen_and_movement_keys_are_held(held):
    kb = Keyboard()
    kb.hold(held, 0.0)
    kb.down(CALL, 0.1)
    kb.down(ONE, 0.2)
    kb.router.close_window()
    kb.repeat(held, 0.233, 5.0, every=0.5)
    kb.down(CALL, 5.0)
    assert not kb.down(ONE, 5.2).let_through
    assert kb.window_taken()


def test_trigger_key_pressed_just_after_the_repeat_delay_is_a_new_press():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    kb.down(ONE, 0.1)
    kb.router.close_window()
    kb.up(CALL, 0.15)
    kb.down(CALL, 0.2)
    assert not kb.down(ONE, 0.1 + REPEAT_GAP + 0.01).let_through
    assert kb.window_taken()


def test_trigger_key_pressed_within_the_repeat_delay_of_its_previous_press_is_a_repeat():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    kb.down(ONE, 0.1)
    kb.router.close_window()
    kb.up(CALL, 0.15)
    kb.down(CALL, 0.2)
    kb.down(ONE, 0.1 + REPEAT_GAP)
    assert not kb.window_taken()


def test_lost_key_up_of_a_swallowed_key_does_not_swallow_a_later_key_up():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    kb.down(ONE, 0.2)  # taken; its key-up is lost
    kb.router.close_window()
    kb.focused = "Notepad"
    assert kb.down(ONE, 5.0).let_through  # an ordinary key in another window
    assert kb.up(ONE, 5.1).let_through


def test_call_key_is_acted_on_when_its_previous_key_up_was_never_seen():
    kb = Keyboard()
    assert kb.down(CALL, 0.0).start_watching is not None
    kb.router.close_window()
    assert kb.down(CALL, 4.0).start_watching is not None


def test_held_trigger_key_repeating_is_swallowed_and_not_taken_twice():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    kb.down(ONE, 0.1)
    assert not kb.down(ONE, 0.5).let_through
    assert not kb.down(ONE, 0.533).let_through
    assert not kb.up(ONE, 0.6).let_through


def test_trigger_key_is_an_ordinary_key_outside_the_arming_window():
    kb = Keyboard()
    assert kb.down(ONE, 0.0).let_through
    assert not kb.window_taken()


def test_trigger_key_long_after_the_call_key_is_still_taken_while_the_menu_is_open():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.router.offer(window, MENU)
    kb.now = 0.1
    kb.router.offer(window, MENU)
    kb.now = 12.0
    decision = kb.down(ONE, 12.0)
    assert not decision.let_through
    assert decision.outcome == Outcome("call", "DDUR")
    assert "Call DDUR" in kb.lines[-1]


def test_trigger_key_is_an_ordinary_key_again_after_a_call():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.router.offer(window, MENU)
    kb.now = 0.1
    kb.router.offer(window, MENU)
    kb.down(ONE, 0.2)
    kb.up(ONE, 0.25)
    assert kb.down(TWO, 0.5).let_through


def test_beep_swallows_the_key_and_the_watch_goes_on():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.router.offer(window, MENU)
    kb.now = 0.1
    kb.router.offer(window, MENU)
    three = Key("3", 4, False)
    kb.router.trigger_keys[three] = 3
    decision = kb.down(three, 0.5)
    assert not decision.let_through and decision.outcome == Outcome("beep")
    kb.up(three, 0.55)
    assert kb.router.is_current(window)
    assert kb.down(ONE, 0.8).outcome == Outcome("call", "DDUR")


def test_second_call_key_press_keeps_watching_instead_of_starting_again():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.up(CALL, 0.05)
    assert kb.down(CALL, 3.0).start_watching is None
    assert kb.router.is_current(window)


def test_call_key_after_the_watch_ended_starts_a_new_one():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.router.offer(window, Reading(menu_open=True))
    kb.down(ONE, 0.2)
    kb.router.finish(window, Outcome("call", "DDUR"))
    assert kb.down(CALL, 4.0).start_watching is not None


def test_held_trigger_key_is_returned_when_the_watch_hands_it_back():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.down(TWO, 0.1)
    assert kb.router.finish(window, Outcome("pass")) == TWO
    assert not kb.router.is_current(window)


def test_keys_are_ignored_in_other_windows():
    kb = Keyboard(focused="Notepad")
    assert kb.down(CALL, 0.0).start_watching is None
    assert kb.down(ONE, 0.2).let_through


def test_keys_are_ignored_while_the_tool_is_typing_or_paused():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    kb.sending = True
    assert kb.down(ONE, 0.2).let_through
    kb.sending = False
    kb.router.paused = True
    assert kb.down(TWO, 0.4).let_through


def test_direct_key_calls_with_movement_keys_held(held):
    kb = Keyboard()
    kb.hold(held, 0.0)
    decision = kb.down(REINFORCE, 0.3)
    assert not decision.let_through
    assert decision.direct_code == "DDDUUR"
    assert not kb.up(REINFORCE, 0.4).let_through


def test_direct_key_calls_when_its_previous_key_up_was_never_seen():
    kb = Keyboard()
    kb.down(REINFORCE, 0.0)
    assert kb.down(REINFORCE, 3.0).direct_code == "DDDUUR"


# --- the log ---


def test_log_says_why_a_trigger_key_was_not_taken():
    kb = Keyboard()
    kb.down(ONE, 0.0)
    assert len(kb.lines) == 1
    assert "Slot 1" in kb.lines[0] and "not in the Arming Window" in kb.lines[0]


def test_log_says_a_repeat_was_ignored():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    kb.down(ONE, 0.1)
    kb.down(ONE, 0.5)
    assert "ignored as repeat" in kb.lines[-1]


def test_log_has_no_line_for_other_keys():
    kb = Keyboard()
    kb.repeat([W, A], 0.0, 1.0)
    kb.down(CALL, 1.0)
    assert kb.lines == []


def test_log_records_the_call_and_the_reading_it_was_made_from():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.down(TWO, 0.1)
    assert "waiting for Reading" in kb.lines[-1] and "none yet" in kb.lines[-1]
    kb.now = 0.2
    assert kb.router.offer(window, MENU) is None
    kb.now = 0.3
    outcome = kb.router.offer(window, MENU)
    assert outcome == Outcome("call", "DLRDLR")
    kb.router.finish(window, outcome)
    assert "Slot 2" in kb.lines[-1]
    assert "Call DLRDLR" in kb.lines[-1]
    assert "Slots 1,2" in kb.lines[-1]


def test_log_records_a_beep_and_a_hand_back():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.down(ONE, 0.1)
    kb.router.finish(window, Outcome("pass"))
    assert "handed back" in kb.lines[-1]
    window = kb.down(CALL, 5.0).start_watching
    kb.down(TWO, 5.1)
    kb.router.finish(window, Outcome("beep"))
    assert "beep" in kb.lines[-1]
    assert kb.router.is_current(window)


def test_log_records_a_direct_key_call():
    kb = Keyboard()
    kb.down(REINFORCE, 0.0)
    assert "DDDUUR" in kb.lines[-1]


def watching(kb):
    kb.down(CALL, 0.0)
    window = kb.router._window
    kb.router.offer(window, MENU)
    kb.router.offer(window, MENU)
    return window


def test_pausing_ends_the_watch_and_a_later_trigger_key_is_not_touched():
    kb = Keyboard()
    watching(kb)
    assert kb.router.end_watch("paused") is None
    kb.router.paused = True
    assert kb.down(ONE, 1.0).let_through
    kb.router.paused = False
    assert kb.down(ONE, 3.0).let_through


def test_pausing_hands_back_a_trigger_key_that_was_held():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    assert not kb.down(ONE, 0.05).let_through  # held: no Reading yet
    assert kb.router.end_watch("paused") == ONE
    assert kb.router.end_watch("paused") is None  # only once


def test_pausing_logs_why_the_watch_ended():
    kb = Keyboard()
    watching(kb)
    kb.router.end_watch("paused")
    assert any("paused" in line for line in kb.lines)


def test_focus_loss_ends_the_watch_and_no_further_readings_are_taken():
    kb = Keyboard()
    window = watching(kb)
    kb.focused = "Notepad"
    now_outcome = kb.router.offer(window, MENU)
    assert now_outcome == Outcome("focus")
    kb.router.finish(window, now_outcome)
    assert not kb.router.is_current(window)
    assert any("focus" in line for line in kb.lines)


def test_after_focus_loss_the_next_call_key_press_starts_a_new_watch():
    kb = Keyboard()
    window = watching(kb)
    kb.focused = "Notepad"
    kb.router.finish(window, kb.router.offer(window, MENU))
    kb.focused = TITLE
    assert kb.down(CALL, 5.0).start_watching is not None


def test_safety_limit_is_logged_and_hands_back_a_held_key():
    kb = Keyboard()
    window = watching(kb)
    t = 0.0
    outcome = None
    while outcome is None and t < 600:
        t += 0.25
        kb.now = t
        outcome = kb.router.offer(window, MENU)
    assert outcome == Outcome("limit")
    assert kb.router.finish(window, outcome) is None
    assert any("limit" in line for line in kb.lines)
    assert kb.down(ONE, t + 1).let_through


def test_router_tells_the_worker_how_long_to_wait_between_readings():
    kb = Keyboard()
    window = watching(kb)
    modest = kb.router.reading_delay(window)
    kb.down(CALL, 5.0)  # opening or closing again
    assert kb.router.reading_delay(window) < modest


CLOSED = Reading()


def test_digit_pressed_while_the_menu_is_closing_is_held_and_handed_back_once_closed():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.now = 0.2
    kb.router.offer(window, MENU)
    kb.now = 0.25
    kb.router.offer(window, MENU)
    kb.down(CALL, 2.0)  # closing the menu
    decision = kb.down(ONE, 2.02)
    assert not decision.let_through and decision.outcome is None
    for at in (2.05, 2.1):
        kb.now = at
        assert kb.router.offer(window, MENU) is None
    kb.now = 2.15
    assert kb.router.offer(window, CLOSED) is None
    kb.now = 2.2
    outcome = kb.router.offer(window, CLOSED)
    assert outcome == Outcome("pass")
    assert kb.router.finish(window, outcome) == ONE


def test_held_trigger_key_stays_held_when_the_call_key_is_pressed_again():
    kb = Keyboard()
    kb.down(CALL, 0.0)
    assert not kb.down(ONE, 0.05).let_through
    kb.down(CALL, 0.3)
    assert kb.router.end_watch("paused") == ONE


def test_a_finished_watch_cannot_wipe_the_held_key_of_a_new_one():
    kb = Keyboard()
    old = kb.down(CALL, 0.0).start_watching
    kb.now = 61.0
    outcome = kb.router.offer(old, MENU)
    assert outcome == Outcome("limit")  # the worker has not called finish yet
    new = kb.down(CALL, 61.1).start_watching
    assert new is not None and new is not old
    assert not kb.down(ONE, 61.2).let_through
    assert kb.router.finish(old, outcome) is None
    assert kb.router.end_watch("paused") == ONE


def test_a_mark_describes_the_watch_and_the_latest_reading():
    kb = Keyboard()
    assert kb.router.describe() == "not watching; latest Reading: none yet"
    window = kb.down(CALL, 0.0).start_watching
    kb.down(TWO, 0.1)
    assert kb.router.describe() == "watching, Trigger Key held for Slot 2; latest Reading: none yet"
    kb.router.finish(window, Outcome("pass"))
    window = kb.down(CALL, 2.0).start_watching
    kb.router.offer(window, MENU)
    assert kb.router.describe() == "watching; latest Reading: menu open, Slots 1,2"
    kb.router.paused = True
    assert kb.router.describe().startswith("paused;")


def test_direct_key_presses_the_call_key_when_no_menu_is_watched():
    kb = Keyboard()
    assert kb.down(REINFORCE, 0.0).direct_presses_call_key


def test_direct_key_skips_the_call_key_and_ends_the_watch_when_the_menu_was_just_opened():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.up(CALL, 0.05)
    kb.down(TWO, 0.1)  # held, waiting for a Reading
    decision = kb.down(REINFORCE, 0.2)
    assert decision.direct_code == "DDDUUR" and not decision.direct_presses_call_key
    assert not kb.router.is_current(window)
    assert "Call Key skipped" in kb.lines[-1]


def test_direct_key_presses_the_call_key_while_a_call_key_press_is_closing_the_menu():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.up(CALL, 0.05)
    kb.router.offer(window, MENU)
    kb.now = 0.1
    kb.router.offer(window, MENU)
    kb.down(CALL, 2.0)  # closing the open menu
    assert kb.down(REINFORCE, 2.1).direct_presses_call_key


# --- Key Caps: what the Overlay should show, by Slot ---


def listing(*slots):
    """A Reading of an open menu listing `slots`, callable or not."""
    icon = np.zeros((86, 86, 3), np.uint8)
    return Reading(codes={s: "DDUR" for s in slots if s == 1}, icons={s: icon for s in slots}, menu_open=True)


def watching_an_open_menu(*slots):
    """A Keyboard whose watch has confirmed a menu listing `slots` open."""
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    kb.up(CALL, 0.05)
    for at in (0.3, 0.35):
        kb.now = at
        kb.router.offer(window, listing(*slots))
    return kb, window


def test_key_caps_show_each_listed_slots_trigger_key_name():
    kb, _ = watching_an_open_menu(1, 2)
    assert kb.router.key_caps() == {1: "1", 2: "2"}


def test_slot_10_shows_the_key_zero():
    kb, _ = watching_an_open_menu(1, 2, 10)
    assert kb.router.key_caps() == {1: "1", 2: "2", 10: "0"}


def test_slot_without_a_trigger_key_gets_no_key_cap():
    kb, _ = watching_an_open_menu(1, 2, 3)
    assert kb.router.key_caps() == {1: "1", 2: "2"}


def test_key_cap_names_follow_the_configured_trigger_keys():
    kb, _ = watching_an_open_menu(1, 2)
    kb.router.trigger_keys = {Key("f5", 63, False): 1, Key("page down", 81, True): 2}
    assert kb.router.key_caps() == {1: "f5", 2: "page down"}


def test_no_key_caps_before_the_menu_is_confirmed_open():
    kb = Keyboard()
    window = kb.down(CALL, 0.0).start_watching
    assert kb.router.key_caps() == {}
    kb.now = 0.3
    kb.router.offer(window, listing(1, 2))
    assert kb.router.key_caps() == {}


def test_no_key_caps_outside_a_watch():
    assert Keyboard().router.key_caps() == {}


def test_key_caps_hide_when_the_game_loses_focus_and_the_watch_ends_with_it():
    kb, window = watching_an_open_menu(1, 2)
    kb.focused = "Notepad"
    assert kb.router.key_caps() == {}
    outcome = kb.router.offer(window, listing(1, 2))
    kb.router.finish(window, outcome)
    kb.focused = TITLE
    assert kb.router.key_caps() == {}


def test_key_caps_hide_when_the_tool_is_paused():
    kb, window = watching_an_open_menu(1, 2)
    kb.router.paused = True
    assert kb.router.key_caps() == {}
    kb.router.end_watch("paused")
    kb.router.paused = False
    assert kb.router.key_caps() == {}


def test_key_caps_hide_when_a_call_starts():
    kb, _ = watching_an_open_menu(1, 2)
    assert kb.down(ONE, 0.4).outcome == Outcome("call", "DDUR")
    assert kb.router.key_caps() == {}


def test_key_caps_stay_when_a_trigger_key_beeps():
    kb, _ = watching_an_open_menu(1, 2)
    assert kb.down(TWO, 1.0).outcome == Outcome("beep")
    assert kb.router.key_caps() == {1: "1", 2: "2"}


def test_key_caps_hide_when_the_call_key_closes_the_menu():
    kb, _ = watching_an_open_menu(1, 2)
    kb.down(CALL, 1.0)
    assert kb.router.key_caps() == {}


def test_key_caps_hide_for_a_direct_key():
    kb, _ = watching_an_open_menu(1, 2)
    kb.down(REINFORCE, 1.0)
    assert kb.router.key_caps() == {}


def test_key_caps_stay_while_fire_hides_the_menu_and_hide_when_it_is_closed():
    kb, window = watching_an_open_menu(1, 2)
    kb.now = 0.4
    kb.router.offer(window, Reading())
    assert kb.router.key_caps() == {1: "1", 2: "2"}
    outcome = None
    for at in (0.5, 0.6, 0.7, 1.0, 1.1):
        kb.now = at
        outcome = kb.router.offer(window, Reading()) or outcome
    assert outcome == Outcome("closed")
    kb.router.finish(window, outcome)
    assert kb.router.key_caps() == {}


def test_two_trigger_keys_for_one_slot_show_the_first_in_settings_order():
    kb, _ = watching_an_open_menu(1)
    kb.router.trigger_keys = {Key("f5", 63, False): 1, ONE: 1}
    assert kb.router.key_caps() == {1: "f5"}


# --- the red flash: which Key Cap a beep flashes ---


def red_at(kb, *times):
    """The Slots in a red step of a flash at each of `times`."""
    out = []
    for at in times:
        kb.now = at
        out.append(set(kb.router.red_key_caps()))
    return out


def test_a_beep_flashes_that_slots_key_cap_red_twice():
    kb, _ = watching_an_open_menu(1, 2)
    assert kb.down(TWO, 1.0).outcome == Outcome("beep")
    assert red_at(kb, 1.0, 1.1, 1.2, 1.4, 1.5, 1.6, 2.0) == [
        {2}, {2}, set(), {2}, set(), set(), set(),
    ]  # fmt: skip


def test_a_slot_that_can_be_called_does_not_flash():
    kb, _ = watching_an_open_menu(1, 2)
    assert kb.down(ONE, 1.0).outcome == Outcome("call", "DDUR")
    assert red_at(kb, 1.0, 1.2) == [set(), set()]


def test_a_beep_for_a_slot_beyond_the_end_of_the_menu_flashes_nothing():
    kb, _ = watching_an_open_menu(1, 2)
    assert kb.down(ZERO, 1.0).outcome == Outcome("beep")
    assert red_at(kb, 1.0, 1.2, 1.4) == [set(), set(), set()]


def test_a_second_beep_during_a_flash_restarts_it():
    kb, _ = watching_an_open_menu(1, 2)
    kb.down(TWO, 1.0)
    kb.up(TWO, 1.02)
    assert red_at(kb, 1.2) == [set()]  # between reds
    kb.down(TWO, 1.2)
    # Red again from the second beep (1.2 on), not on the first one's clock (1.0 on).
    assert red_at(kb, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8) == [{2}, {2}, set(), {2}, {2}, set()]


def test_two_slots_flash_on_their_own():
    kb, _ = watching_an_open_menu(1, 2, 3)
    three = Key("3", 4, False)
    kb.router.trigger_keys[three] = 3
    kb.down(TWO, 1.0)
    kb.down(three, 1.1)
    assert red_at(kb, 1.05, 1.15, 1.2, 1.3) == [{2}, {3}, {3}, {2}]


def test_a_slot_that_stays_unreadable_flashes_when_it_finally_beeps():
    kb, window = watching_an_open_menu(1, 2)
    unreadable = Reading(unreadable={2}, icons=listing(1, 2).icons, menu_open=True)
    kb.now = 0.4
    kb.router.offer(window, unreadable)
    assert kb.down(TWO, 0.4).outcome is None  # waits for a Reading
    outcome, at = None, 0.4
    while outcome is None and at < 3:
        at += 0.05
        kb.now = at
        outcome = kb.router.offer(window, unreadable)
    assert outcome == Outcome("beep")
    assert red_at(kb, at) == [set()]  # not yet: the watch's thread has still to report it
    kb.router.finish(window, outcome)
    assert red_at(kb, at, at + 0.2) == [{2}, set()]


def test_no_red_key_cap_when_the_key_caps_are_hidden():
    kb, _ = watching_an_open_menu(1, 2)
    kb.down(TWO, 1.0)
    kb.now = 1.0
    kb.focused = "Notepad"
    assert kb.router.red_key_caps() == frozenset()
    kb.focused = TITLE
    kb.router.paused = True
    assert kb.router.red_key_caps() == frozenset()


def test_a_flash_does_not_carry_over_to_the_next_watch():
    kb, _ = watching_an_open_menu(1, 2)
    kb.down(TWO, 1.0)
    kb.up(TWO, 1.01)
    kb.router.end_watch("test")
    window = kb.down(CALL, 1.1).start_watching
    for at in (1.35, 1.4):  # the menu is confirmed open again while the old flash would be red
        kb.now = at
        kb.router.offer(window, listing(1, 2))
    assert kb.router.key_caps() == {1: "1", 2: "2"}
    assert kb.router.red_key_caps() == frozenset()
