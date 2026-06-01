from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from fh6_tuning_sim.db.migrations import foreign_key_check, init_schema
from fh6_tuning_sim.db.repositories import (
    BuildRepository,
    CarRepository,
    ExperimentRepository,
    RouteRepository,
    RunRepository,
    SetupSnapshotRepository,
    TagRepository,
    TuneRepository,
    UpgradeStoreRepository,
)
from fh6_tuning_sim.db.seed_data.demo_seed import seed_demo_database
from fh6_tuning_sim.db.seed_data.seed_upgrade_templates import seed_upgrade_templates


class TestSQLiteRepositories(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "repo.db"
        seed_demo_database(self.db_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_archive_car_build_tune_snapshot(self) -> None:
        cars = CarRepository(self.db_path)
        builds = BuildRepository(self.db_path)
        tunes = TuneRepository(self.db_path)
        snapshots = SetupSnapshotRepository(self.db_path)

        car = cars.create_car({"car_id": "car_repo_test", "display_name": "Repo Test Car", "drivetrain": "RWD"})
        build = builds.ensure_default_stock_build(car["car_id"])
        tune = tunes.ensure_baseline_tune(build["build_id"])
        setup = snapshots.ensure_default_setup_snapshot(car["car_id"], build["build_id"], tune["tune_id"])

        self.assertTrue(snapshots.validate_context(car["car_id"], build["build_id"], tune["tune_id"], setup["setup_snapshot_id"]))
        self.assertTrue(cars.archive_car(car["car_id"]))
        self.assertEqual(cars.get_car(car["car_id"])["status"], "archived")
        self.assertEqual(foreign_key_check(self.db_path), [])

    def test_run_repository_enforces_context_and_tags(self) -> None:
        tags = TagRepository(self.db_path)
        runs = RunRepository(self.db_path)

        created = runs.create_run(
            {
                "run_id": "repo_run_1",
                "session_id": "repo_run_1",
                "car_id": "car_demo_amg",
                "build_id": "build_amg_stock",
                "tune_id": "tune_amg_stock_baseline",
                "setup_snapshot_id": "setup_amg_stock_baseline",
                "route_id": "route_horizon_loop",
                "route_mode": "timed_route",
                "record_type": "full_lap",
                "notes": "repository smoke",
            },
            ["intent_tag__baseline"],
        )
        self.assertEqual(created["run_id"], "repo_run_1")
        filtered = runs.query_run_records(car_id="car_demo_amg", tag_id="intent_tag__baseline", keyword="smoke")
        self.assertEqual([item["run_id"] for item in filtered], ["repo_run_1"])
        self.assertTrue(runs.update_run_notes("repo_run_1", "updated notes"))
        self.assertTrue(runs.add_tag_to_run("repo_run_1", "general_tag__needs_review"))
        self.assertTrue(runs.remove_tag_from_run("repo_run_1", "general_tag__needs_review"))
        self.assertTrue(runs.archive_run("repo_run_1"))
        self.assertEqual(runs.query_run_records(keyword="updated notes"), [])
        self.assertEqual(len(runs.query_run_records(keyword="updated notes", include_archived=True)), 1)

        with self.assertRaises(ValueError):
            runs.create_run(
                {
                    "run_id": "repo_run_bad",
                    "session_id": "repo_run_bad",
                    "car_id": "car_demo_amg",
                    "build_id": "build_amg_stage2",
                    "tune_id": "tune_amg_stock_baseline",
                    "setup_snapshot_id": "setup_amg_stock_baseline",
                    "route_mode": "timed_route",
                    "record_type": "full_lap",
                },
                ["intent_tag__baseline"],
            )
        no_tag_run = runs.create_run(
            {
                "run_id": "repo_run_no_tags",
                "session_id": "repo_run_no_tags",
                "car_id": "car_demo_amg",
                "build_id": "build_amg_stock",
                "tune_id": "tune_amg_stock_baseline",
                "setup_snapshot_id": "setup_amg_stock_baseline",
                "route_mode": "timed_route",
                "record_type": "full_lap",
            },
            [],
        )
        self.assertEqual(no_tag_run["run_id"], "repo_run_no_tags")

        self.assertIsNotNone(tags.tag_id_for_key("baseline", "intent_tag"))
        self.assertEqual(foreign_key_check(self.db_path), [])

    def test_upgrade_store_persists_one_option_per_slot(self) -> None:
        seed_upgrade_templates(self.db_path)
        upgrades = UpgradeStoreRepository(self.db_path)

        engine = next(item for item in upgrades.list_categories() if item["category_key"] == "engine")
        intake = next(item for item in upgrades.list_slots(engine["upgrade_category_id"], "build_amg_stock") if item["slot_key"] == "intake")
        options = upgrades.list_options(intake["slot_id"], "build_amg_stock")
        race_intake = next(item for item in options if item["option_key"] == "intake_race")
        saved = upgrades.save_build_upgrade_selection("build_amg_stock", intake["slot_id"], race_intake["upgrade_option_id"])

        self.assertEqual(saved["slot_id"], intake["slot_id"])
        self.assertEqual(saved["option_label"], "赛车版进气系统")
        reloaded = upgrades.get_selection("build_amg_stock", intake["slot_id"])
        self.assertEqual(reloaded["upgrade_option_id"], race_intake["upgrade_option_id"])

        flywheel = next(item for item in upgrades.list_slots(engine["upgrade_category_id"], "build_amg_stock") if item["slot_key"] == "flywheel")
        with self.assertRaises(ValueError):
            upgrades.save_build_upgrade_selection("build_amg_stock", flywheel["slot_id"], race_intake["upgrade_option_id"])

    def test_routes_tags_and_experiment_placeholder(self) -> None:
        routes = RouteRepository(self.db_path)
        tags = TagRepository(self.db_path)
        experiments = ExperimentRepository(self.db_path)

        route = routes.create_route({"display_name": "Repo Route", "route_mode": "timed_route"})
        self.assertEqual(route["display_name"], "Repo Route")
        tag = tags.create_tag("intent_tag", "repo_tag", "仓库测试")
        self.assertEqual(tag["tag_id"], "intent_tag__repo_tag")
        self.assertTrue(tags.archive_tag(tag["tag_id"]))
        matrix = experiments.create_placeholder_matrix("car_demo_amg", "Repo Matrix")
        self.assertEqual(matrix["status"], "draft")

    def test_schema_only_database_supports_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "empty.db"
            init_schema(db_path)
            self.assertEqual(CarRepository(db_path).list_cars(), [])
            self.assertEqual(foreign_key_check(db_path), [])


if __name__ == "__main__":
    unittest.main()
