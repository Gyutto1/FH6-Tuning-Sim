from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from fh6_tuning_sim.db.services.recording_context_service import RecordingContextService
from fh6_tuning_sim.db.seed_data.demo_seed import seed_demo_database
from fh6_tuning_sim.ui_desktop.i18n.snapshot_labels import VEHICLE_DATA_FIELDS
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService


class TestRecordingContextService(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "recording_context.db"
        seed_demo_database(self.db_path)
        self.service = RecordingContextService(self.db_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_valid_context(self) -> None:
        result = self.service.validate(
            {
                "car_id": "car_demo_amg",
                "build_id": "build_amg_stock",
                "tune_id": "tune_amg_stock_baseline",
                "setup_snapshot_id": "setup_amg_stock_baseline",
                "route_mode": "timed_route",
                "record_type": "full_lap",
                "intent_tags": ["full_lap"],
            }
        )
        self.assertTrue(result.is_valid)
        self.assertEqual(result.missing, [])

    def test_missing_context(self) -> None:
        result = self.service.validate({"car_id": "car_demo_amg"})
        self.assertFalse(result.is_valid)
        self.assertIn("build_id", result.missing)
        self.assertIn("tune_id", result.missing)
        self.assertIn("setup_snapshot_id", result.missing)
        self.assertIn("route_mode", result.missing)
        self.assertIn("record_type", result.missing)
        self.assertNotIn("intent_tags", result.missing)

    def test_context_chain_must_match(self) -> None:
        result = self.service.validate(
            {
                "car_id": "car_demo_amg",
                "build_id": "build_amg_stage2",
                "tune_id": "tune_amg_stock_baseline",
                "setup_snapshot_id": "setup_amg_stock_baseline",
                "route_mode": "timed_route",
                "record_type": "full_lap",
                "intent_tags": [],
            }
        )
        self.assertFalse(result.is_valid)
        self.assertIn("context_chain", result.missing)

    def test_ensure_default_context(self) -> None:
        context = self.service.ensure_default_context("car_demo_amg")
        self.assertEqual(context["car_id"], "car_demo_amg")
        self.assertTrue(context["build_id"])
        self.assertTrue(context["tune_id"])
        self.assertTrue(context["setup_snapshot_id"])

    def test_desktop_service_creates_run_from_recording_context(self) -> None:
        desktop = DesktopDataService(db_path=self.db_path)
        run = desktop.create_run_from_recording(
            session_id="recording_context_run",
            csv_path=str(Path(self.tmp.name) / "recording_context_run.csv"),
            packet_count=12,
            duration_seconds=1.5,
            context={
                "car_id": "car_demo_amg",
                "build_id": "build_amg_stock",
                "tune_id": "tune_amg_stock_baseline",
                "setup_snapshot_id": "setup_amg_stock_baseline",
                "route_mode": "timed_route",
                "record_type": "full_lap",
                "intent_tags": [],
            },
        )
        self.assertEqual(run["run_id"], "recording_context_run")
        records = desktop.list_run_records()
        self.assertIn("recording_context_run", [record["run_id"] for record in records])

    def test_archive_build_with_related(self) -> None:
        desktop = DesktopDataService(db_path=self.db_path)
        desktop.create_run_from_recording(
            session_id="cascade_run",
            csv_path=str(Path(self.tmp.name) / "cascade_run.csv"),
            packet_count=3,
            duration_seconds=0.4,
            context={
                "car_id": "car_demo_amg",
                "build_id": "build_amg_stock",
                "tune_id": "tune_amg_stock_baseline",
                "setup_snapshot_id": "setup_amg_stock_baseline",
                "route_mode": "timed_route",
                "record_type": "full_lap",
                "intent_tags": [],
            },
        )
        ok, _ = desktop.archive_build_with_related("build_amg_stock")
        self.assertTrue(ok)
        build = desktop.builds.get_build("build_amg_stock")
        self.assertEqual(build.get("status"), "archived")
        records_active = desktop.list_run_records()
        self.assertNotIn("cascade_run", [record["run_id"] for record in records_active])

    def test_copy_snapshot_context(self) -> None:
        desktop = DesktopDataService(db_path=self.db_path)
        source_snapshot_id = "setup_amg_stock_baseline"
        desktop.snapshots.update_snapshot(source_snapshot_id, {"pi": 901, "car_class": "S2", "notes": "source"})
        desktop.confirm_setup_snapshot(
            source_snapshot_id,
            [{"data_key": "top_speed", "label_zh": "最高速度", "value": "321", "unit": "kph"}],
        )
        target = desktop.snapshots.ensure_default_setup_snapshot("car_demo_amg", "build_amg_stage2", "tune_amg_stage2_baseline")
        ok = desktop.copy_snapshot_context(source_snapshot_id, str(target.get("setup_snapshot_id") or ""))
        self.assertTrue(ok)
        copied = desktop.snapshots.get_snapshot(str(target.get("setup_snapshot_id") or ""))
        self.assertEqual(copied.get("pi"), 901)
        self.assertEqual(copied.get("car_class"), "S2")
        vehicle_data = desktop._freeze.get_vehicle_data(str(target.get("setup_snapshot_id") or ""))
        self.assertGreaterEqual(len(vehicle_data), 1)

    def test_snapshot_vehicle_data_status_complete_after_full_supplement(self) -> None:
        desktop = DesktopDataService(db_path=self.db_path)
        snapshot_id = "setup_amg_stock_baseline"
        vehicle_data = [
            {
                "data_key": key,
                "label_zh": label_zh,
                "value": "1",
                "unit": unit,
            }
            for label_zh, unit, key in VEHICLE_DATA_FIELDS
        ]
        desktop.confirm_setup_snapshot(snapshot_id, vehicle_data)
        status = desktop.snapshot_vehicle_data_status(snapshot_id)
        self.assertTrue(status["is_complete"])
        self.assertEqual(status["missing_keys"], [])
        self.assertEqual(status["saved_count"], status["required_count"])

    def test_count_runs_for_snapshot(self) -> None:
        desktop = DesktopDataService(db_path=self.db_path)
        snapshot_id = "setup_amg_stock_baseline"
        before = desktop.count_runs_for_snapshot(snapshot_id)
        desktop.create_run_from_recording(
            session_id="snapshot_count_run",
            csv_path=str(Path(self.tmp.name) / "snapshot_count_run.csv"),
            packet_count=2,
            duration_seconds=0.2,
            context={
                "car_id": "car_demo_amg",
                "build_id": "build_amg_stock",
                "tune_id": "tune_amg_stock_baseline",
                "setup_snapshot_id": snapshot_id,
                "route_mode": "timed_route",
                "record_type": "full_lap",
                "intent_tags": [],
            },
        )
        after = desktop.count_runs_for_snapshot(snapshot_id)
        self.assertEqual(after, before + 1)

    def test_recording_metrics_use_display_units(self) -> None:
        desktop = DesktopDataService(db_path=self.db_path)
        csv_path = Path(self.tmp.name) / "metrics_units.csv"
        csv_path.write_text(
            "speed,current_engine_rpm,power,torque,acceleration_x,acceleration_y,accel,brake\n"
            "10,3000,73549.875,250,9.80665,4.903325,128,64\n"
            "20,6000,147099.75,300,-4.903325,-2.4516625,255,0\n",
            encoding="utf-8",
        )
        run = desktop.create_run_from_recording(
            session_id="metrics_units_run",
            csv_path=str(csv_path),
            packet_count=2,
            duration_seconds=0.2,
            context={
                "car_id": "car_demo_amg",
                "build_id": "build_amg_stock",
                "tune_id": "tune_amg_stock_baseline",
                "setup_snapshot_id": "setup_amg_stock_baseline",
                "route_mode": "timed_route",
                "record_type": "full_lap",
                "intent_tags": [],
            },
        )
        metrics = json.loads(run["metrics_json"])
        self.assertEqual(metrics["metrics_units_version"], 2)
        self.assertAlmostEqual(metrics["max_speed_kph"], 72.0)
        self.assertAlmostEqual(metrics["avg_speed_kph"], 54.0)
        self.assertAlmostEqual(metrics["max_power_ps"], 200.0)
        self.assertAlmostEqual(metrics["max_longitudinal_g"], 1.0)
        self.assertAlmostEqual(metrics["max_lateral_g"], 0.5)


if __name__ == "__main__":
    unittest.main()
