from __future__ import annotations

import ctypes
import os
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent
_PYSIDE6_DIR = _PKG_ROOT.parent / ".venv" / "Lib" / "site-packages" / "PySide6"

if _PYSIDE6_DIR.exists():
    _pyside6_str = str(_PYSIDE6_DIR.resolve())
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_pyside6_str)

    _LOAD_WITH_ALTERED_SEARCH_PATH = 0x00000008
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    for _dll_name in [
        "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll",
        "msvcp140_2.dll", "msvcp140_codecvt_ids.dll", "concrt140.dll",
        "vccorlib140.dll", "vcomp140.dll", "vcamp140.dll", "vcruntime140.dll",
    ]:
        _dll_path = os.path.join(_pyside6_str, _dll_name)
        if os.path.exists(_dll_path):
            try:
                _kernel32.LoadLibraryExW(_dll_path, None, _LOAD_WITH_ALTERED_SEARCH_PATH)
            except OSError:
                pass
