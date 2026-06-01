# Desktop 0.99 Beta Implementation Report

Date: 2026-05-31

## Summary

Desktop 0.99 beta has been implemented as the data architecture stabilization release. SQLite is now the primary desktop storage, and the application uses the required Car -> Build -> Tune -> Setup Snapshot -> Run hierarchy before recording can create a run.

## Phase Completion

### Phase 1: SQLite Schema / Migration / Seed

Completed:

- Added `fh6_tuning_sim/db/schema.sql`.
- Added migration runner and `schema_version`.
- Added legacy JSON -> SQLite migration.
- Added demo seed database generation.
- Generated `data/fh6_tuning_sim.db` and `data/demo/fh6_demo.db`.

### Phase 2: Repository Layer

Completed:

- Added repository classes for core entities.
- Added transaction-based writes.
- Added run creation with required context fields.
- Added Experiment Matrix placeholder repository.

### Phase 3: PySide6 SQLite Service

Completed:

- Replaced JSON-primary `DesktopDataService` behavior with SQLite-backed repository calls.
- Kept the v0.5 API shape where possible to reduce UI churn.

### Phase 4: Context Workflow UI

Completed:

- Car Detail exposes Build/Tune/Setup Snapshot information.
- Record Run page loads Build, Tune, and Setup Snapshot choices for the selected car.
- Default stock Build, baseline Tune, and default Setup Snapshot can be created/used instead of unknown orphan context.

### Phase 5: Run Library On SQLite

Completed:

- Run Library reads from SQLite.
- Filters include Car, Build, Tune, Setup Snapshot, Route Mode, Record Type, Quality, Tag, and text search.
- Existing archive/edit/tag behavior remains supported through SQLite-backed service calls.

### Phase 6: Recording Preconditions

Completed:

- Added `RecordingContextService`.
- Recording Start is blocked unless all required context is valid.
- Runs cannot be created without `car_id`, `build_id`, `tune_id`, and `setup_snapshot_id`.

### Phase 7: Minimal RecordingWorker Integration

Completed:

- Record Run uses QThread + `RecordingWorker`.
- UI remains non-blocking.
- On session completion, the UI creates a SQLite run with full context.
- Packet parser, UDP listener behavior, and raw telemetry schema were left unchanged.

### Phase 8: Distribution / Windows Readiness

Completed:

- Updated `.gitignore`.
- Updated `setup_windows.bat`.
- Updated `start_desktop.bat`.
- Updated README/status/next-step docs.
- Added QA distribution report.

### Phase 9: Final QA / Handoff

Completed:

- Ran compile, unit, offscreen UI, and DB integrity checks.
- Generated final handoff documents.

## Acceptance Criteria Result

```text
SQLite schema design: PASS
JSON -> SQLite migration: PASS
Repository layer: PASS
PySide6 page adjustment: PASS
Car/Build/Tune/Setup Snapshot/Run relationship: PASS
Recording preconditions: PASS
Experiment Matrix placeholder: PASS
GitHub/Windows distribution plan/scripts: PASS with manual Git validation pending
Five-agent phase reports: PASS
No AI/optimizer/raw parser rewrite: PASS
```

## Verification

```text
.venv312\python.exe -m compileall fh6_tuning_sim
PASS

.venv312\python.exe -m unittest discover -s tests
Ran 41 tests
OK

offscreen MainWindow smoke
PASS

offscreen Record Run + Run Library smoke
PASS

SQLite foreign_key_check
[]

orphan_runs
0
```

## Important Notes

- `.venv\Scripts\python.exe` passes compile/unit tests but fails `PySide6.QtWidgets` import in this workspace.
- `.venv312\python.exe` passes PySide6 smoke tests.
- `setup_windows.bat` now checks `PySide6.QtWidgets` explicitly.
- `start_desktop.bat` has a local `.venv312` fallback.
- Git checks could not be run because `git` is unavailable and there is no `.git` directory.
