from __future__ import annotations

import os
import sys
from pathlib import Path


def _set_qt_plugin_paths() -> None:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    plugins_dir = base_dir / "PySide6" / "plugins"
    platform_dir = plugins_dir / "platforms"

    if plugins_dir.exists():
        os.environ["QT_PLUGIN_PATH"] = str(plugins_dir)
    if platform_dir.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platform_dir)


_set_qt_plugin_paths()
