@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  echo Existing virtual environment found.
  goto :install
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -c "import sys" >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py"
    goto :setup
  )
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python -c "import sys" >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
    goto :setup
  )
)

echo Python was not found.
echo Install Python 3.10+ from https://www.python.org/downloads/windows/.
echo Enable "Add python.exe to PATH" during installation.
pause
exit /b 1

:setup
echo Creating virtual environment...
%PYTHON_CMD% -m venv .venv
if %ERRORLEVEL% NEQ 0 (
  echo Failed to create .venv.
  pause
  exit /b 1
)

:install
echo Checking installed dependencies...
".venv\Scripts\python.exe" -c "import pandas, matplotlib, numpy, pyarrow; from PySide6.QtWidgets import QApplication" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  echo Dependencies already installed.
  goto :database
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo Installing project dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

echo Verifying PySide6 desktop runtime...
".venv\Scripts\python.exe" -c "from PySide6.QtWidgets import QApplication" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo PySide6 Qt runtime could not be loaded from .venv.
  echo If you are using Conda Python, recreate .venv with Python 3.10-3.12 from python.org and rerun setup_windows.bat.
  pause
  exit /b 1
)

:database
echo Initializing SQLite databases...
".venv\Scripts\python.exe" -m fh6_tuning_sim.db.init_db --legacy --demo
if %ERRORLEVEL% NEQ 0 (
  echo Database initialization failed.
  pause
  exit /b 1
)

echo.
echo Setup complete.
echo Start the desktop app with start_desktop.bat.
pause
endlocal
