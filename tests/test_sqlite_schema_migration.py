from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from fh6_tuning_sim.db.connection import connect
from fh6_tuning_sim.db.legacy_migration import migrate_legacy_json
from fh6_tuning_sim.db.migrations import foreign_key_check, init_schema
from fh6_tuning_sim.db.seed_data.demo_seed import seed_demo_database


class TestSQLiteSchemaMigration(unittest.TestCase):
    def test_schema_initializes_with_required_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "schema.db"
            init_schema(db_path)
            conn = connect(db_path)
            try:
                tables = {
                    row["name"]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
                }
            finally:
                conn.close()
            for table in {
                "cars",
                "builds",
                "build_snapshots",
                "upgrade_categories",
                "upgrade_options",
                "upgrade_slots",
                "car_upgrade_availability",
                "build_upgrade_selections",
                "upgrade_compatibility_rules",
                "tunes",
                "tune_parameter_definitions",
                "tune_parameter_values",
                "setup_snapshots",
                "routes",
                "runs",
                "tags",
                "run_tags",
                "annotations",
                "dataset_groups",
                "experiment_matrices",
                "experiment_variables",
                "experiment_tasks",
                "recording_sessions",
            }:
                self.assertIn(table, tables)
            self.assertEqual(foreign_key_check(db_path), [])
            conn = connect(db_path)
            try:
                option_cols = {row["name"] for row in conn.execute("PRAGMA table_info(upgrade_options)").fetchall()}
                selection_pk = [
                    row["name"]
                    for row in sorted(
                        conn.execute("PRAGMA table_info(build_upgrade_selections)").fetchall(),
                        key=lambda row: row["pk"],
                    )
                    if row["pk"]
                ]
                versions = [row["version"] for row in conn.execute("SELECT version FROM schema_version").fetchall()]
            finally:
                conn.close()
            self.assertIn("slot_id", option_cols)
            self.assertEqual(selection_pk, ["build_id", "slot_id"])
            self.assertIn(4, versions)

    def test_demo_seed_counts_and_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.db"
            counts = seed_demo_database(db_path)
            self.assertEqual(counts["cars"], 2)
            self.assertEqual(counts["builds"], 3)
            self.assertEqual(counts["tunes"], 4)
            self.assertEqual(counts["setup_snapshots"], 4)
            self.assertEqual(counts["routes"], 3)
            self.assertEqual(counts["runs"], 10)
            self.assertGreaterEqual(counts["tags"], 10)
            conn = connect(db_path)
            try:
                archived = conn.execute("SELECT COUNT(*) AS c FROM runs WHERE status = 'archived'").fetchone()["c"]
                free_drive = conn.execute("SELECT COUNT(*) AS c FROM runs WHERE route_mode = 'free_drive'").fetchone()["c"]
                unset_route = conn.execute("SELECT COUNT(*) AS c FROM runs WHERE route_mode = 'unset'").fetchone()["c"]
                orphan = conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM runs
                    WHERE car_id = '' OR build_id = '' OR tune_id = '' OR setup_snapshot_id = ''
                    """
                ).fetchone()["c"]
            finally:
                conn.close()
            self.assertEqual(archived, 1)
            self.assertGreaterEqual(free_drive, 1)
            self.assertGreaterEqual(unset_route, 1)
            self.assertEqual(orphan, 0)
            self.assertEqual(foreign_key_check(db_path), [])

    def test_legacy_migration_imports_existing_json_without_orphans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "legacy.db"
            result = migrate_legacy_json(db_path, backup_existing_db=False)
            self.assertGreaterEqual(result["counts"]["cars"], 2)
            self.assertGreaterEqual(result["counts"]["runs"], 4)
            self.assertGreaterEqual(result["counts"]["builds"], 2)
            self.assertGreaterEqual(result["counts"]["tunes"], 2)
            self.assertEqual(result["orphan_runs"], 0)
            self.assertEqual(result["foreign_key_check"], [])


if __name__ == "__main__":
    unittest.main()
