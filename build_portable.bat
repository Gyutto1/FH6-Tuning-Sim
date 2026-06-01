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

echo Preparing testable portable folder...
if exist "portable_test\FH6TuningSim" rmdir /s /q "portable_test\FH6TuningSim"
mkdir "portable_test\FH6TuningSim"
xcopy "dist\FH6TuningSim\*" "portable_test\FH6TuningSim\" /E /I /Y >nul

if exist "portable_test\FH6TuningSim\_internal\data" (
  if exist "portable_test\FH6TuningSim\data" rmdir /s /q "portable_test\FH6TuningSim\data"
  move "portable_test\FH6TuningSim\_internal\data" "portable_test\FH6TuningSim\data" >nul
)
if exist "portable_test\FH6TuningSim\_internal\configs" (
  if exist "portable_test\FH6TuningSim\configs" rmdir /s /q "portable_test\FH6TuningSim\configs"
  move "portable_test\FH6TuningSim\_internal\configs" "portable_test\FH6TuningSim\configs" >nul
)

> "portable_test\FH6TuningSim\README_START_HERE.txt" echo FH6 Tuning Sim Portable (v1.1)
>> "portable_test\FH6TuningSim\README_START_HERE.txt" echo.
>> "portable_test\FH6TuningSim\README_START_HERE.txt" echo 1. Double-click FH6TuningSim.exe
>> "portable_test\FH6TuningSim\README_START_HERE.txt" echo 2. Keep data, configs, and _internal in the same folder
>> "portable_test\FH6TuningSim\README_START_HERE.txt" echo 3. If SmartScreen appears, click More info ^> Run anyway

echo Building release zip...
if not exist "releases" mkdir "releases"
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'releases\\FH6TuningSim_portable_v1_1.zip') { Remove-Item -LiteralPath 'releases\\FH6TuningSim_portable_v1_1.zip' -Force }; Compress-Archive -Path 'portable_test\\FH6TuningSim' -DestinationPath 'releases\\FH6TuningSim_portable_v1_1.zip' -CompressionLevel Optimal"
if %ERRORLEVEL% NEQ 0 (
  echo Zip build failed.
  pause
  exit /b 1
)

echo.
echo Portable build ready:
echo   dist\FH6TuningSim\FH6TuningSim.exe
echo Test folder:
echo   portable_test\FH6TuningSim\FH6TuningSim.exe
echo Release zip:
echo   releases\FH6TuningSim_portable_v1_1.zip
echo.
echo Use portable_test for direct local run, no unzip required.
pause
endlocal
