@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" fh6_launcher.py
  goto :end
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -c "import sys" >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    py fh6_launcher.py
    goto :end
  )
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python -c "import sys" >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    python fh6_launcher.py
    goto :end
  )
)

echo Python was not found.
echo Install Python 3.10+ first, then run setup_windows.bat.
pause

:end
endlocal
