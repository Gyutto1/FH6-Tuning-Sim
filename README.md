# FH6 Tuning Sim

Forza Horizon 6 telemetry and vehicle-centered tuning data platform.

Current maintained UI is **PySide6 Desktop** with SQLite primary storage.

Core hierarchy:

```text
Car -> Build -> Tune -> Setup Snapshot -> Run
```

## Quick Start (Windows)

1. Run `setup_windows.bat`
2. Run `start_desktop.bat`

Manual commands:

```powershell
.\.venv\Scripts\python.exe -m fh6_tuning_sim.db.init_db --legacy --demo
.\.venv\Scripts\python.exe -m fh6_tuning_sim.ui_desktop.app
```

If local `.venv` cannot load Qt, `start_desktop.bat` will try local `.venv312` fallback.

## Required Docs First

Read in this order before code changes:

```text
AI_READING_GUIDE.md
PROJECT_STATUS.md
CURRENT_TASK.md
docs/current/*
current_handoff_after_client_rewire.md
```

## CLI Tools (Preserved)

```powershell
.\.venv\Scripts\python.exe -m fh6_tuning_sim.receiver.udp_listener --host 127.0.0.1 --port 9999 --tune-config configs/tune_config.json --notes "baseline run"
.\.venv\Scripts\python.exe -m fh6_tuning_sim.analysis.feature_engineering data/raw/<session_id>.csv --output data/processed/<session_id>_processed.csv
.\.venv\Scripts\python.exe -m fh6_tuning_sim.visualization.plot_timeseries data/processed/<session_id>_processed.csv --output reports/<session_id>_timeseries.png
.\.venv\Scripts\python.exe -m fh6_tuning_sim.analysis.report_generator data/processed/<session_id>_processed.csv --metadata data/sessions/<session_id>_meta.json --tune-config data/sessions/<session_id>_tune.json --output reports/<session_id>_report.md
.\.venv\Scripts\python.exe -m fh6_tuning_sim.analysis.tune_compare data/processed/run_a.csv data/processed/run_b.csv --left-name baseline --right-name revised --output reports/baseline_vs_revised.md
.\.venv\Scripts\python.exe -m fh6_tuning_sim.models.dataset data/processed/<session_id>_processed.csv --output data/processed/<session_id>_dataset.npz --past-samples 60 --future-samples 12
```

## Validation

```powershell
.\.venv\Scripts\python.exe -m compileall fh6_tuning_sim tests
.\.venv\Scripts\python.exe -m unittest discover -s tests
py -3 smoke_test.py
```

## Archive Policy

- Legacy Streamlit code and old reports are archived under `docs/archive/`.
- `docs/archive/` is not part of default reading scope unless explicitly requested.
