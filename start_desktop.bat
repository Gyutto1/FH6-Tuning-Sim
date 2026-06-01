@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "from PySide6.QtWidgets import QApplication" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=.venv\Scripts\python.exe"
)

if not defined PYTHON_CMD (
  if exist ".venv312\python.exe" (
    ".venv312\python.exe" -c "from PySide6.QtWidgets import QApplication" >nul 2>nul
    if not errorlevel 1 (
      echo Using local developer environment .venv312.
      set "PYTHON_CMD=.venv312\python.exe"
    )
  )
)

if not defined PYTHON_CMD (
  echo No usable PySide6 desktop Python environment was found.
  echo Run setup_windows.bat first.
  echo If .venv exists but fails here, recreate it with Python 3.10-3.12 from python.org and rerun setup_windows.bat.
  pause
  exit /b 1
)

"%PYTHON_CMD%" -m fh6_tuning_sim.ui_desktop.app
endlocal
