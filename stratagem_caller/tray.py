"""The Tray Icon: the tool's icon in the Windows notification area while it runs.

It shows the Key Cap (greyed while paused), says Running or Paused in its tooltip, and has a
menu that pauses or resumes, opens the log, and quits. It decides nothing itself: what a menu
item does is handed in, and the pause state is asked for, so the hotkey and the menu share one
pause toggle and the icon follows either (the toggle calls `refresh`). It also shows Windows
notifications, which only work once the icon is in the notification area. pystray is reached
through a backend the caller may replace, so tests never put a real icon on the screen.
"""

import threading
from collections.abc import Callable
from pathlib import Path

from PIL import Image

ICON_PATH = Path(__file__).resolve().parent / "assets" / "stratagem_caller.ico"
NAME = "Stratagem Caller"
TRAY_SIZE = 64
# How bright a greyed icon is, against the grey of the same picture: dimmer reads as "off".
GREY_LEVEL = 0.6
# How long a notification waits for the icon to appear in the notification area (normally a few ms).
SHOWN_WITHIN = 3.0


def load_icon(path: Path = ICON_PATH, size: int = TRAY_SIZE) -> Image.Image:
    """The Key Cap icon file as a `size` pixel square RGBA picture."""
    with Image.open(path) as opened:
        opened.size = max(opened.info["sizes"])  # the largest picture in the file
        picture = opened.convert("RGBA")
    return picture.resize((size, size), Image.LANCZOS)


def greyed(image: Image.Image) -> Image.Image:
    """The same picture without colour, dimmed, with its shape (alpha) kept."""
    rgba = image.convert("RGBA")
    level = rgba.convert("L").point(lambda v: round(v * GREY_LEVEL))
    return Image.merge("RGBA", (level, level, level, rgba.getchannel("A")))


def _real_backend():
    """pystray itself. Imported only when a real icon is wanted."""
    import pystray

    return pystray


class TrayIcon:
    def __init__(
        self,
        *,
        paused: Callable[[], bool],
        toggle_pause: Callable[[], None],
        open_log: Callable[[], None],
        quit: Callable[[], None],
        running_image: Image.Image,
        paused_image: Image.Image,
        backend=None,
    ):
        """`paused` says whether the tool is paused now. The menu items call `toggle_pause`,
        `open_log` and `quit`. `backend` has pystray's `Icon`, `Menu` and `MenuItem`."""
        self._paused = paused
        self._toggle_pause = toggle_pause
        self._open_log = open_log
        self._quit = quit
        self._running_image = running_image
        self._paused_image = paused_image
        self._backend = backend if backend is not None else _real_backend()
        self._icon = None
        self._shown = threading.Event()

    def start(self) -> None:
        """Put the icon in the notification area; its loop runs on its own thread."""
        assert self._icon is None, "the Tray Icon is already started"
        self._icon = self._backend.Icon(NAME, icon=self._image(), title=self._title(), menu=self._menu())
        self._icon.run_detached(self._show)

    def notify(self, message: str, shown_within: float = SHOWN_WITHIN) -> None:
        """Show a Windows notification. Waits for the icon to appear first, since pystray cannot
        notify from an icon that is not shown yet. Raises if it never appears."""
        icon = self._icon
        assert icon is not None, f"the Tray Icon is not started, so it cannot show: {message!r}"
        if not self._shown.wait(shown_within):
            raise RuntimeError(f"the Tray Icon did not appear within {shown_within} s, so it cannot show: {message!r}")
        icon.notify(message, NAME)

    def refresh(self) -> None:
        """Bring the picture, the tooltip and the menu label in line with the pause state."""
        icon = self._icon
        if icon is None:
            return
        icon.icon = self._image()
        icon.title = self._title()
        icon.update_menu()

    def stop(self) -> None:
        """Remove the icon. Safe to call again, or before `start`."""
        icon, self._icon = self._icon, None
        if icon is not None:
            icon.stop()

    def _show(self, icon) -> None:
        """Runs on the icon's own thread once its loop has started."""
        icon.visible = True
        self._shown.set()

    def _image(self) -> Image.Image:
        return self._paused_image if self._paused() else self._running_image

    def _title(self) -> str:
        return f"{NAME}: {'Paused' if self._paused() else 'Running'}"

    def _menu(self):
        item = self._backend.MenuItem
        return self._backend.Menu(
            item(lambda _item: "Resume" if self._paused() else "Pause", lambda _icon, _item: self._toggle_pause()),
            item("Open log", lambda _icon, _item: self._open_log()),
            item("Quit", lambda _icon, _item: self._quit()),
        )
