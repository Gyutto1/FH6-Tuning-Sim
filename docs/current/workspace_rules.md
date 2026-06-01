# Workspace Rules

## Default Read Entry

Read in order:

1. `AI_READING_GUIDE.md`
2. `README.md`
3. `PROJECT_STATUS.md`
4. `CURRENT_TASK.md`
5. `docs/current/*`

## Default Do-Not-Read

- `docs/archive/`
- `_archive/`
- `old_versions/`
- `reports/old/`
- `logs/`
- `backup/`
- `data/raw/`
- `data/processed/`

## Extra Read Rule

Before opening extra files, explicitly list:

1. filename  
2. reason

Then read only the minimum needed set.

## Data Safety

- Never delete `data/fh6_tuning_sim.db`
- Keep latest 1-2 DB backup files
- Use archive/disable over hard-delete for user data records
