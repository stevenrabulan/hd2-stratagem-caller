import pytest

from stratagem_caller.terminal_code import CodeReading, CodeStatus
from stratagem_caller.terminal_prompt import TerminalPrompt
from stratagem_caller.terminal_watch import CODE_HOLD, GIVE_UP_AFTER, GONE_FOR, SAFETY_LIMIT, TerminalWatch

NONE = TerminalPrompt.NONE
INTERACT = TerminalPrompt.INTERACT
MOVE = TerminalPrompt.MOVE_CURSOR


def feed(watch, readings):
    """Offer (time, prompt) readings in order; the first reason the watch ends for, or None."""
    for at, prompt in readings:
        reason = watch.offer(prompt, at)
        if reason is not None:
            return at, reason
    return None


def every(start, stop, prompt, step=0.1):
    """Readings of one prompt from `start` up to (not including) `stop`."""
    count = round((stop - start) / step)
    return [(start + i * step, prompt) for i in range(count)]


def test_gives_up_when_no_terminal_prompt_appears_within_5_seconds_of_the_press():
    watch = TerminalWatch(started=10.0)
    ended = feed(watch, every(10.0, 20.0, NONE))
    assert ended is not None
    at, reason = ended
    assert 14.9 < at <= 15.1  # 5 s after the press
    assert "5 s" in reason


def test_does_not_give_up_before_5_seconds():
    watch = TerminalWatch(started=0.0)
    assert feed(watch, every(0.0, GIVE_UP_AFTER - 0.05, NONE)) is None


def test_a_prompt_seen_late_in_the_5_seconds_keeps_the_watch():
    watch = TerminalWatch(started=0.0)
    readings = every(0.0, 4.5, NONE) + every(4.5, 30.0, INTERACT)
    assert feed(watch, readings) is None


def test_lasts_while_any_terminal_prompt_shows_whichever_it_reads():
    watch = TerminalWatch(started=0.0)
    readings = every(1.0, 20.0, INTERACT) + every(20.0, 40.0, MOVE) + every(40.0, 60.0, INTERACT)
    assert feed(watch, readings) is None


def test_ends_about_one_second_after_the_prompt_goes():
    watch = TerminalWatch(started=0.0)
    assert feed(watch, every(1.0, 8.0, INTERACT)) is None
    ended = feed(watch, every(8.0, 12.0, NONE))
    assert ended is not None
    at, reason = ended
    assert 8.0 + GONE_FOR - 0.15 <= at <= 8.0 + GONE_FOR + 0.15  # the first reading with none was at 8.0
    assert "Terminal Prompt" in reason


def test_a_prompt_that_comes_back_within_the_second_keeps_the_watch():
    # The prompt fades between steps of one Terminal: INTERACT, a gap, then MOVE CURSOR.
    watch = TerminalWatch(started=0.0)
    readings = every(1.0, 5.0, INTERACT) + every(5.0, 5.8, NONE) + every(5.8, 9.0, MOVE)
    assert feed(watch, readings) is None


def test_two_short_gaps_do_not_add_up():
    watch = TerminalWatch(started=0.0)
    readings = (
        every(1.0, 5.0, INTERACT)
        + every(5.0, 5.7, NONE)
        + every(5.7, 6.0, INTERACT)
        + every(6.0, 6.7, NONE)
        + every(6.7, 8.0, INTERACT)
    )
    assert feed(watch, readings) is None


def test_ends_at_the_safety_limit_while_a_prompt_still_shows():
    watch = TerminalWatch(started=0.0)
    ended = feed(watch, every(1.0, SAFETY_LIMIT + 5, INTERACT, step=0.5))
    assert ended is not None
    at, reason = ended
    assert SAFETY_LIMIT <= at < SAFETY_LIMIT + 1
    assert "safety limit" in reason


def test_another_use_key_press_starts_the_5_seconds_and_the_limit_again():
    watch = TerminalWatch(started=0.0)
    assert feed(watch, every(0.0, 4.0, NONE)) is None
    watch.restart(4.0)
    assert feed(watch, every(4.0, 8.9, NONE)) is None  # 5 s from the second press, not the first
    assert feed(watch, every(8.9, 10.0, NONE)) is not None


def test_a_restart_while_a_prompt_shows_keeps_it_showing_until_the_next_reading():
    watch = TerminalWatch(started=0.0)
    watch.offer(INTERACT, 3.0)
    watch.restart(3.5)
    assert watch.prompt is INTERACT  # still on screen; the press did not remove it


def test_the_latest_reading_is_the_prompt():
    watch = TerminalWatch(started=0.0)
    assert watch.prompt is NONE  # nothing read yet
    watch.offer(INTERACT, 1.0)
    assert watch.prompt is INTERACT
    watch.offer(MOVE, 1.1)
    assert watch.prompt is MOVE
    watch.offer(NONE, 1.2)
    assert watch.prompt is NONE


def test_gone_for_is_about_a_second():
    assert 0.8 <= GONE_FOR <= 1.2
    assert GIVE_UP_AFTER == 5.0


# --- the Code read while the prompt reads INTERACT ---

CODE = CodeReading(CodeStatus.READ, "LURRDR", 2, why="6 arrows")


def test_a_code_reading_is_kept_while_the_prompt_reads_interact():
    watch = TerminalWatch(started=0.0)
    assert watch.code is None
    watch.offer(INTERACT, 1.0)
    watch.offer_code(CODE, 1.0)
    assert watch.code is CODE
    watch.offer(INTERACT, 1.1)
    assert watch.code is CODE  # the next reading of the prompt does not forget it


@pytest.mark.parametrize("prompt", [NONE, MOVE])
def test_the_code_goes_when_the_prompt_stops_reading_interact(prompt):
    watch = TerminalWatch(started=0.0)
    watch.offer(INTERACT, 1.0)
    watch.offer_code(CODE, 1.0)
    watch.offer(prompt, 1.1)
    assert watch.code is None
    watch.offer(INTERACT, 1.2)
    assert watch.code is None  # the next step's Code has to be read afresh


@pytest.mark.parametrize("prompt", [NONE, MOVE])
def test_a_code_reading_that_arrives_after_the_prompt_changed_is_dropped(prompt):
    watch = TerminalWatch(started=0.0)
    watch.offer(prompt, 1.0)
    watch.offer_code(CODE, 1.0)
    assert watch.code is None


UNREADABLE = CodeReading(CodeStatus.UNREADABLE, why="a hand over an arrow")
NO_CODE = CodeReading(CodeStatus.NONE, why="no row of arrows")
ALL_ENTERED = CodeReading(CodeStatus.READ, "LURRDR", 6, why="6 arrows")


@pytest.mark.parametrize("dropout", [UNREADABLE, NO_CODE], ids=["unreadable", "none"])
def test_a_code_is_held_through_readings_that_cannot_see_it_for_a_moment(dropout):
    watch = TerminalWatch(started=0.0)
    watch.offer(INTERACT, 1.0)
    watch.offer_code(CODE, 1.0)
    watch.offer_code(dropout, 1.0 + CODE_HOLD - 0.05)
    assert watch.code is CODE
    watch.offer_code(dropout, 1.0 + CODE_HOLD)
    assert watch.code is dropout  # held no longer


def test_each_fresh_reading_of_the_code_starts_the_hold_again():
    watch = TerminalWatch(started=0.0)
    watch.offer(INTERACT, 1.0)
    watch.offer_code(CODE, 1.0)
    watch.offer_code(UNREADABLE, 1.25)
    watch.offer_code(CODE, 1.5)
    watch.offer_code(UNREADABLE, 1.5 + CODE_HOLD - 0.05)
    assert watch.code is CODE


def test_a_code_read_all_entered_is_not_held_off():
    watch = TerminalWatch(started=0.0)
    watch.offer(INTERACT, 1.0)
    watch.offer_code(CODE, 1.0)
    watch.offer_code(ALL_ENTERED, 1.25)
    assert watch.code is ALL_ENTERED


def test_code_waits_since_marks_when_a_code_began_to_wait_and_clears_when_it_stops():
    watch = TerminalWatch(started=0.0)
    watch.offer(INTERACT, 1.0)
    watch.offer_code(CODE, 1.0)
    watch.offer_code(CODE, 1.25)
    assert watch.code_waits_since == 1.0
    watch.offer_code(ALL_ENTERED, 1.5)
    assert watch.code_waits_since is None
    watch.offer_code(CODE, 1.75)
    assert watch.code_waits_since == 1.75
    watch.offer(MOVE, 2.0)
    assert watch.code_waits_since is None


def test_the_hold_is_three_code_readings():
    assert CODE_HOLD == 0.75
