# Current Handoff After Desktop v0.99.1

Date: 2026-05-31

## 1. Current Stage / Subtask

Desktop v0.99.1 implementation is complete for the current coding run.

The A-G scope from the pasted brief has been implemented at the intended 0.99.1 level:

```text
A. Car / Build / Tune UI hierarchy
B. Record Run Wizard
C. Tune Parameter Editor
D. Setup Snapshot Editor
E. Run Library layout and filters
F. Tag consistency
G. Distribution cleanup
```

Manual Windows/Git/FH6 validation still remains before calling it real-world stable.

## 2. Completed Features

- Run Library now uses a left filter sidebar and right result list.
- Run Library tag filtering now uses `tag_id`.
- Run cards display tag `label_zh` with fallback available from tag metadata.
- Tag add/remove/bind/filter paths use SQLite `tags` / `run_tags`.
- Record Run is now a 5-step wizard.
- Record Run still uses the existing RecordingContextService final gate.
- Car Detail now shows Build Cards as first-class entry points.
- Build Detail page added.
- Tune Detail page added.
- Tune Parameter Editor placeholder/value framework added.
- Setup Snapshot editor/confirmation dialog added.
- DesktopDataService now exposes Build/Tune detail, Tune parameter, Setup Snapshot update, and tag-id filtering helpers.
- Repository layer gained TuneParameterRepository and SetupSnapshot update support.
- `.gitignore` keeps venv/raw/processed/cache/log/bak artifacts out of distribution.

## 3. Unfinished Features

- Real Windows 10/11 clone/install workflow still needs manual testing.
- Real FH6 Data Out capture was not performed in this run.
- `git check-ignore` was not run because `git` is unavailable in this workspace.
- The Tune Parameter Editor supports definitions and values, but the full FH tuning parameter catalog is not populated.
- Setup Snapshot Editor is functional for existing snapshots; richer creation flows can be improved later.
- Some older UI labels elsewhere in the app still contain mojibake; new v0.99.1 surfaces use normal Chinese labels.

## 4. Main Files Added Or Modified

Added:

- `fh6_tuning_sim/db/repositories/tune_parameter_repository.py`
- `fh6_tuning_sim/ui_desktop/pages/build_detail_page.py`
- `fh6_tuning_sim/ui_desktop/pages/tune_detail_page.py`
- `fh6_tuning_sim/ui_desktop/pages/setup_snapshot_edit_dialog.py`
- `fh6_tuning_sim/ui_desktop/pages/tune_parameter_editor.py`

Modified:

- `fh6_tuning_sim/db/repositories/__init__.py`
- `fh6_tuning_sim/db/repositories/build_repository.py`
- `fh6_tuning_sim/db/repositories/run_repository.py`
- `fh6_tuning_sim/db/repositories/setup_snapshot_repository.py`
- `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py`
- `fh6_tuning_sim/ui_desktop/pages/run_library_page.py`
- `fh6_tuning_sim/ui_desktop/pages/record_run_page.py`
- `fh6_tuning_sim/ui_desktop/pages/car_detail_page.py`
- `fh6_tuning_sim/ui_desktop/main_window.py`
- `tests/test_run_library_filter.py`
- `.gitignore`
- `README.md`
- `PROJECT_STATUS.md`
- `NEXT_STEPS.md`

## 5. SQLite / Repository Current State

- SQLite schema was not rebuilt.
- JSON migration was not redone.
- Existing 0.99 beta schema supports all new 0.99.1 UI work.
- Runs still require:

```text
car_id
build_id
tune_id
setup_snapshot_id
```

- New repository support:

```text
TuneParameterRepository.list_definitions()
TuneParameterRepository.list_values(tune_id)
TuneParameterRepository.save_values(tune_id, values)
SetupSnapshotRepository.update_snapshot()
BuildRepository.latest_build_snapshot()
BuildRepository.list_upgrade_selections()
```

## 6. PySide6 UI Current State

- MainWindow now includes Car Detail, Build Detail, Tune Detail, Record Run Wizard, Run Library, Tag Library, and Settings.
- Sidebar version label is now `v0.99.1`.
- Car Detail shows Build Cards.
- Build Detail shows Build Snapshot, Upgrade selections placeholder, Tunes, and Runs.
- Tune Detail shows metadata, Tune Parameter Editor, Setup Snapshots, and Runs.
- Record Run is a wizard with five steps.
- Run Library uses a left sidebar and right-side result list.

## 7. Car -> Build -> Tune -> Setup Snapshot -> Run Workflow Current State

- The workflow is visible in UI navigation:

```text
Car Detail -> Build Detail -> Tune Detail -> Setup Snapshot -> Run
```

- Record Run Wizard still requires complete context before Start.
- Setup Snapshot edits are saved to SQLite and remain selectable.
- No orphan run path was introduced.

## 8. Run Library Current State

- Layout is now:

```text
left filter sidebar + right result list
```

- Filters include:

```text
Car
Build
Tune
Setup Snapshot
Route Mode
Record Type
Quality
Tag
Keyword
Active / Archived
```

- Empty state is shown when no records match.
- Result list is independently scrollable.

## 9. Tag Add / Bind / Filter Current State

- Run Library tag filter uses `tag_id`.
- Run cards display Chinese tag labels from `label_zh`.
- Add/remove tag actions use `tag_id` through service helpers.
- Tests cover Chinese tag creation, binding, filtering, label exposure, and removal.

## 10. Record Run Wizard Current State

Steps:

```text
1. Select Build
2. Select/Edit Tune
3. Confirm/Edit Setup Snapshot
4. Route / Record Type / Intent Tags
5. Ready / Start Recording
```

Start Recording is enabled only when the existing validator accepts:

```text
car_id
build_id
tune_id
setup_snapshot_id
route_mode
record_type
intent_tags
```

RecordingWorker / QThread integration is preserved. UDP listener, packet parser, and raw telemetry schema were not changed.

## 11. Test Results

Executed with `.venv312\python.exe`:

```text
python -m compileall fh6_tuning_sim tests
PASS

python -m unittest discover -s tests
46 tests PASS

offscreen MainWindow -> Car -> Build -> Tune -> Record smoke
PASS

offscreen Record Run Wizard gate smoke
PASS

offscreen Run Library sidebar smoke
PASS

offscreen Setup Snapshot editor smoke
PASS

offscreen Tune Parameter Editor smoke
PASS
```

## 12. Known Issues

- `.venv` still cannot load `PySide6.QtWidgets`; `.venv312` remains the verified local environment.
- Real FH6 Data Out capture still needs manual validation.
- Git validation still needs a real Git checkout.
- Full tune parameter catalog is intentionally not populated.
- Some legacy pages still have mojibake labels.

## 13. Next Window Should Continue From

Start with:

```text
reports/current_handoff_after_0_99_1.md
NEXT_STEPS.md
```

Recommended next work:

```text
1. Run clean Windows 10/11 clone/install/start test.
2. Run one real FH6 Data Out recording.
3. Verify saved Run appears in Run Library with tag labels and full context.
4. Run git status/check-ignore in a real Git checkout.
5. Begin 1.0 workflow hardening.
```

## 14. Do Not Do

```text
AI training
world model training
reinforcement learning
automatic tune optimizer
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
