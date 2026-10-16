"""What the tool says when it starts, when an error ends it, and when it is already running,
with or without a console.

Started from a terminal, startup lines are printed as they always were. Started from the desktop
shortcut there is no console (pythonw.exe), so those lines go to the event log instead. Warnings
and the "stopped" notice are Windows notifications either way, shown by the Tray Icon, and
are also written to the log.
"""

import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path

from .reader import REFERENCE_HEIGHT
from .settings import Settings

STOPPED_NOTICE = "Stratagem Caller stopped: see log"
ALREADY_RUNNING_NOTICE = "Stratagem Caller is already running"
# How long a closing notice stays up before the Tray Icon is removed (removing the icon can
# take its notification with it).
STOPPED_NOTICE_SECONDS = 5.0


def has_console() -> bool:
    """False under pythonw.exe, which leaves sys.stdout as None."""
    return sys.stdout is not None


class Reporter:
    def __init__(self, *, console: bool, log: Callable[[str], None], out: Callable[[str], None] = print):
        """Startup lines are printed with a `console` and logged without one. `notify` shows a
        Windows notification; it does nothing until the Tray Icon exists and sets it."""
        self._console = console
        self._log = log
        self._out = out
        self.notify: Callable[[str], None] = lambda text: None

    def line(self, text: str) -> None:
        if self._console:
            self._out(text)
        else:
            self._log(text.strip())

    def warning(self, text: str, notify: bool = True) -> None:
        """Always logged; printed with a console; a notification unless `notify` is false (the
        caller will put it in a notification of its own)."""
        self._log(f"Warning: {text}")
        if self._console:
            self._out(f"  Warning: {text}")
        if notify:
            self.notify_safely(f"Warning: {text}")

    def notify_safely(self, text: str) -> None:
        """Losing a notification must not lose the keyboard: say so in the log and carry on."""
        try:
            self.notify(text)
        except Exception as error:
            self._log(f"Notification failed ({text!r}): {error!r}")


def started_message(settings: Settings, warnings: list[str]) -> str:
    """The notification shown at start: that it is running, naming the Call Key, then any
    startup warnings (one notification, so a warning doesn't replace the news that it started)."""
    return "\n".join([f"Running. Call Key: {settings.call_key.upper()}", *(f"Warning: {w}" for w in warnings)])


def describe_startup(report: Reporter, settings: Settings, height: int, log_path: Path) -> list[str]:
    """Say what the tool is set up to do. Returns the warnings, which are logged (and printed)
    but not yet notified."""
    warnings = []
    report.line(f"Stratagem Caller running. Screen height {height}.")
    if height != REFERENCE_HEIGHT:
        warnings.append(f"only tested at {REFERENCE_HEIGHT}; Trigger Keys may not read the menu.")
        report.warning(warnings[-1], notify=False)
    report.line(f"  Call Key [{settings.call_key}] then {', '.join(settings.trigger_keys)} for Slots")
    report.line(f"  Use Key [{settings.use_key}] at a Terminal, then Terminal Key [{settings.terminal_key}] (beeps for now: the Code is not read yet)")
    for key, code in settings.direct_keys.items():
        report.line(f"  Direct Key [{key}] -> {code}")
    report.line(f"  [{settings.pause_key}] pause/resume, [{settings.mark_key}] mark something unexpected, Ctrl+C here to quit")
    report.line(f"  Logging Trigger Keys and Calls to {log_path}")
    report.line(f"  Overlay (Key Caps beside each Slot and a ready heading while the menu is open): {'on' if settings.overlay_enabled else 'off'}")
    return warnings


def end_with_error(
    error: BaseException,
    *,
    log: Callable[[str], None],
    tray,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """An unexpected error ended the tool: the full traceback goes to the log, the stopped notice
    is shown, and the Tray Icon is removed. The caller has already given the keyboard back."""
    log("Stopped by an unexpected error:\n" + "".join(traceback.format_exception(error)).rstrip())
    _show_closing_notice(STOPPED_NOTICE, tray=tray, log=log, sleep=sleep)


def refuse_second_launch(
    *,
    tray,
    beep: Callable[[], None],
    log: Callable[[str], None],
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Another copy of the tool holds the keyboard: say so, beep once, and remove the Tray Icon
    (a bare one, just to carry the notice). The caller exits without hooking anything."""
    log(f"{ALREADY_RUNNING_NOTICE}: this launch exits")
    _show_closing_notice(ALREADY_RUNNING_NOTICE, tray=tray, log=log, sleep=sleep, also=beep)


def _show_closing_notice(notice: str, *, tray, log, sleep, also: Callable[[], None] | None = None) -> None:
    """Show `notice`, do `also` (a beep), give the notice time to be read, then remove the Tray
    Icon. The icon goes whatever fails on the way."""
    try:
        try:
            tray.notify(notice)
        except Exception as error:
            log(f"Notification failed ({notice!r}): {error!r}")
            shown = False
        else:
            shown = True
        if also is not None:
            try:
                also()
            except Exception as error:
                log(f"Sound failed ({notice!r}): {error!r}")
        if shown:
            sleep(STOPPED_NOTICE_SECONDS)
    finally:
        tray.stop()


def log_thread_failure(log: Callable[[str], None]) -> Callable:
    """A `threading.excepthook` that writes a worker thread's traceback to the log; with no
    console it would otherwise be lost."""

    def hook(args) -> None:
        trace = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)).rstrip()
        log(f"Thread {args.thread.name} failed:\n{trace}")

    return hook
