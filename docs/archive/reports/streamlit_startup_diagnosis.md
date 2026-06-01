# Streamlit Startup Diagnosis Report

## 1. Summary
- Reproduced historical failure from existing logs: Streamlit previously failed with `ImportError: cannot import name 'add_time_lap_state_features'`.
- Current source-level startup checks do not reproduce that import failure.
- Current startup command: `.\.venv\Scripts\python.exe -m streamlit run fh6_tuning_sim/ui/app.py`.
- Current server smoke test returned HTTP 200 on a temporary local port.
- Most likely historical root cause: stale Streamlit background process/module cache after code changed, not a missing function in current source.
- Additional high-risk runtime issue found and fixed: Streamlit navigation used widget key `page` while helper code also mutated `st.session_state.page`.

## 2. Environment
- Working directory: `C:\Users\12591\Documents\FH6`
- Python executable: `C:\Users\12591\Documents\FH6\.venv\Scripts\python.exe`
- Python version: `Python 3.13.5`
- Streamlit version: `1.58.0`
- Key dependencies installed:
  - `pandas 3.0.3`
  - `numpy 2.4.6`
  - `matplotlib 3.10.9`
  - `pyarrow 24.0.0`
- `plotly` is not installed, but it is not declared in project requirements and no direct project import was found.
- `pip check`: `No broken requirements found.`

## 3. Reproduction Steps
Commands used for current diagnosis:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show streamlit pandas numpy matplotlib plotly pyarrow
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q fh6_tuning_sim
.\.venv\Scripts\python.exe -c "import fh6_tuning_sim.ui.app as app; print('import ok'); print(app.__file__)"
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Historical error from `streamlit_ui.err.log`:

```text
ImportError: cannot import name 'add_time_lap_state_features' from 'fh6_tuning_sim.analysis.feature_engineering'
```

Current import smoke result:

```text
import ok
C:\Users\12591\Documents\FH6\fh6_tuning_sim\ui\app.py
```

Current Streamlit server smoke result on temporary port:

```text
http_status=200
```

## 4. Findings by Area

### A. Environment / Dependencies
- `.venv` exists and is used by `start_ui.bat`.
- Required packages from `requirements.txt` are installed.
- `pip check` reports no dependency conflicts.
- Current versions are newer than minimum bounds, especially Python 3.13, pandas 3, and numpy 2.4; this is a compatibility risk but not the observed startup blocker.

### B. Streamlit Entry
- `start_ui.bat` runs the correct command from the project root.
- `fh6_tuning_sim/ui/app.py` exists.
- `README.md` documents both `start_ui.bat` and direct Streamlit command.
- `start_ui.bat` previously closed after Streamlit exit, which could hide tracebacks for double-click users. This has been fixed by printing the exit code and pausing.

### C. Imports / Runtime
- `compileall` passed.
- `import fh6_tuning_sim.ui.app` passed.
- No internal import cycle was found in the UI/data-management path.
- Historical import error is not reproducible with current source.
- A likely runtime navigation issue was found: `st.sidebar.radio(..., key="page")` created a widget-backed key, while `set_page()` wrote to `st.session_state.page`. This can fail when navigation buttons are clicked. This has been fixed by using `_pending_page` and `nav_widget`.

### D. Config / JSON / Data Index
- 31 JSON files checked.
- All checked JSON files parse successfully.
- All dictionary files have valid `items` with required `key`, `label_zh`, and `label_en` fields.
- `data/index/runs_index.json` is present and contains 4 runs.
- `data/platform/platform_index.json` is present and contains 2 cars.
- Optional files `data/index/annotations.json` and `data/platform/route_profiles.json` may be missing; read helpers handle them as empty/default data.

### E. Tests
- `python -m unittest discover -s tests` passed.
- Current result: `Ran 9 tests ... OK`.
- Coverage includes packet parser, feature engineering, lap reset, route profile, annotation store, data quality behavior, diagnosis, and dataset window shape.

## 5. Root Cause Ranking
1. Stale Streamlit background process/module cache after source changes. Most likely cause of the historical import error because current source and venv import successfully.
2. Streamlit widget session-state conflict in navigation. Fixed by separating `nav_widget` from `_pending_page`.
3. `start_ui.bat` did not pause after Streamlit exit, hiding tracebacks for double-click startup failures. Fixed by printing exit code and pausing.
4. Write permissions during startup initialization. Possible but not observed in this workspace.
5. Dependency incompatibility from very new Python/pandas/numpy. Possible future risk but not observed in current checks.

## 6. Minimal Fix Plan
Applied minimal fixes only:
- Keep existing UI structure and pages.
- Do not touch CLI, packet parser, logger, or raw telemetry behavior.
- Replace direct `st.session_state.page` mutation with `_pending_page` and `nav_widget`.
- Keep startup crash details visible in `start_ui.bat`.

## 7. Files That Need Changes
Changed:
- `fh6_tuning_sim/ui/app.py`
- `start_ui.bat`
- `reports/streamlit_startup_diagnosis.md`

No changes were made to:
- packet parser
- telemetry logger
- UDP listener
- feature engineering pipeline
- existing data/index or config JSON content

## 8. Risk Notes
- Navigation fix is low risk and localized to Streamlit session-state behavior.
- Startup script change affects only user visibility after Streamlit exits; it does not change the Streamlit command itself.
- Existing CLI commands remain untouched.
- Existing raw telemetry files are untouched.
- Streamlit still emits `use_container_width` deprecation warnings; these are non-blocking and intentionally left out of the minimal fix.

## 9. Verification Plan
Run after repair:

```powershell
.\.venv\Scripts\python.exe -m compileall fh6_tuning_sim
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -c "import fh6_tuning_sim.ui.app"
.\.venv\Scripts\python.exe -m streamlit run fh6_tuning_sim/ui/app.py --server.headless=true --server.port=8766 --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

Manual checks:
- Open `http://127.0.0.1:8501` or the printed local URL.
- Confirm Dashboard loads.
- Click into Car Detail, Route Detail, and Run Review.
- Confirm no widget/session-state exception appears.
