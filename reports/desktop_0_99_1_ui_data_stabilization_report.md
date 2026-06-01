# Desktop 0.99.1 UI / Data Stabilization Report

Date: 2026-05-31

## Summary

Desktop v0.99.1 UI/data stabilization is implemented for the current coding run. The work stayed on the existing SQLite 0.99 beta foundation and did not redo schema, migration, UDP listener, packet parser, or raw telemetry.

## Subtask Status

| Subtask | Status | Notes |
| --- | --- | --- |
| A. Car / Build / Tune UI hierarchy | Complete | Car Detail has Build Cards; Build Detail and Tune Detail pages exist. |
| B. Record Run Wizard | Complete | Record Run is a 5-step wizard with the existing context validator as final gate. |
| C. Tune Parameter Editor | Complete for 0.99.1 | Uses existing definitions/values tables; shows placeholder when definitions are empty. |
| D. Setup Snapshot Editor | Complete for 0.99.1 | Existing snapshots can be edited/confirmed and saved. |
| E. Run Library layout/filter repair | Complete | Left sidebar filters and right result list implemented. |
| F. Tag consistency | Complete | tag_id filtering, label display, add/remove/bind test coverage added. |
| G. Distribution cleanup | Complete as local cleanup | `.gitignore` improved; Git validation still requires real checkout. |

## Validation

```text
.venv312\python.exe -m compileall fh6_tuning_sim tests
PASS

.venv312\python.exe -m unittest discover -s tests
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

## Remaining External Validation

- Windows 10/11 clean clone test.
- Real FH6 Data Out recording test.
- Git ignore verification with `git check-ignore`.

## Do Not Do

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
