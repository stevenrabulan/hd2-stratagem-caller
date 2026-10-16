"""Let modules that load Windows DLLs at import be imported, and tested, elsewhere."""

import ctypes
import sys
from unittest import mock

if sys.platform != "win32" and not hasattr(ctypes, "windll"):
    ctypes.windll = mock.MagicMock()
