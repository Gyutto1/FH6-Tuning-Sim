from __future__ import annotations

import argparse
from pathlib import Path

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, DEMO_DB_PATH
from fh6_tuning_sim.db.legacy_migration import migrate_legacy_json
from fh6_tuning_sim.db.migrations import foreign_key_check, init_schema
from fh6_tuning_sim.db.seed_data.demo_seed import seed_demo_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize FH6 Tuning Sim SQLite databases.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Primary database path.")
    parser.add_argument("--schema-only", action="store_true", help="Only initialize schema.")
    parser.add_argument("--legacy", action="store_true", help="Import existing legacy JSON indexes.")
    parser.add_argument("--demo", action="store_true", help="Create demo database.")
    parser.add_argument("--demo-db", default=str(DEMO_DB_PATH), help="Demo database path.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.legacy:
        result = migrate_legacy_json(db_path)
        print(f"Legacy migration complete: {result}")
    else:
        init_schema(db_path)
        print(f"Schema initialized: {db_path}")

    fk_errors = foreign_key_check(db_path)
    if fk_errors:
        print(f"Foreign key check failed: {fk_errors}")
        return 1

    if args.demo:
        counts = seed_demo_database(args.demo_db)
        print(f"Demo database initialized: {args.demo_db} {counts}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
