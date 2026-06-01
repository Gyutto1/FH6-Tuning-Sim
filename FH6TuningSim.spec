# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules

extra_binaries = []

# Conda-based Python runtime dependencies that PyInstaller does not always detect.
conda_bin = Path(sys.base_prefix) / "Library" / "bin"
for dll_name in (
    "ffi.dll",
    "libssl-3-x64.dll",
    "libcrypto-3-x64.dll",
    "libmpdec-4.dll",
    "libexpat.dll",
    "sqlite3.dll",
    "libbz2.dll",
    "liblzma.dll",
    "tcl86t.dll",
    "tk86t.dll",
):
    dll_path = conda_bin / dll_name
    if dll_path.exists():
        extra_binaries.append((str(dll_path), "."))

# PortableGit fallback for libffi chain when host runtime does not expose ffi.dll.
for dll_name in ("libffi-8.dll", "libwinpthread-1.dll", "libgcc_s_seh-1.dll"):
    dll_path = Path("tools/PortableGit/mingw64/bin") / dll_name
    if dll_path.exists():
        extra_binaries.append((str(dll_path), "."))

a = Analysis(
    ["fh6_tuning_sim/ui_desktop/app.py"],
    pathex=["."],
    binaries=extra_binaries,
    datas=[
        ("configs", "configs"),
        ("data", "data"),
    ],
    hiddenimports=collect_submodules("fh6_tuning_sim"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FH6TuningSim",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory=".",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FH6TuningSim",
)
