# Database Schema (Current)

Primary DB: `data/fh6_tuning_sim.db`

## Core Hierarchy Tables

- `cars`
- `builds`
- `tunes`
- `setup_snapshots`
- `runs`

Hierarchy rule:

```text
car_id -> build_id -> tune_id -> setup_snapshot_id -> run_id
```

## Upgrade Store

- `upgrade_categories`
- `upgrade_slots`
- `upgrade_options`
- `build_upgrade_selections`

Effective selection key:

```text
(build_id, slot_id)
```

`save_build_upgrade_selection` must validate option-slot match.

## Tune Parameters

- `tune_parameter_definitions`
- `tune_parameter_values`

## Tags / Context

- `tags`
- `run_tags`
- `annotation_tags`
- route / record-type / experiment placeholder tables

## Migrations

- `schema.sql`
- `migration_v2_phase1.py`
- `migration_v2_phase2.py`
- `migration_v4_client_rewire.py`

All schema changes must go through migration flow.
