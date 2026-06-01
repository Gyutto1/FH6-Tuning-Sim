from __future__ import annotations

from pathlib import Path
import shutil
from datetime import datetime, UTC

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect


OPTION_SLOT_BY_PREFIX = {
    "intake": "us_intake",
    "fuel": "us_fuel",
    "ignition": "us_ignition",
    "exhaust": "us_exhaust",
    "cam": "us_camshaft",
    "valves": "us_valves",
    "disp": "us_displacement",
    "pistons": "us_pistons",
    "turbo": "us_twin_turbo",
    "ic": "us_intercooler",
    "fly": "us_flywheel",
    "springs": "us_springs",
    "chassis": "us_chassis",
    "weight": "us_weight",
    "trans": "us_transmission",
    "diff": "us_differential",
    "tire": "us_tire_compound",
    "skirts": "us_side_skirts",
    "eswap": "us_engine_swap",
    "dswap": "us_drivetrain_swap",
}


def _backup_db(db_path: Path) -> Path | None:
    if not db_path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_suffix(f".bak.{ts}{db_path.suffix}")
    shutil.copy2(db_path, backup)
    return backup


def _columns(conn, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _pk_columns(conn, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(row["name"]) for row in sorted(rows, key=lambda row: int(row["pk"] or 0)) if row["pk"]]


def _infer_slot_id(option_key: str) -> str | None:
    for prefix, slot_id in OPTION_SLOT_BY_PREFIX.items():
        if option_key.startswith(prefix):
            return slot_id
    return None


def migrate_v4_client_rewire(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """v4: slot-level upgrade option and selection persistence for client menus."""
    db_path = Path(db_path)

    from fh6_tuning_sim.db.migration_v2_phase2 import migrate_phase2

    migrate_phase2(db_path)

    conn = connect(db_path)
    try:
        row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
        current_version = int(row["version"]) if row else 1
        if current_version >= 4:
            return
    finally:
        conn.close()

    _backup_db(db_path)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    conn = connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")

        if "slot_id" not in _columns(conn, "upgrade_options"):
            conn.execute("ALTER TABLE upgrade_options ADD COLUMN slot_id TEXT REFERENCES upgrade_slots(slot_id)")

        for option_key, slot_id in OPTION_SLOT_BY_PREFIX.items():
            conn.execute(
                """
                UPDATE upgrade_options
                SET slot_id = ?
                WHERE slot_id IS NULL AND option_key LIKE ?
                """,
                (slot_id, f"{option_key}%"),
            )

        conn.execute(
            """
            UPDATE upgrade_options
            SET slot_id = (
                SELECT cua.slot_id
                FROM car_upgrade_availability cua
                WHERE cua.option_id = upgrade_options.upgrade_option_id
                  AND cua.slot_id IS NOT NULL
                LIMIT 1
            )
            WHERE slot_id IS NULL
              AND EXISTS (
                SELECT 1
                FROM car_upgrade_availability cua
                WHERE cua.option_id = upgrade_options.upgrade_option_id
                  AND cua.slot_id IS NOT NULL
              )
            """
        )

        if "slot_id" not in _columns(conn, "build_upgrade_selections") or _pk_columns(conn, "build_upgrade_selections") != ["build_id", "slot_id"]:
            backup_table = "build_upgrade_selections_v3_backup"
            existing_backup = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (backup_table,),
            ).fetchone()
            if existing_backup is None:
                conn.execute(f"ALTER TABLE build_upgrade_selections RENAME TO {backup_table}")
            else:
                conn.execute("DROP TABLE build_upgrade_selections")

            conn.execute(
                """
                CREATE TABLE build_upgrade_selections (
                    build_id TEXT NOT NULL,
                    slot_id TEXT NOT NULL,
                    upgrade_category_id TEXT NOT NULL,
                    upgrade_option_id TEXT,
                    notes TEXT,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    PRIMARY KEY (build_id, slot_id),
                    FOREIGN KEY (build_id) REFERENCES builds(build_id),
                    FOREIGN KEY (slot_id) REFERENCES upgrade_slots(slot_id),
                    FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
                    FOREIGN KEY (upgrade_option_id) REFERENCES upgrade_options(upgrade_option_id)
                )
                """
            )

            source_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (backup_table,),
            ).fetchone()
            if source_exists:
                conn.execute(
                    f"""
                    INSERT OR IGNORE INTO build_upgrade_selections (
                        build_id, slot_id, upgrade_category_id, upgrade_option_id,
                        notes, created_at_utc, updated_at_utc
                    )
                    SELECT
                        old.build_id,
                        COALESCE(
                            o.slot_id,
                            (
                                SELECT s.slot_id
                                FROM upgrade_slots s
                                WHERE s.upgrade_category_id = old.upgrade_category_id
                                ORDER BY s.sort_order, s.slot_key
                                LIMIT 1
                            )
                        ) AS slot_id,
                        old.upgrade_category_id,
                        old.upgrade_option_id,
                        old.notes,
                        old.created_at_utc,
                        old.updated_at_utc
                    FROM {backup_table} old
                    LEFT JOIN upgrade_options o ON o.upgrade_option_id = old.upgrade_option_id
                    WHERE COALESCE(
                        o.slot_id,
                        (
                            SELECT s.slot_id
                            FROM upgrade_slots s
                            WHERE s.upgrade_category_id = old.upgrade_category_id
                            ORDER BY s.sort_order, s.slot_key
                            LIMIT 1
                        )
                    ) IS NOT NULL
                    """
                )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_upgrade_options_slot_id ON upgrade_options(slot_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_build_upgrade_selections_category ON build_upgrade_selections(upgrade_category_id)")
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version, name, applied_at_utc) VALUES (?, ?, ?)",
            (4, "v1_0_client_rewire_slot_upgrade_store", now),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


if __name__ == "__main__":
    migrate_v4_client_rewire()
    print("Client rewire migration complete (version 4).")
