"""Only one copy of the tool runs at a time: two would type every Call twice.

The tool claims a machine-wide named lock (a Win32 named mutex) before it hooks the keyboard.
The OS releases it when the process ends, however it ends, so a crash never blocks the next start.
"""

import ctypes
from ctypes import wintypes

# "Global\" is shared by every login session; "Local\" would only see this one.
LOCK_NAME = "Global\\StratagemCaller"

_ERROR_ACCESS_DENIED = 5
_ERROR_ALREADY_EXISTS = 183


class InstanceLock:
    """A claim on the lock, held until `release` or until the process ends."""

    def __init__(self, handle: int, close_handle):
        self._handle = handle
        self._close_handle = close_handle

    def release(self) -> None:
        """Let go of the lock. Safe to call again."""
        handle, self._handle = self._handle, None
        if handle is not None:
            self._close_handle(handle)


def claim(name: str = LOCK_NAME) -> InstanceLock | None:
    """The lock called `name` if nothing holds it, else None. Raises if the OS fails to say."""
    assert name, "a lock needs a name"
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.CreateMutexW(None, False, name)
    error = ctypes.get_last_error()
    if not handle:
        if error == _ERROR_ACCESS_DENIED:
            # The holder runs elevated (the shortcut's "Run as administrator") and this copy does
            # not, so the OS will not even let it open the lock: someone else holds it.
            return None
        raise ctypes.WinError(error)
    if error == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)  # only our handle to the holder's lock; theirs stays
        return None
    return InstanceLock(handle, kernel32.CloseHandle)
