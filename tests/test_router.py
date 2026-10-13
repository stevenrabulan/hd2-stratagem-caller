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
REINFORCE = Key("page down", 81, True)
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

    def __init__(self, focused=TITLE):
        self.now = 0.0
        self.focused = focused
        self.sending = False
        self.lines = []
        self.router = KeyRouter(
            call_key=CALL,
            direct_keys={REINFORCE: "DDDUUR"},
            trigger_keys={ONE: 1, TWO: 2},
            window_title=TITLE,
            clock=lambda: self.now,
            foreground_title=lambda: self.focused,
            is_sending=lambda: self.sending,
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
