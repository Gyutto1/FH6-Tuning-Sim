@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD=.venv\Scripts\python.exe"
)

if not defined PYTHON_CMD (
  where py >nul 2>nul
  if %ERRORLEVEL% EQU 0 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if %ERRORLEVEL% EQU 0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo Python was not found.
  echo Run setup_windows.bat first, or install Python 3.10+.
  pause
  exit /b 1
)

echo Installing/updating PyInstaller...
%PYTHON_CMD% -m pip install "pyinstaller>=6.0"
if %ERRORLEVEL% NEQ 0 (
  echo PyInstaller installation failed.
  pause
  exit /b 1
)

echo Building portable onedir package...
%PYTHON_CMD% -m PyInstaller -y --clean FH6TuningSim.spec
if %ERRORLEVEL% NEQ 0 (
  echo Build failed.
  pause
  exit /b 1
)

echo.
echo Portable build ready:
echo   dist\FH6TuningSim\FH6TuningSim.exe
echo.
echo The folder includes configs and data beside the EXE.
pause
endlocal
