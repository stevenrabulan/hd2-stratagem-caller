"""The Terminal watch: how long the tool keeps reading the Terminal Prompt after a Use Key press.

Like the Arming Window it holds no keyboard, screen or clock: it is driven by readings and the
times they were taken.
"""

from .terminal_prompt import TerminalPrompt

# The Use Key is also used for samples, ammo and pods, so a press that brings no Terminal Prompt
# is given up after this long (it covers the walk-up animation, and the Code's own 1 s delay).
GIVE_UP_AFTER = 5.0
# Once a Terminal Prompt has shown, the watch ends this long after none shows. A step's prompt can
# fade before the next step's appears, and a later step must work without another Use Key press.
GONE_FOR = 1.0
# A watch that has run this long since the last Use Key press is given up, so a misread prompt
# cannot keep the tool reading the screen for a whole session. A long Terminal (nine steps) takes
# well under this.
SAFETY_LIMIT = 120.0
# Seconds between readings of the Terminal Prompt.
READING_INTERVAL = 0.1


class TerminalWatch:
    def __init__(self, started: float):
        self.prompt = TerminalPrompt.NONE  # the latest reading
        self._shown_at: float | None = None  # when a Terminal Prompt was last read, since the press
        self.restart(started)

    def restart(self, now: float) -> None:
        """The Use Key was pressed again: the 5 s and the safety limit count from now. What is on
        screen is not forgotten, the next reading says whether it still is."""
        self._started = now
        self._shown_at = None

    def offer(self, prompt: TerminalPrompt, now: float) -> str | None:
        """Feed a reading. Returns why the watch is over, or None while it goes on."""
        self.prompt = prompt
        if prompt is not TerminalPrompt.NONE:
            self._shown_at = now
        if now - self._started >= SAFETY_LIMIT:
            return "safety limit reached"
        if self._shown_at is None:
            if now - self._started >= GIVE_UP_AFTER:
                return f"gave up, no Terminal Prompt within {GIVE_UP_AFTER:g} s of the Use Key press"
        elif prompt is TerminalPrompt.NONE and now - self._shown_at >= GONE_FOR:
            return "Terminal Prompt gone"
        return None
