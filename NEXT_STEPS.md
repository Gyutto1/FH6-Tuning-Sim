# FH6 Tuning Sim Next Steps

Updated: 2026-05-31

## Immediate Next Step

Continue from the completed v0.99.1 handoff:

```text
reports/current_handoff_after_0_99_1.md
reports/desktop_0_99_1_ui_data_stabilization_report.md
```

## P0 Manual Validation

1. Run a clean Windows 10/11 clone workflow:
   - `setup_windows.bat`
   - `start_desktop.bat`
2. Verify Desktop navigation:
   - Car Detail
   - Build Detail
   - Tune Detail
   - Record Run Wizard
   - Run Library
3. Run one real FH6 Data Out recording:
   - select Car
   - select Build
   - select Tune
   - confirm Setup Snapshot
   - select Route Mode / Record Type / Intent Tag
   - Start/Stop Recording
   - confirm Run appears in Run Library
4. Verify tag workflow:
   - create a Chinese tag
   - bind it to a run
   - confirm Run card displays Chinese label
   - filter by that tag
   - remove the tag and confirm it no longer matches
5. Run Git validation in a real checkout:
   - `git status --ignored`
   - `git check-ignore -v data/raw/`
   - `git check-ignore -v data/processed/`
   - `git check-ignore -v data/cache/`
   - `git check-ignore -v data/fh6_tuning_sim.db`

## P1 Before 1.0

1. Populate real tune parameter definitions gradually from game data.
2. Improve Setup Snapshot creation flow beyond editing existing snapshots.
3. Clean remaining legacy mojibake labels in older pages.
4. Add optional post-record analysis trigger for feature engineering/plot/report without blocking UI.

## Do Not Do

```text
AI training
world model training
reinforcement learning
automatic tuning optimizer
full Route Profile boundary fusion
full lap simulation
EXE commercial packaging
packet parser rewrite
UDP listener rewrite
raw telemetry schema change
hard-delete user data
delete Streamlit
```
