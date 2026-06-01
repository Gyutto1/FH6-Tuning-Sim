"""FH6 Tuning Sim - PySide6 Desktop MVP entry point.

Start with:
    python -m fh6_tuning_sim.ui_desktop.app
"""

from __future__ import annotations

import ctypes
import importlib.util
import os
import sys
from pathlib import Path

from fh6_tuning_sim.runtime_paths import app_root

ROOT = app_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Work around Conda Python vcruntime/msvcp DLL conflicts by
# force-loading PySide6-bundled VC++ DLLs from the active Python env.
_pyside6_spec = importlib.util.find_spec("PySide6")
if _pyside6_spec and _pyside6_spec.submodule_search_locations:
    _PYSIDE6_DIR = Path(next(iter(_pyside6_spec.submodule_search_locations)))
else:
    _PYSIDE6_DIR = ROOT / ".venv" / "Lib" / "site-packages" / "PySide6"
if _PYSIDE6_DIR.exists():
    _pyside6_str = str(_PYSIDE6_DIR.resolve())
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_pyside6_str)

    # Pre-load all VC++ runtime DLLs from PySide6 to prevent Conda's
    # incompatible versions from being used.
    _PRELOAD_DLLS = [
        "vcruntime140_1.dll",
        "msvcp140.dll",
        "msvcp140_1.dll",
        "msvcp140_2.dll",
        "msvcp140_codecvt_ids.dll",
        "concrt140.dll",
        "vccorlib140.dll",
        "vcomp140.dll",
        "vcamp140.dll",
        "vcruntime140.dll",
    ]
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # Use LOAD_WITH_ALTERED_SEARCH_PATH so dependencies are resolved
    # from the DLL's own directory.
    _LOAD_WITH_ALTERED_SEARCH_PATH = 0x00000008
    for _dll_name in _PRELOAD_DLLS:
        _dll_path = os.path.join(_pyside6_str, _dll_name)
        if os.path.exists(_dll_path):
            try:
                _kernel32.LoadLibraryExW(_dll_path, None, _LOAD_WITH_ALTERED_SEARCH_PATH)
            except OSError:
                pass


def main() -> None:
    from PySide6.QtWidgets import QApplication
    from fh6_tuning_sim.ui_desktop.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("FH6 Tuning Sim")
    app.setOrganizationName("FH6")

    app.setStyleSheet("""
    QWidget {
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 13px;
        color: #111111;
    }
    QDialog, QInputDialog, QMessageBox {
        background-color: #ffffff;
    }
    QInputDialog QLabel, QMessageBox QLabel {
        color: #111111;
    }
    QInputDialog QLineEdit, QInputDialog QTextEdit, QInputDialog QPlainTextEdit {
        background-color: #ffffff;
        color: #111111;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 4px 8px;
    }
    QInputDialog QComboBox {
        background-color: #ffffff;
        color: #111111;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 4px 8px;
    }
    QInputDialog QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #111111;
        selection-background-color: #e8f0ea;
        selection-color: #111111;
    }
    QMessageBox QPushButton {
        background-color: #f5f5f5;
        color: #111111;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 6px 16px;
        min-width: 72px;
    }
    QMessageBox QPushButton:hover {
        background-color: #ebebeb;
    }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
