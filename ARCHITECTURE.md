# FH6 Tuning Sim Architecture

Updated: 2026-05-31

## Overview

FH6 Tuning Sim is a vehicle-centered telemetry and tuning data platform.

```text
FH6 Data Out
  -> UDP receiver / packet parser
  -> raw CSV
  -> feature engineering / reports / plots
  -> SQLite storage
  -> PySide6 Desktop UI
```

Streamlit remains as a legacy/debug prototype.

## Primary Data Model

```text
Car
└── Build
    └── Tune
        └── Setup Snapshot
            └── Run
```

Meaning:

- Car: vehicle identity.
- Build: hardware/upgrade combination.
- Tune: tuning parameters under one Build.
- Setup Snapshot: final general/performance state after Build + Tune confirmation and before Recording.
- Run: one telemetry recording bound to a Setup Snapshot.

Every Run must have:

```text
car_id
build_id
tune_id
setup_snapshot_id
route_mode
record_type
intent tag
```

## Storage

Desktop 0.99 beta primary DB:

```text
data/fh6_tuning_sim.db
```

Demo DB:

```text
data/demo/fh6_demo.db
```

SQLite code:

```text
fh6_tuning_sim/db/
  schema.sql
  connection.py
  migrations.py
  legacy_migration.py
  init_db.py
  repositories/
  services/
  seed_data/
```

JSON files remain legacy/import/export sources:

```text
data/platform/platform_index.json
data/index/runs_index.json
data/index/tags.json
data/index/annotations.json
configs/dictionaries/
```

## UI Layer

PySide6 Desktop:

```text
fh6_tuning_sim/ui_desktop/
```

The UI talks to `DesktopDataService`, which talks to SQLite repositories. Pages must not write SQL directly.

## Recording

Desktop uses `RecordingWorker` in a QThread for minimal Start/Stop recording. Recording cannot start until context validation passes.

Protected modules:

```text
fh6_tuning_sim/receiver/packet_parser.py
fh6_tuning_sim/receiver/udp_listener.py
fh6_tuning_sim/receiver/raw_logger.py
```

Do not change packet parser behavior, UDP listener behavior, or raw telemetry schema for 0.99 / 1.0.
