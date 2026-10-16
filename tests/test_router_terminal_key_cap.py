"""When the Terminal Key's Key Cap shows, and when it flashes, from scripted readings."""

import pytest
from test_router import CALL, ONE, RETURN, TITLE, USE
from test_router_terminal import INTERACT, MOVE, NONE, log_has, show, terminal_waiting

from stratagem_caller.keycaps import TerminalKeyCap
from stratagem_caller.router import TERMINAL_CAP_OFF, TERMINAL_CAP_ON
from stratagem_caller.terminal_code import CodeReading, CodeStatus
from stratagem_caller.terminal_watch import CODE_HOLD

CODE = CodeReading(CodeStatus.READ, "LURRDR", 2, why="6 arrows")
NOTHING_ENTERED = CodeReading(CodeStatus.READ, "LURRDR", 0, why="6 arrows")
ALL_ENTERED = CodeReading(CodeStatus.READ, "LURRDR", 6, why="6 arrows")
UNREADABLE = CodeReading(CodeStatus.UNREADABLE, why="the arrows are unevenly spaced, one may be hidden")
NO_CODE = CodeReading(CodeStatus.NONE, why="no row of arrows")


def read(kb, watch, reading, at):
    kb.now = at
    kb.router.offer_terminal_code(watch, reading)


def key_cap(kb):
    return kb.router.terminal_key_cap()


def test_there_is_no_key_cap_until_a_code_is_read():
    kb, _ = terminal_waiting(INTERACT)
    assert key_cap(kb) is None


def test_the_key_cap_shows_the_terminal_keys_name_while_a_code_is_read():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    assert key_cap(kb) == TerminalKeyCap("1")


def test_the_key_cap_shows_whichever_key_is_the_terminal_key():
    kb, watch = terminal_waiting(INTERACT, terminal_key=RETURN)
    read(kb, watch, CODE, 1.1)
    assert key_cap(kb) == TerminalKeyCap("enter")


def test_a_code_with_nothing_entered_gets_a_key_cap_too():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, NOTHING_ENTERED, 1.1)
    assert key_cap(kb) == TerminalKeyCap("1")


@pytest.mark.parametrize("reading", [UNREADABLE, NO_CODE], ids=["unreadable", "none"])
def test_no_key_cap_while_the_code_cannot_be_read_or_is_not_there(reading):
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, reading, 1.1)
    assert key_cap(kb) is None


def test_the_key_cap_goes_when_the_code_is_entered():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    read(kb, watch, ALL_ENTERED, 1.4)  # the Code is whole and yellow, fading
    assert key_cap(kb) is None


def test_the_key_cap_stays_through_a_moment_the_code_cannot_be_read():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    read(kb, watch, UNREADABLE, 1.35)  # a hand over an arrow for a reading or two
    read(kb, watch, NO_CODE, 1.6)
    assert key_cap(kb) == TerminalKeyCap("1")


def test_the_key_cap_goes_when_the_code_stays_unreadable_and_returns_when_it_can_be_read_again():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    read(kb, watch, UNREADABLE, 1.1 + CODE_HOLD)
    assert key_cap(kb) is None
    read(kb, watch, CODE, 2.1)
    assert key_cap(kb) == TerminalKeyCap("1")


def test_the_key_cap_blinks_off_for_a_quarter_as_long_as_it_shows():
    assert TERMINAL_CAP_OFF == pytest.approx(TERMINAL_CAP_ON / 4)
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.0)  # the blink counts from the first reading of the Code
    period = TERMINAL_CAP_ON + TERMINAL_CAP_OFF
    for start in (1.0, 1.0 + period):
        for at, shown in [(0.0, True), (TERMINAL_CAP_ON - 0.01, True), (TERMINAL_CAP_ON + 0.01, False), (period - 0.01, False)]:
            kb.now = start + at
            read(kb, watch, CODE, kb.now)  # fresh readings do not restart the blink
            assert (key_cap(kb) is not None) == shown, (start, at)


def test_the_blink_starts_afresh_for_a_code_read_again_after_it_went():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.0)
    read(kb, watch, ALL_ENTERED, 1.25)
    read(kb, watch, CODE, 1.0 + TERMINAL_CAP_ON + 0.05)  # would be in the off part of the first blink
    assert key_cap(kb) == TerminalKeyCap("1")


def test_the_red_steps_of_a_flash_show_even_in_the_off_part_of_the_blink():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.0)
    kb.now = 1.0 + TERMINAL_CAP_ON + 0.01
    flash(kb)
    assert key_cap(kb) == TerminalKeyCap("1", red=True)


@pytest.mark.parametrize("prompt", [NONE, MOVE], ids=["no prompt", "move cursor"])
def test_the_key_cap_goes_with_the_terminal_prompt(prompt):
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    show(kb, watch, prompt, 1.2)
    assert key_cap(kb) is None


def test_a_code_read_before_the_prompt_went_does_not_come_back_with_the_next_prompt():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    show(kb, watch, MOVE, 1.2)
    show(kb, watch, INTERACT, 1.3)  # the next step's prompt: its Code has not been read yet
    assert key_cap(kb) is None


def test_a_code_offered_while_the_prompt_is_not_interact_is_not_shown():
    kb, watch = terminal_waiting(INTERACT)
    show(kb, watch, MOVE, 1.1)
    read(kb, watch, CODE, 1.15)  # a reading begun before the prompt changed
    assert key_cap(kb) is None


def test_the_key_cap_goes_when_the_watch_ends():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    kb.router.end_terminal_watch("test")
    assert key_cap(kb) is None


def test_a_reading_for_a_replaced_watch_shows_nothing():
    kb, old = terminal_waiting(INTERACT)
    kb.router.end_terminal_watch("test")
    new = kb.down(USE, 3.0).start_terminal_watch
    show(kb, new, INTERACT, 3.1)
    read(kb, old, CODE, 3.2)
    assert key_cap(kb) is None


def test_the_key_cap_goes_at_once_when_the_game_loses_focus_and_returns_with_it():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    kb.focused = "Notepad"
    assert key_cap(kb) is None  # before the watch has had a reading to notice
    kb.focused = TITLE
    assert key_cap(kb) == TerminalKeyCap("1")


def test_the_key_cap_goes_at_once_when_the_tool_is_paused():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    kb.router.paused = True
    assert key_cap(kb) is None


def test_the_key_cap_is_not_shown_while_the_stratagem_menu_is_watched():
    # There the Terminal Key is a Trigger Key, so a Key Cap saying ENTER CODE would be a lie.
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    kb.down(CALL, 1.2)
    assert key_cap(kb) is None
    kb.router.close_window()
    assert key_cap(kb) == TerminalKeyCap("1")


def test_the_key_cap_goes_when_the_terminal_key_is_pressed_and_waits_for_a_fresh_reading():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    assert kb.down(ONE, 1.2).enter_code
    assert key_cap(kb) is None  # the Code is being typed; what was read is out of date
    kb.up(ONE, 1.25)
    assert key_cap(kb) is None
    read(kb, watch, CODE, 1.6)  # still not all in: the next reading brings it back
    assert key_cap(kb) == TerminalKeyCap("1")


def test_no_key_cap_while_a_code_is_being_entered_and_readings_taken_then_are_dropped():
    kb, watch = terminal_waiting(INTERACT)
    kb.entering_code = True
    read(kb, watch, CODE, 1.1)  # taken a moment before the key was pressed
    assert key_cap(kb) is None
    kb.entering_code = False
    assert key_cap(kb) is None  # and not remembered afterwards either


# --- the flash ---


def flash(kb):
    kb.router.flash_terminal_key()


def test_the_terminal_key_cap_flashes_red_twice_in_step_with_the_beep():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.0)
    flash(kb)  # at 1.0
    shown = []
    for step in range(5):  # red, normal, red, normal, then nothing more
        kb.now = 1.0 + step * 0.15 + 0.07
        shown.append(key_cap(kb))
    assert shown == [
        TerminalKeyCap("1", red=True),
        TerminalKeyCap("1"),
        TerminalKeyCap("1", red=True),
        TerminalKeyCap("1"),
        TerminalKeyCap("1"),
    ]


def test_a_flash_with_no_code_read_shows_the_key_cap_only_in_its_red_steps():
    # The Code could not be read, so there is no Key Cap to turn red: the flash itself shows it.
    kb, _ = terminal_waiting(INTERACT)
    flash(kb)
    shown = []
    for step in range(5):
        kb.now = 1.0 + step * 0.15 + 0.07
        shown.append(key_cap(kb))
    assert shown == [TerminalKeyCap("1", red=True), None, TerminalKeyCap("1", red=True), None, None]


def test_a_flash_is_red_while_the_code_is_being_entered_flag_is_still_up():
    kb, _ = terminal_waiting(INTERACT)
    kb.entering_code = True  # the press that beeps is still marked as entering when it flashes
    flash(kb)
    assert key_cap(kb) == TerminalKeyCap("1", red=True)


def test_the_flash_restarts_when_the_terminal_key_beeps_again():
    kb, _ = terminal_waiting(INTERACT)
    flash(kb)
    kb.now = 1.2  # a normal step of the first flash
    assert key_cap(kb) is None
    flash(kb)
    assert key_cap(kb) == TerminalKeyCap("1", red=True)


@pytest.mark.parametrize("why", ["paused", "not focused", "no prompt", "menu watched"])
def test_a_flash_is_not_shown_when_the_key_cap_would_not_be(why):
    kb, watch = terminal_waiting(INTERACT)
    flash(kb)
    kb.now = 1.05
    if why == "paused":
        kb.router.paused = True
    elif why == "not focused":
        kb.focused = "Notepad"
    elif why == "no prompt":
        show(kb, watch, NONE, 1.05)
    else:
        kb.down(CALL, 1.05)
    assert key_cap(kb) is None


def test_a_flash_over_leaves_nothing_behind():
    kb, _ = terminal_waiting(INTERACT)
    flash(kb)
    kb.now = 5.0
    assert key_cap(kb) is None


def test_the_slot_key_caps_and_flashes_are_not_touched_by_the_terminal_key_cap():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    flash(kb)
    assert kb.router.key_caps() == {} and kb.router.red_key_caps() == frozenset()


# --- the log ---


def test_the_log_says_when_the_key_cap_appears_and_goes_and_why():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    assert log_has(kb, "Terminal Key Cap shown: Code LURRDR, 2 entered")
    read(kb, watch, CODE, 1.4)
    assert sum("Terminal Key Cap shown" in line for line in kb.lines) == 1  # only changes are logged
    read(kb, watch, ALL_ENTERED, 1.7)
    assert log_has(kb, "Terminal Key Cap hidden: Code LURRDR, all entered")
    read(kb, watch, UNREADABLE, 2.0)
    read(kb, watch, CODE, 2.3)
    read(kb, watch, UNREADABLE, 2.3 + CODE_HOLD)
    assert log_has(kb, "Terminal Key Cap hidden: a Code that cannot be read, the arrows are unevenly spaced")


def test_the_log_says_when_the_prompt_takes_the_key_cap_away():
    kb, watch = terminal_waiting(INTERACT)
    read(kb, watch, CODE, 1.1)
    show(kb, watch, NONE, 1.2)
    assert log_has(kb, "Terminal Key Cap hidden: no Terminal Prompt")
