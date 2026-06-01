# FH6 Tuning Sim Project Status

Updated: 2026-05-31

## Current Version

Desktop v0.99.1 (PySide6 mainline)

## Current Mainline

```text
PySide6 Desktop + SQLite
Car -> Build -> Tune -> Setup Snapshot -> Run
```

## Available Now

- Car / Build / Tune navigation
- Upgrade Store slot-level selection
- Tune section parameter editing
- Setup Snapshot confirmation / freeze
- Record Run 5-step workflow
- Run Library filter / tag / archive
- Legacy CLI tooling preserved

## Recently Completed

- Archive cleanup and workspace governance baseline
- Reports and legacy Streamlit artifacts moved under `docs/archive/`
- Default doc entry narrowed to current docs
- Main dependencies cleaned for PySide6 mainline
- Upgrade/Record rewire package documented under `docs/current/`:
  - `upgrade_record_rewire_handoff.md`
  - `upgrade_record_rewire_requirement_matrix.md`
  - `upgrade_record_rewire_manual_checklist.md`
  - `upgrade_record_rewire_test_result_template.md`
  - `upgrade_record_rewire_sql_checks.sql`

## Known Issues

- Local `.venv` may fail Qt runtime load on some hosts.
- `.venv312` remains local fallback in this workspace.
- Some historical Chinese text encoding artifacts still exist in older files.

## Next

1. Windows + FH6 manual recording validation
2. Git environment validation in a shell with `git` available
3. Execute rewire checklist and fill evidence template (UI + SQL)
4. Continue desktop UX hardening toward 1.0

## Default Reading Rules

Read: `AI_READING_GUIDE.md` -> `README.md` -> `PROJECT_STATUS.md` -> `CURRENT_TASK.md` -> `docs/current/*`

Do not read by default: `docs/archive/`, legacy reports, backups, raw/processed data trees.
