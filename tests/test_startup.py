import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from stratagem_caller.settings import load
from stratagem_caller.startup import (
    STOPPED_NOTICE,
    Reporter,
    describe_startup,
    end_with_error,
    has_console,
    log_thread_failure,
    started_message,
)

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = load(ROOT / "settings.toml", ROOT / "codebook.toml")


class Recorder:
    """What a Reporter did: what reached the terminal, the event log and the notifications."""

    def __init__(self, console: bool):
        self.printed, self.logged, self.notified = [], [], []
        self.reporter = Reporter(console=console, log=self.logged.append, out=self.printed.append)
        self.reporter.notify = self.notified.append


# --- where startup lines go ---


def test_with_a_console_a_startup_line_is_printed_and_not_logged():
    run = Recorder(console=True)
    run.reporter.line("  Direct Key [page down] -> Reinforce")
    assert run.printed == ["  Direct Key [page down] -> Reinforce"] and run.logged == []


def test_without_a_console_a_startup_line_goes_to_the_log_only():
    run = Recorder(console=False)
    run.reporter.line("  Direct Key [page down] -> Reinforce")
    assert run.printed == [] and run.logged == ["Direct Key [page down] -> Reinforce"]


@pytest.mark.parametrize("console", [True, False])
def test_a_warning_is_in_the_log_and_a_notification_whether_or_not_there_is_a_console(console):
    run = Recorder(console)
    run.reporter.warning("the Overlay stopped; Trigger Keys still work.")
    assert run.logged == ["Warning: the Overlay stopped; Trigger Keys still work."]
    assert run.notified == ["Warning: the Overlay stopped; Trigger Keys still work."]
    assert run.printed == (["  Warning: the Overlay stopped; Trigger Keys still work."] if console else [])


def test_a_warning_that_cannot_be_notified_is_still_logged_with_why():
    run = Recorder(console=False)

    def broken(text):
        raise RuntimeError("no tray")

    run.reporter.notify = broken
    run.reporter.warning("something")
    assert run.logged[0] == "Warning: something"
    assert "Notification failed" in run.logged[1] and "no tray" in run.logged[1]


def test_a_warning_can_be_held_back_from_notifying_so_the_caller_can_batch_it():
    run = Recorder(console=False)
    run.reporter.warning("batched", notify=False)
    assert run.notified == [] and run.logged == ["Warning: batched"]


def test_python_exe_has_a_console_and_pythonw_exe_does_not(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)  # what pythonw.exe leaves
    assert not has_console()
    monkeypatch.setattr(sys, "stdout", SimpleNamespace())
    assert has_console()


# --- what startup says ---


def test_the_started_message_names_the_call_key():
    assert started_message(SETTINGS, []) == "Running. Call Key: B"


def test_the_started_message_carries_the_startup_warnings():
    message = started_message(SETTINGS, ["only tested at 2160."])
    assert message.splitlines() == ["Running. Call Key: B", "Warning: only tested at 2160."]


def test_startup_says_what_it_says_today_for_the_tested_screen_height():
    run = Recorder(console=True)
    warnings = describe_startup(run.reporter, SETTINGS, 2160, Path("logs/x.log"))
    assert warnings == []
    assert run.printed[0] == "Stratagem Caller running. Screen height 2160."
    assert "  Call Key [b] then 1, 2, 3, 4, 5, 6, 7, 8, 9, 0 for Slots" in run.printed
    assert "  Direct Key [page down] -> UDRLU" in run.printed
    assert any("Overlay" in line and line.endswith("on") for line in run.printed)
    assert any("Ctrl+C here to quit" in line for line in run.printed)
    assert run.logged == [] and run.notified == []


def test_an_untested_screen_height_is_a_warning_handed_back_for_the_started_notification():
    run = Recorder(console=False)
    warnings = describe_startup(run.reporter, SETTINGS, 1440, Path("logs/x.log"))
    assert warnings == ["only tested at 2160; Trigger Keys may not read the menu."]
    assert "Warning: only tested at 2160; Trigger Keys may not read the menu." in run.logged
    assert run.notified == []  # the caller sends one notification for the lot
    assert run.printed == []


def test_without_a_console_the_other_startup_lines_are_in_the_log():
    run = Recorder(console=False)
    describe_startup(run.reporter, SETTINGS, 2160, Path("logs/x.log"))
    assert "Stratagem Caller running. Screen height 2160." in run.logged
    assert any("Direct Key [page down]" in line for line in run.logged)


# --- an unexpected error ---


class FakeTray:
    def __init__(self, events):
        self.events = events

    def notify(self, message):
        self.events.append(("notify", message))

    def stop(self):
        self.events.append(("stop",))


def broken_function_name_for_the_traceback():
    raise ValueError("screen 0 is not there")


def test_an_error_puts_the_traceback_in_the_log_shows_the_stopped_notice_then_removes_the_tray():
    events, lines = [], []
    try:
        broken_function_name_for_the_traceback()
    except ValueError as error:
        end_with_error(error, log=lines.append, tray=FakeTray(events), sleep=lambda seconds: events.append(("wait", seconds)))
    assert STOPPED_NOTICE == "Stratagem Caller stopped: see log"
    assert len(lines) == 1
    assert "broken_function_name_for_the_traceback" in lines[0] and "ValueError: screen 0 is not there" in lines[0]
    assert [event[0] for event in events] == ["notify", "wait", "stop"]  # the notice gets time to be read
    assert events[0] == ("notify", STOPPED_NOTICE)


def test_the_tray_is_removed_even_when_the_notice_cannot_be_shown():
    events, lines = [], []

    class NoNotice(FakeTray):
        def notify(self, message):
            raise RuntimeError("never appeared")

    try:
        broken_function_name_for_the_traceback()
    except ValueError as error:
        end_with_error(error, log=lines.append, tray=NoNotice(events), sleep=lambda seconds: None)
    assert events == [("stop",)]
    assert "Notification failed" in lines[1] and "never appeared" in lines[1]


def test_an_error_in_a_worker_thread_is_logged_in_full():
    lines = []
    hook = log_thread_failure(lines.append)
    try:
        broken_function_name_for_the_traceback()
    except ValueError as error:
        hook(SimpleNamespace(exc_type=type(error), exc_value=error, exc_traceback=error.__traceback__, thread=SimpleNamespace(name="Thread-7")))
    assert len(lines) == 1
    assert "Thread-7" in lines[0] and "broken_function_name_for_the_traceback" in lines[0] and "screen 0 is not there" in lines[0]
