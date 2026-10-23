"""Where Peelpad keeps its files."""

from __future__ import annotations

import os
from pathlib import Path


def app_data_dir() -> Path:
    base = os.environ.get("PEELPAD_HOME") or os.path.join(os.environ.get("APPDATA") or str(Path.home()), "Peelpad")
    folder = Path(base)
    folder.mkdir(parents=True, exist_ok=True)
    return folder
