# FH6 Tuning Sim Development Rules

This project is a vehicle-centered FH6 telemetry data platform, not only a recorder UI.

Current version: Desktop 0.99 beta implementation complete for current coding run; manual Windows validation remains before 1.0.

## Core Rules

- Keep the UI vehicle-centered using the Car -> Build -> Tune -> Setup Snapshot -> Run hierarchy.
- Do not hard-code user-facing labels. Use dictionaries and database-stored labels.
- Keep stable internal English keys; show Chinese labels in the default UI.
- Do not break existing CLI tools: UDP listener, feature engineering, plotting, reports, compare, dataset builder.
- Treat raw telemetry as the raw layer. Do not write manual labels or derived analysis into raw CSV.
- Data quality means context, interpretability, comparability, and modeling readiness.
- Do not penalize understeer, oversteer, wheelspin, crashes, or loss of control as quality by default.
- Never hard-delete data. Use archive / `is_active=false`.

## 0.99 Beta Rules

### Storage

- SQLite is the primary storage. JSON is import/export/legacy only.
- All writes must happen in transactions where repository methods create or update data.
- Foreign key constraints must be enforced.
- Every run must have `car_id`, `build_id`, `tune_id`, and `setup_snapshot_id`.
- No orphan runs are allowed.
- Schema changes must go through the migration system and `schema_version`.

### Data Model

- Car -> Build -> Tune -> Setup Snapshot -> Run hierarchy is mandatory.
- Build represents hardware/upgrade combinations.
- Tune represents tuning parameters within a Build.
- Setup Snapshot captures the final vehicle state after Build + Tune are confirmed but before Recording starts.
- Every Run must bind to a `setup_snapshot_id`.
- Tags, Routes, Datasets, Annotations, and Experiment Matrix placeholders live in SQLite.

### Recording

- RecordingController integration is allowed in 0.99 beta only after SQLite schema, migration, repositories, and context workflow exist.
- Recording must not start until Car, Build, Tune, Setup Snapshot, Route/Route Mode, Record Type, and at least one intent tag are selected.
- Use QThread + RecordingWorker for desktop recording. UI must not block.
- Do not modify packet parser behavior, UDP listener behavior, or raw telemetry schema.

### Upgrade Parts And Tune Parameters

- Table structures for `upgrade_categories`, `upgrade_options`, `build_upgrade_selections`, and compatibility placeholders must exist.
- Table structures for `tune_parameter_definitions` and `tune_parameter_values` must exist.
- Specific part names and parameter values can be empty initially.
- Users will fill upgrade and tuning dictionaries gradually from the game.

### Migration

- Existing JSON data must be migrated to SQLite by an idempotent script.
- Legacy JSON data must not be deleted.
- Generate `.bak.{timestamp}` backups before destructive operations.
- After migration, new desktop writes go directly to SQLite.

## Do

- Keep PySide6 Desktop runnable.
- Keep CLI tools compatible.
- Improve car-centered UX without rewriting the whole UI.
- Reduce UI information density where it improves workflow.
- Preserve raw telemetry.
- Prefer archive/disable over hard delete.
- Run tests after changes.
- Write reports for major iterations.
- Use SQLite transactions for writes.

## Do Not

- Implement AI training.
- Implement reinforcement learning.
- Implement automatic tune optimizer.
- Implement world-model training.
- Implement full Route Profile algorithms.
- Implement full lap simulation.
- Package an EXE.
- Modify packet parser behavior.
- Modify UDP listener behavior.
- Modify raw telemetry schema.
- Delete Streamlit.
- Rewrite the whole UI.
- Hard-code user-facing labels.
- Delete existing data/config files.
- Create orphan runs.
- Hard-delete data.
