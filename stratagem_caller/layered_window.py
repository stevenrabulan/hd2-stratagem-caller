"""Windows glue for the Overlay: a click-through, always-on-top window that never takes focus.

The window shows a premultiplied BGRA picture with per-pixel transparency
(UpdateLayeredWindow). It is not excluded from screen capture, so it shows in
streams and recordings. Only the Overlay's thread should create and use one: Windows
delivers a window's messages to the thread that made it.

Everything that needs Windows is set up inside `_load`, so importing this module
elsewhere is harmless; creating a LayeredWindow is not.
"""

import ctypes
from ctypes import wintypes
from functools import cache
from types import SimpleNamespace

import numpy as np

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020  # clicks and keys fall through to the game
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000  # never takes focus
WS_EX_TOOLWINDOW = 0x00000080  # no taskbar button, not in Alt+Tab
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x1, 0x2, 0x10, 0x40
SW_HIDE = 0
ULW_ALPHA = 2
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
PM_REMOVE = 1
CLASS_NAME = "StratagemCallerOverlay"
TITLE = "Stratagem Caller Overlay"


class _WNDCLASSEXW(ctypes.Structure):
    # The window procedure is typed c_void_p here and given a WINFUNCTYPE callback in `_load`.
    _fields_ = [
        ("cbSize", wintypes.UINT), ("style", wintypes.UINT), ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR), ("hIconSm", wintypes.HICON),
    ]  # fmt: skip


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]  # fmt: skip


class _BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte),
    ]  # fmt: skip


@cache
def _load() -> SimpleNamespace:
    """Bind the Win32 calls once, with their argument types, and register the window class."""
    user32, gdi32, kernel32 = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.kernel32
    lresult = ctypes.c_ssize_t
    wndproc_type = ctypes.WINFUNCTYPE(lresult, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = lresult
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(_WNDCLASSEXW)]
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
    ]  # fmt: skip
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.UpdateLayeredWindow.argtypes = [
        wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT), ctypes.POINTER(wintypes.SIZE), wintypes.HDC,
        ctypes.POINTER(wintypes.POINT), wintypes.DWORD, ctypes.POINTER(_BLENDFUNCTION), wintypes.DWORD,
    ]  # fmt: skip
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND] + [ctypes.c_int] * 4 + [wintypes.UINT]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.PeekMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT,
    ]  # fmt: skip
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC, ctypes.POINTER(_BITMAPINFOHEADER), wintypes.UINT, ctypes.POINTER(ctypes.c_void_p),
        wintypes.HANDLE, wintypes.DWORD,
    ]  # fmt: skip
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE

    # Kept alive here: Windows calls it for as long as the class exists.
    window_proc = wndproc_type(lambda h, m, w, l: user32.DefWindowProcW(h, m, w, l))
    instance = kernel32.GetModuleHandleW(None)
    window_class = _WNDCLASSEXW(
        cbSize=ctypes.sizeof(_WNDCLASSEXW),
        lpfnWndProc=ctypes.cast(window_proc, ctypes.c_void_p),
        hInstance=instance,
        lpszClassName=CLASS_NAME,
    )
    if not user32.RegisterClassExW(ctypes.byref(window_class)):
        raise OSError("RegisterClassExW failed: could not register the Overlay window class")
    return SimpleNamespace(user32=user32, gdi32=gdi32, instance=instance, window_proc=window_proc)


class LayeredWindow:
    """A topmost, click-through, never-focused window showing a premultiplied BGRA image."""

    def __init__(self, left: int, top: int, width: int, height: int):
        api = self._api = _load()
        self.width, self.height = width, height
        self._hwnd = self._screen_dc = self._memory_dc = self._bitmap = None
        self._shown = False
        self._opacity = 255  # the whole window's opacity; the picture's own alpha is on top of it
        try:
            self._create(api, left, top, width, height)
        except Exception:
            self.close()
            raise

    def _create(self, api, left: int, top: int, width: int, height: int) -> None:
        exstyle = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        self._hwnd = api.user32.CreateWindowExW(
            exstyle, CLASS_NAME, TITLE, WS_POPUP, left, top, width, height, None, None, api.instance, None
        )
        _check(self._hwnd, "CreateWindowExW")
        self._position = wintypes.POINT(left, top)
        self._size = wintypes.SIZE(width, height)
        self._screen_dc = _check(api.user32.GetDC(None), "GetDC")
        self._memory_dc = _check(api.gdi32.CreateCompatibleDC(self._screen_dc), "CreateCompatibleDC")
        header = _BITMAPINFOHEADER(ctypes.sizeof(_BITMAPINFOHEADER), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
        self._bits = ctypes.c_void_p()
        self._bitmap = _check(
            api.gdi32.CreateDIBSection(self._memory_dc, ctypes.byref(header), 0, ctypes.byref(self._bits), None, 0),
            "CreateDIBSection",
        )
        api.gdi32.SelectObject(self._memory_dc, self._bitmap)

    def show(self, image: np.ndarray) -> None:
        """Show `image` (height x width x 4, premultiplied BGRA) at the window's opacity,
        becoming visible if hidden."""
        if image.shape != (self.height, self.width, 4):
            raise ValueError(f"picture is {image.shape}, window is {(self.height, self.width, 4)}")
        image = np.ascontiguousarray(image)
        ctypes.memmove(self._bits, image.ctypes.data, image.nbytes)
        blend = _BLENDFUNCTION(AC_SRC_OVER, 0, self._opacity, AC_SRC_ALPHA)
        updated = self._api.user32.UpdateLayeredWindow(
            self._hwnd, self._screen_dc, ctypes.byref(self._position), ctypes.byref(self._size),
            self._memory_dc, ctypes.byref(wintypes.POINT(0, 0)), 0, ctypes.byref(blend), ULW_ALPHA,
        )  # fmt: skip
        _check(updated, "UpdateLayeredWindow")
        if not self._shown:
            # Topmost again each time it appears, in case the game has taken the top.
            self._api.user32.SetWindowPos(
                self._hwnd, wintypes.HWND(-1), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )  # fmt: skip
            self._shown = True

    def set_opacity(self, opacity: int) -> None:
        """Fade the whole window (0 invisible to 255 as drawn) without sending its picture
        again. Kept for the next `show` too. Call it before the first `show` or after."""
        if not 0 <= opacity <= 255:
            raise ValueError(f"opacity {opacity} is outside 0 to 255")
        if opacity == self._opacity:
            return
        self._opacity = opacity
        if self._shown:
            # No picture or position: only the blend changes, so this is cheap.
            blend = _BLENDFUNCTION(AC_SRC_OVER, 0, opacity, AC_SRC_ALPHA)
            updated = self._api.user32.UpdateLayeredWindow(
                self._hwnd, None, None, None, None, None, 0, ctypes.byref(blend), ULW_ALPHA
            )  # fmt: skip
            _check(updated, "UpdateLayeredWindow")

    def hide(self) -> None:
        if self._shown:
            self._api.user32.ShowWindow(self._hwnd, SW_HIDE)
            self._shown = False

    def pump(self) -> None:
        """Handle the window's pending messages. Call regularly, on the creating thread."""
        message = wintypes.MSG()
        while self._api.user32.PeekMessageW(ctypes.byref(message), None, 0, 0, PM_REMOVE):
            self._api.user32.TranslateMessage(ctypes.byref(message))
            self._api.user32.DispatchMessageW(ctypes.byref(message))

    def close(self) -> None:
        """Release whatever was created; safe after a partly failed construction."""
        api = self._api
        if self._hwnd:
            api.user32.DestroyWindow(self._hwnd)
        if self._bitmap:
            api.gdi32.DeleteObject(self._bitmap)
        if self._memory_dc:
            api.gdi32.DeleteDC(self._memory_dc)
        if self._screen_dc:
            api.user32.ReleaseDC(None, self._screen_dc)
        self._hwnd = self._screen_dc = self._memory_dc = self._bitmap = None


def _check(result, call: str):
    """A Win32 call that returns NULL or 0 on failure: fail loudly, naming the call."""
    if not result:
        raise OSError(f"{call} failed: could not set up the Overlay window")
    return result
