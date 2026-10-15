"""The Use Key starts a Terminal watch; the Terminal Key is held back while a Terminal waits."""

import pytest
from test_router import CALL, ONE, RETURN, TITLE, USE, Keyboard, watching_an_open_menu

from stratagem_caller.arming import Outcome
from stratagem_caller.terminal_prompt import TerminalPrompt
from stratagem_caller.terminal_watch import GONE_FOR

NONE = TerminalPrompt.NONE
INTERACT = TerminalPrompt.INTERACT
MOVE = TerminalPrompt.MOVE_CURSOR


def terminal_waiting(prompt=INTERACT, **kwargs):
    """A keyboard on which the Use Key was pressed at 0.0 and `prompt` was read at 1.0."""
    kb = Keyboard(**kwargs)
    watch = kb.down(USE, 0.0).start_terminal_watch
    kb.up(USE, 0.1)
    assert watch is not None
    show(kb, watch, prompt, 1.0)
    return kb, watch


def show(kb, watch, prompt, at):
    kb.now = at
    kb.router.offer_terminal(watch, prompt)


def log_has(kb, text):
    return any(text in line for line in kb.lines)


def test_the_use_key_starts_a_terminal_watch_and_still_reaches_the_game():
    kb = Keyboard()
    decision = kb.down(USE, 0.0)
    assert decision.let_through
    assert decision.start_terminal_watch is not None
    assert log_has(kb, "use key e: Terminal watch started")
    assert kb.up(USE, 0.1).let_through


def test_a_held_use_key_starts_one_watch_not_one_per_repeat():
    kb = Keyboard()
    starts = [kb.down(USE, i * 0.033).start_terminal_watch for i in range(10)]
    assert sum(w is not None for w in starts) == 1


def test_another_use_key_press_restarts_the_running_watch_and_starts_no_second_one():
    kb, watch = terminal_waiting(NONE)
    kb.up(USE, 0.2)
    again = kb.down(USE, 3.0)
    assert again.let_through and again.start_terminal_watch is None
    assert log_has(kb, "use key e: Terminal watch restarted")
    # The 5 s count from the second press: the first press's 5 s are over at 5.0, this one's are not.
    for at in (5.5, 7.0, 7.9):
        show(kb, watch, NONE, at)
    assert kb.router.terminal_is_current(watch)
    show(kb, watch, NONE, 8.1)
    assert not kb.router.terminal_is_current(watch)


@pytest.mark.parametrize("why", ["paused", "not focused", "sending"])
def test_no_watch_starts_when_the_tool_is_paused_sending_or_the_game_is_not_focused(why):
    kb = Keyboard()
    kb.router.paused = why == "paused"
    kb.sending = why == "sending"
    kb.focused = "Notepad" if why == "not focused" else TITLE
    decision = kb.down(USE, 0.0)
    assert decision.let_through and decision.start_terminal_watch is None


def test_the_terminal_key_is_swallowed_while_the_prompt_reads_interact():
    kb, _ = terminal_waiting(INTERACT)
    decision = kb.down(ONE, 1.2)
    assert not decision.let_through
    assert decision.enter_code
    assert decision.outcome is None and not kb.window_taken()  # no Slot is called
    assert log_has(kb, "terminal key 1: swallowed, Terminal Prompt reads INTERACT")


def test_the_terminal_keys_repeats_and_key_up_are_swallowed_too():
    kb, _ = terminal_waiting(INTERACT)
    assert not kb.down(ONE, 1.2).let_through
    for at in (1.3, 1.4, 1.5):
        repeat = kb.down(ONE, at)
        assert not repeat.let_through and not repeat.enter_code  # one press, one decision
    assert not kb.up(ONE, 1.6).let_through


def test_the_terminal_key_up_is_swallowed_even_after_the_prompt_goes():
    kb, watch = terminal_waiting(INTERACT)
    kb.down(ONE, 1.2)
    show(kb, watch, NONE, 1.3)
    assert not kb.up(ONE, 1.4).let_through  # the game never saw the key go down


def test_each_press_of_the_terminal_key_is_a_decision():
    kb, _ = terminal_waiting(INTERACT)
    for start in (1.2, 3.0, 5.0):
        decision = kb.down(ONE, start)
        assert not decision.let_through and decision.enter_code
        kb.up(ONE, start + 0.1)


def test_another_key_can_be_the_terminal_key():
    kb, _ = terminal_waiting(INTERACT, terminal_key=RETURN)
    assert not kb.down(RETURN, 1.2).let_through
    assert kb.down(ONE, 1.5).let_through  # 1 is only a Trigger Key now


def test_the_terminal_key_behaves_as_before_while_the_prompt_reads_move_cursor():
    kb, _ = terminal_waiting(MOVE)
    decision = kb.down(ONE, 1.2)
    assert decision.let_through and not decision.enter_code
    assert log_has(kb, "terminal key 1: not swallowed, Terminal Prompt reads MOVE CURSOR")


def test_the_terminal_key_behaves_as_before_when_no_terminal_prompt_shows():
    kb, _ = terminal_waiting(NONE)
    decision = kb.down(ONE, 1.2)
    assert decision.let_through and not decision.enter_code
    assert log_has(kb, "terminal key 1: not swallowed, no Terminal Prompt")


def test_the_terminal_key_behaves_as_before_when_no_watch_is_running():
    kb = Keyboard()
    decision = kb.down(ONE, 0.0)
    assert decision.let_through and not decision.enter_code
    assert not log_has(kb, "terminal key")  # nothing to decide, so nothing logged


def test_the_terminal_key_is_a_trigger_key_while_the_stratagem_menu_is_watched():
    # At a Terminal with the Stratagem Menu opened for a Slot: 1 calls Slot 1, as it always did.
    kb, _ = terminal_waiting(INTERACT)
    kb.down(CALL, 1.1)
    decision = kb.down(ONE, 1.3)
    assert not decision.enter_code
    assert kb.window_taken()
    assert log_has(kb, "terminal key 1: not swallowed, Stratagem Menu watched, Trigger Key rules apply")


def test_the_terminal_key_is_a_trigger_key_when_the_menu_is_watched_before_the_terminal():
    kb, _ = watching_an_open_menu(1, 2)
    watch = kb.down(USE, 0.9).start_terminal_watch
    show(kb, watch, INTERACT, 1.0)
    decision = kb.down(ONE, 1.1)
    assert not decision.enter_code and not decision.let_through
    assert decision.outcome == Outcome("call", "DDUR")  # Slot 1 is called, not a Code entered


def test_the_terminal_key_stays_held_back_while_a_code_is_being_entered():
    # Reading and typing take a moment, and the tool ignores its own keys meanwhile; a second press in
    # that time must not slip through to the game as a weapon switch, nor start a second Code.
    kb, _ = terminal_waiting(INTERACT)
    assert kb.down(ONE, 1.1).enter_code
    kb.up(ONE, 1.15)
    kb.sending = kb.entering_code = True
    again = kb.down(ONE, 1.4)
    assert not again.let_through and not again.enter_code
    assert log_has(kb, "terminal key 1: swallowed, a Code is being entered")
    assert not kb.up(ONE, 1.45).let_through  # its release is held back too
    kb.sending = kb.entering_code = False
    assert kb.down(ONE, 3.0).enter_code  # and once the Code is in, the next press enters a Code again


def test_the_terminal_key_is_back_once_the_stratagem_menu_watch_is_over():
    kb, _ = terminal_waiting(INTERACT)
    kb.down(CALL, 1.1)
    kb.router.close_window()
    decision = kb.down(ONE, 3.0)
    assert not decision.let_through and decision.enter_code


def test_the_watch_ends_a_second_after_the_prompt_goes_and_the_terminal_key_is_ordinary_again():
    kb, watch = terminal_waiting(INTERACT)
    at = 1.0
    while kb.router.terminal_is_current(watch) and at < 4:
        at += 0.1
        show(kb, watch, NONE, at)
    assert 1.0 + GONE_FOR - 0.2 <= at <= 1.0 + GONE_FOR + 0.2
    assert log_has(kb, "Terminal watch ended: Terminal Prompt gone")
    assert kb.down(ONE, at + 0.1).let_through


def test_the_watch_gives_up_after_5_seconds_with_no_prompt():
    kb = Keyboard()
    watch = kb.down(USE, 0.0).start_terminal_watch
    at = 0.0
    while kb.router.terminal_is_current(watch) and at < 8:
        at += 0.1
        show(kb, watch, NONE, at)
    assert 4.9 <= at <= 5.2
    assert log_has(kb, "Terminal watch ended: gave up, no Terminal Prompt within 5 s")


def test_the_watch_ends_when_the_game_loses_focus():
    kb, watch = terminal_waiting(INTERACT)
    kb.focused = "Notepad"
    show(kb, watch, INTERACT, 1.5)
    assert not kb.router.terminal_is_current(watch)
    assert log_has(kb, "Terminal watch ended: game window lost focus")
    kb.focused = TITLE
    assert kb.down(ONE, 2.0).let_through  # coming back to the game, nothing is held over


def test_the_terminal_key_goes_to_the_game_when_the_game_is_not_focused():
    kb, _ = terminal_waiting(INTERACT)
    kb.focused = "Notepad"
    assert kb.down(ONE, 1.5).let_through


def test_pausing_ends_the_watch():
    kb, watch = terminal_waiting(INTERACT)
    kb.router.paused = True
    kb.router.end_terminal_watch("paused")
    assert not kb.router.terminal_is_current(watch)
    assert log_has(kb, "Terminal watch ended: paused")
    kb.router.paused = False
    assert kb.down(ONE, 2.0).let_through


def test_ending_a_watch_that_is_not_the_current_one_changes_nothing():
    kb, old = terminal_waiting(INTERACT)
    kb.router.end_terminal_watch("test")
    new = kb.down(USE, 3.0).start_terminal_watch
    kb.router.end_terminal_watch("reading stopped", only=old)  # the old worker's clean-up
    assert kb.router.terminal_is_current(new)


def test_readings_offered_by_a_replaced_watch_are_ignored():
    kb, old = terminal_waiting(INTERACT)
    kb.router.end_terminal_watch("test")
    show(kb, old, INTERACT, 2.0)
    assert not kb.router.terminal_is_current(old)
    assert kb.down(ONE, 2.1).let_through


def test_a_second_use_key_press_while_the_prompt_shows_keeps_the_terminal_key_held():
    kb, _ = terminal_waiting(INTERACT)
    kb.down(USE, 2.0)
    assert not kb.down(ONE, 2.05).let_through


def test_the_mark_describes_the_terminal_watch():
    kb, _ = terminal_waiting(INTERACT)
    assert "Terminal watch running, Terminal Prompt reads INTERACT" in kb.router.describe()
    kb.router.end_terminal_watch("test")
    assert "Terminal watch" not in kb.router.describe()


def test_no_key_cap_or_flash_comes_from_the_terminal_key():
    kb, _ = terminal_waiting(INTERACT)
    kb.down(ONE, 1.2)
    assert kb.router.key_caps() == {} and kb.router.red_key_caps() == frozenset()
