"""Where Peelpad keeps its files, and whether it runs from the Microsoft Store."""

from __future__ import annotations

import ctypes
import os
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def packaged() -> bool:
    """True when Peelpad runs as an MSIX package (the Microsoft Store version)."""
    if sys.platform != "win32":
        return False
    length = ctypes.c_uint32(0)
    # ERROR_INSUFFICIENT_BUFFER (122) means there is a package; APPMODEL_ERROR_NO_PACKAGE (15700) means not
    return ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None) == 122


def app_data_dir() -> Path:
    base = os.environ.get("PEELPAD_HOME") or os.path.join(os.environ.get("APPDATA") or str(Path.home()), "Peelpad")
    folder = Path(base)
    folder.mkdir(parents=True, exist_ok=True)
    return folder
