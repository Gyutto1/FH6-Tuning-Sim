# Current Handoff After 0.99 Run

Date: 2026-05-31

## 1. Current Phase

Phase 9 is complete for the current coding run. Desktop 0.99 beta data architecture, repository layer, PySide6 SQLite integration, guarded recording workflow, distribution scripts, and final QA reports have been implemented.

Manual Windows 10/11 friend testing remains before calling the project 1.0-ready.

## 2. Completed Features

- SQLite primary storage at `data/fh6_tuning_sim.db`.
- Demo/sample database at `data/demo/fh6_demo.db`.
- `schema_version` migration base.
- Legacy JSON -> SQLite migration from existing platform/runs/tags JSON.
- Car -> Build -> Tune -> Setup Snapshot -> Run data chain.
- Build Snapshot, upgrade category/option/selection, compatibility placeholder tables.
- Extensible tune parameter definition/value tables.
- Tags, routes, datasets, annotations, experiment matrix placeholders in SQLite.
- Repository layer for core entities.
- `RecordingContextService` validation.
- PySide6 `DesktopDataService` now backed by SQLite repositories.
- Car Detail shows Build/Tune/Setup Snapshot context.
- Run Library reads SQLite and filters by car/build/tune/setup/route/type/tag.
- Record Run requires full context before Start.
- Minimal QThread `RecordingWorker` integration creates full-context SQLite runs.
- Windows setup/start scripts updated.
- Final QA/distribution reports generated.

## 3. Unfinished Features

- Full manual Windows 10/11 clone/install/run validation.
- Rich Build/Tune/Setup Snapshot creation/edit dialogs.
- Full upgrade parts catalog and compatibility rule UI.
- Full tune parameter catalog UI.
- Experiment Matrix functional page.
- Post-record analysis trigger integration.
- Dictionary cleanup for remaining legacy hard-coded/mojibake PySide6 labels.
- Git ignore verification in a real Git checkout.

## 4. Main Files Added Or Modified

Added SQLite/data layer:

- `fh6_tuning_sim/db/schema.sql`
- `fh6_tuning_sim/db/connection.py`
- `fh6_tuning_sim/db/migrations.py`
- `fh6_tuning_sim/db/legacy_migration.py`
- `fh6_tuning_sim/db/init_db.py`
- `fh6_tuning_sim/db/repositories/*.py`
- `fh6_tuning_sim/db/services/recording_context_service.py`
- `fh6_tuning_sim/db/seed_data/demo_seed.py`

Modified PySide6/UI:

- `fh6_tuning_sim/ui_desktop/app.py`
- `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py`
- `fh6_tuning_sim/ui_desktop/pages/car_detail_page.py`
- `fh6_tuning_sim/ui_desktop/pages/record_run_page.py`
- `fh6_tuning_sim/ui_desktop/pages/run_library_page.py`
- `fh6_tuning_sim/ui_desktop/main_window.py`

Modified tests/docs/distribution:

- `tests/test_sqlite_schema_migration.py`
- `tests/test_sqlite_repositories.py`
- `tests/test_recording_context_service.py`
- `tests/test_run_library_filter.py`
- `.gitignore`
- `setup_windows.bat`
- `start_desktop.bat`
- `README.md`
- `ARCHITECTURE.md`
- `AGENTS.md`
- `PROJECT_STATUS.md`
- `NEXT_STEPS.md`

## 5. SQLite Schema / Migration / Repository State

Schema includes:

```text
schema_version
cars
builds
build_snapshots
upgrade_categories
upgrade_options
build_upgrade_selections
upgrade_compatibility_rules
tunes
tune_parameter_definitions
tune_parameter_values
setup_snapshots
routes
tags
runs
run_tags
annotations
annotation_tags
dataset_groups
dataset_group_runs
experiment_matrices
experiment_variables
experiment_tasks
recording_sessions
```

Current main DB check:

```text
cars=2
builds=2
tunes=2
setup_snapshots=2
runs=4
tags=148
routes=3
foreign_key_check=[]
orphan_runs=0
```

Repository layer exists for Cars, Builds, Tunes, Setup Snapshots, Runs, Tags, Routes, and Experiment Matrix placeholders. Writes are repository-based and use transactions.

## 6. PySide6 UI State

- Desktop uses SQLite through `DesktopDataService`.
- Dashboard/Cars/Car Detail/Run Library/Record Run stay runnable.
- Car Detail is vehicle-centered and exposes Build -> Tune -> Setup Snapshot context.
- Run Library filters against SQLite.
- Record Run has Car/Build/Tune/Setup Snapshot/Route Mode/Record Type/Intent Tag validation.
- Existing UI still needs label dictionary cleanup before polish; some older PySide6 labels are mojibake/hard-coded.

## 7. RecordingController State

Recording is minimally connected through `RecordingWorker` on a QThread. The UI does not start recording until context validation passes.

Run creation now requires:

```text
car_id
build_id
tune_id
setup_snapshot_id
route_mode / route_id when applicable
record_type
at least one intent tag
```

Packet parser behavior, UDP listener behavior, and raw telemetry CSV schema were not changed.

## 8. Test Results

Executed with `.venv312\python.exe`:

```text
python -m compileall fh6_tuning_sim
PASS

python -m unittest discover -s tests
41 tests PASS

offscreen MainWindow smoke
PASS

offscreen Record Run + Run Library smoke
PASS

SQLite foreign_key_check
PASS

orphan run check
PASS
```

Also executed with `.venv\Scripts\python.exe`:

```text
compileall PASS
41 tests PASS
PySide6.QtWidgets import FAIL
```

The `.venv` failure is an environment/runtime issue in this workspace's Anaconda Python 3.13 environment. The setup script now validates this explicitly.

## 9. Known Issues

- Current `.venv` cannot load `PySide6.QtWidgets`; `.venv312` works. Fresh Windows setup should prefer Python 3.10-3.12 from python.org.
- `git` is not installed/available here, and this workspace has no `.git` directory, so Git ignore behavior was not runtime-verified.
- Start/Stop recording with zero packets may still create a full-context draft run depending on `RecordingWorker.session_ready`; decide whether to require packet count > 0 before 1.0.
- Remaining legacy hard-coded/mojibake UI labels should be moved to dictionaries/DB labels.
- No real FH6 Data Out UDP recording was performed in this run.

## 10. Next Window Should Continue Here

Start with:

```text
reports/current_handoff_after_0_99_run.md
NEXT_STEPS.md
```

Then do:

1. Run `setup_windows.bat` from a clean clone on Windows 10/11.
2. Run `start_desktop.bat`.
3. Complete one real FH6 Data Out recording.
4. Confirm the saved Run appears in Run Library with car/build/tune/setup/route/type/tags.
5. Fix any runtime/UI issues found during that manual workflow.

## 11. Do Not Do

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
create orphan runs
```
