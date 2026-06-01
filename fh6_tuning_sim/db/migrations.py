from __future__ import annotations

from importlib import resources
from pathlib import Path

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect

SCHEMA_PATH = Path(__file__).resolve().with_name("schema.sql")


def _read_schema_text() -> str:
    if SCHEMA_PATH.exists():
        return SCHEMA_PATH.read_text(encoding="utf-8")
    return resources.files("fh6_tuning_sim.db").joinpath("schema.sql").read_text(encoding="utf-8")


def init_schema(db_path: str | Path = DEFAULT_DB_PATH, *, run_migrations: bool = True) -> None:
    """Create the current SQLite schema idempotently."""
    schema = _read_schema_text()
    conn = connect(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
    if run_migrations:
        from fh6_tuning_sim.db.migration_v4_client_rewire import migrate_v4_client_rewire

        migrate_v4_client_rewire(db_path)


def schema_versions(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    conn = connect(db_path)
    try:
        rows = conn.execute("SELECT version, name, applied_at_utc FROM schema_version ORDER BY version").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def foreign_key_check(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    conn = connect(db_path)
    try:
        rows = conn.execute("PRAGMA foreign_key_check").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
