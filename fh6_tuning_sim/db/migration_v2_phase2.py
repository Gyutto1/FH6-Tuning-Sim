from __future__ import annotations

from pathlib import Path
import shutil
from datetime import datetime, UTC

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect


def _backup_db(db_path: Path) -> Path | None:
    if not db_path.exists():
        return None
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = db_path.with_suffix(f'.bak.{ts}{db_path.suffix}')
    shutil.copy2(db_path, backup)
    return backup


def migrate_phase2(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    db_path = Path(db_path)

    from fh6_tuning_sim.db.migrations import init_schema
    from fh6_tuning_sim.db.migration_v2_phase1 import migrate_phase1
    migrate_phase1(db_path)

    conn = connect(db_path)
    try:
        cur = conn.execute('SELECT version FROM schema_version ORDER BY version DESC LIMIT 1')
        row = cur.fetchone()
        current_version = int(row['version']) if row else 2
        if current_version >= 3:
            return
    finally:
        conn.close()

    _backup_db(db_path)
    now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S+00:00')

    conn = connect(db_path)
    try:
        conn.execute('BEGIN')

        # New tables
        conn.execute('''CREATE TABLE IF NOT EXISTS upgrade_slots (
            slot_id TEXT PRIMARY KEY, upgrade_category_id TEXT NOT NULL,
            slot_key TEXT NOT NULL, label_zh TEXT NOT NULL, label_en TEXT,
            sort_order INTEGER DEFAULT 0, is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
            UNIQUE (upgrade_category_id, slot_key))''')

        conn.execute('''CREATE TABLE IF NOT EXISTS car_upgrade_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT, car_id TEXT NOT NULL,
            upgrade_category_id TEXT, slot_id TEXT, option_id TEXT,
            is_available INTEGER NOT NULL DEFAULT 1,
            override_label_zh TEXT, override_label_en TEXT,
            override_pi_delta INTEGER, notes TEXT,
            FOREIGN KEY (car_id) REFERENCES cars(car_id),
            FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
            FOREIGN KEY (slot_id) REFERENCES upgrade_slots(slot_id),
            FOREIGN KEY (option_id) REFERENCES upgrade_options(upgrade_option_id))''')

        conn.execute('''CREATE TABLE IF NOT EXISTS tune_sections (
            section_id TEXT PRIMARY KEY, section_key TEXT NOT NULL UNIQUE,
            label_zh TEXT NOT NULL, label_en TEXT, description TEXT,
            sort_order INTEGER DEFAULT 0, is_active INTEGER NOT NULL DEFAULT 1)''')

        conn.execute('''CREATE TABLE IF NOT EXISTS car_tune_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT, car_id TEXT NOT NULL,
            build_id TEXT, section_id TEXT, parameter_id TEXT,
            is_available INTEGER NOT NULL DEFAULT 1,
            override_min_value REAL, override_max_value REAL,
            override_step REAL, override_unit TEXT,
            override_default_value REAL, notes TEXT,
            FOREIGN KEY (car_id) REFERENCES cars(car_id),
            FOREIGN KEY (build_id) REFERENCES builds(build_id),
            FOREIGN KEY (section_id) REFERENCES tune_sections(section_id),
            FOREIGN KEY (parameter_id) REFERENCES tune_parameter_definitions(tune_parameter_id))''')

        conn.execute('''CREATE TABLE IF NOT EXISTS snapshot_build_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id TEXT NOT NULL,
            category_label_zh TEXT, slot_label_zh TEXT, option_label_zh TEXT,
            pi_delta INTEGER, unit TEXT, sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (snapshot_id) REFERENCES setup_snapshots(setup_snapshot_id))''')

        conn.execute('''CREATE TABLE IF NOT EXISTS snapshot_tune_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id TEXT NOT NULL,
            section_label_zh TEXT, parameter_label_zh TEXT,
            value REAL, unit TEXT, sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (snapshot_id) REFERENCES setup_snapshots(setup_snapshot_id))''')

        conn.execute('''CREATE TABLE IF NOT EXISTS snapshot_vehicle_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id TEXT NOT NULL,
            data_key TEXT NOT NULL, label_zh TEXT, value TEXT, unit TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (snapshot_id) REFERENCES setup_snapshots(setup_snapshot_id))''')

        # ALTER existing tables - safe (ignore if column exists)
        safe_alters = [
            'ALTER TABLE builds ADD COLUMN pi INTEGER',
            'ALTER TABLE builds ADD COLUMN car_class TEXT',
            'ALTER TABLE builds ADD COLUMN pi_source TEXT DEFAULT "manual_total"',
            'ALTER TABLE setup_snapshots ADD COLUMN confirmed_pi INTEGER',
            'ALTER TABLE setup_snapshots ADD COLUMN confirmed_class TEXT',
            'ALTER TABLE setup_snapshots ADD COLUMN frozen_summary_json TEXT',
            'ALTER TABLE setup_snapshots ADD COLUMN confirmed_at TEXT',
            'ALTER TABLE setup_snapshots ADD COLUMN is_current INTEGER DEFAULT 0',
            'ALTER TABLE tune_parameter_definitions ADD COLUMN section_id TEXT REFERENCES tune_sections(section_id)',
            'ALTER TABLE tune_parameter_definitions ADD COLUMN display_type TEXT DEFAULT "slider"',
            'ALTER TABLE tune_parameter_definitions ADD COLUMN side TEXT',
            'ALTER TABLE tune_parameter_definitions ADD COLUMN unlock_condition TEXT',
            'ALTER TABLE upgrade_options ADD COLUMN default_pi_delta INTEGER',
            'ALTER TABLE upgrade_options ADD COLUMN unlock_tune_sections TEXT',
            'ALTER TABLE upgrade_options ADD COLUMN tier INTEGER DEFAULT 0',
        ]
        for stmt in safe_alters:
            try:
                conn.execute(stmt)
            except Exception:
                pass

        # PI migration
        conn.execute('''UPDATE builds SET pi = (
            SELECT c.default_pi FROM cars c WHERE c.car_id = builds.car_id
        ), pi_source = "manual_total"
        WHERE builds.pi IS NULL AND builds.build_key = "default_stock_build"''')

        conn.execute(
            'INSERT OR IGNORE INTO schema_version (version, name, applied_at_utc) VALUES (?, ?, ?)',
            (3, 'v1_0_phase2_full_schema', now),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Indices
    conn = connect(db_path)
    try:
        conn.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_freeze ON snapshot_build_items(snapshot_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_tune_values_sid ON snapshot_tune_values(snapshot_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_vehicle_data_sid ON snapshot_vehicle_data(snapshot_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_car_upgrade_avail_car ON car_upgrade_availability(car_id)')
        conn.commit()
    finally:
        conn.close()


if __name__ == '__main__':
    migrate_phase2()
    print('Phase 2 migration complete (version 3).')
