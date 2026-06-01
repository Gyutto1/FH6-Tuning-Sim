# Desktop 0.99 Beta Handoff To 1.0

Date: 2026-05-31

## 1.0 Goal

1.0 should make the real friend-testing workflow reliable on Windows 10/11:

```text
Install dependencies
Launch PySide6 Desktop
Create/select Car
Create/select Build
Create/select Tune
Confirm Setup Snapshot
Select Route / Record Type / Tags
Start Recording
Save Run
Search, edit, tag, annotate, and archive Run in Run Library
```

## Current 0.99 Foundation

- SQLite is primary storage.
- JSON is legacy/import/export.
- Repository layer exists.
- Required hierarchy exists:

```text
Car -> Build -> Tune -> Setup Snapshot -> Run
```

- Recording cannot start without complete context.
- Runs bind to `setup_snapshot_id`.
- Experiment Matrix has placeholder schema/repository.
- Upgrade catalog and tune parameter extensibility tables exist.

## 1.0 P0 Work

1. Validate a clean Windows 10/11 clone:
   - `setup_windows.bat`
   - `start_desktop.bat`
   - PySide6 opens reliably
2. Run one real FH6 Data Out recording.
3. Confirm saved Run appears in Run Library with:
   - Car
   - Build
   - Tune
   - Setup Snapshot
   - Route/Route Mode
   - Record Type
   - Intent Tags
4. Add UI dialogs for creating/editing:
   - Build
   - Tune
   - Setup Snapshot
5. Clean remaining legacy hard-coded/mojibake labels into dictionaries or database labels.
6. Decide zero-packet recording behavior:
   - allow draft run
   - or block save until packet_count > 0
7. Run Git ignore validation in a real Git checkout.

## 1.0 P1 Work

- Add a simple Experiment Matrix placeholder page.
- Add post-record analysis actions for feature engineering/plots/reports.
- Improve Route selection/editing UX.
- Add dataset/annotation management polish.
- Add export/import commands for SQLite <-> JSON handoff.

## Known Carryover Risks

- Current local `.venv` cannot import `PySide6.QtWidgets`; use Python 3.10-3.12 from python.org for clean setup.
- No real FH6 UDP recording was performed in this coding run.
- GitHub ignore rules were statically reviewed but not verified with `git`.
- Some PySide6 labels are still legacy hard-coded/mojibake strings.
- Upgrade/tune parameter tables exist, but full catalogs are not populated.

## Do Not Do In 1.0

```text
AI training
world model training
reinforcement learning
automatic tune optimizer
full scoring/evaluation system
full Route Profile boundary fusion
full lap simulation
packet parser rewrite
UDP listener rewrite
raw telemetry schema change
hard-delete user data
delete Streamlit
commercial EXE packaging
```
