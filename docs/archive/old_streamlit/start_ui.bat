@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Running setup first...
  call setup_windows.bat
)

if not exist ".venv\Scripts\python.exe" (
  echo Setup did not create .venv.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run fh6_tuning_sim/ui/app.py
set "STREAMLIT_EXIT_CODE=%ERRORLEVEL%"
echo.
echo Streamlit exited with code %STREAMLIT_EXIT_CODE%.
echo If the UI failed to start, keep this window open and read the traceback above.
pause
endlocal
