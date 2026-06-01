# FH6 Tuning Sim ? GitHub Distribution Notes

?????2026-05-31

---

## ????

?????? GitHub ???????????????
- Windows 10/11 PC
- ? FH6 ??
- ????????????? bat ?????

---

## .gitignore ??

????????
```gitignore
# Python virtual environments
.venv/
.venv2/
.venv312/
venv/

# Raw data (large files)
data/raw/*.csv

# Logs
*.log
logs/

# Backup files
*.bak.*.json
*.bak.*.db

# OS files
Thumbs.db
.DS_Store
__pycache__/
*.pyc
*.pyo

# IDE
.vscode/
.idea/

# Distribution
dist/
build/
*.spec
*.exe
```

---

## ???????

### ????
```
fh6_tuning_sim/          # ?? Python ??
tests/                   # 29 tests
configs/                 # ?????
notebooks/               # Jupyter notebooks????
```

### ????
```
setup_windows.bat        # ????????? venv + pip install?
start_desktop.bat        # ???????
start_fh6_tool.bat       # CLI ???????
start_ui.bat             # Streamlit ???????
```

### ????
```
data/index/runs_index.json    # ?? demo ??
data/platform/platform_index.json
data/demo/                     # demo ?????????
```

### ??
```
README.md
ARCHITECTURE.md
PROJECT_STATUS.md
NEXT_STEPS.md
AGENTS.md
reports/                 # ???????? run ???
```

---

## setup_windows.bat ??

```bat
@echo off
echo FH6 Tuning Sim - Windows Setup
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Create virtual environment
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate and install
call .venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt

REM Initialize database
echo Initializing database...
python -m fh6_tuning_sim.data_management.db_init

echo.
echo Setup complete! Run start_desktop.bat to launch.
pause
```

---

## start_desktop.bat ??

```bat
@echo off
call .venv\Scripts\activate.bat
python -m fh6_tuning_sim.ui_desktop.app
pause
```

---

## requirements.txt ??

```
# Core
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
pyarrow>=12.0

# Desktop UI (0.99 beta)
PySide6>=6.8

# Legacy (Streamlit, retained)
streamlit>=1.25

# Database (0.99 beta)
# sqlite3 is stdlib, no extra dependency
```

---

## ??????

0.99 beta ????????????
- 1 ??????Mercedes-AMG GT?
- 1-2 ? demo run?? CSV?? demo_udp.csv?
- ???????
- ???????? 4 ? road_test run?????????

???????????`fh6_tuning_sim/data_management/db_init.py`

---

## ??????

```
1. Clone repo: git clone <url>
2. ?? setup_windows.bat
3. ?? start_desktop.bat
4. ?????? Mercedes-AMG GT demo ??
5. ??????? FH6 Data Out ? ??????
```
