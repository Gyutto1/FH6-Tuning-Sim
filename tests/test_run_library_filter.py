import tempfile
import unittest
from pathlib import Path

from fh6_tuning_sim.db.seed_data.demo_seed import seed_demo_database
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService


class TestRunLibraryFilter(unittest.TestCase):
    """Test filter_run_records pure function."""

    def setUp(self):
        self.records = [
            {
                "run_id": "r1", "session_id": "s1",
                "display_title": "AMG GT · Route A · Lap",
                "car_id": "car_ordinal_4265", "car_name": "Mercedes-AMG GT",
                "route_mode": "timed_route", "route_name": "Route A",
                "record_type": "lap_recording", "record_type_label": "Lap",
                "tag_keys": ["baseline", "full_lap"],
                "tag_ids": ["intent_tag__baseline", "intent_tag__full_lap"],
                "tag_labels": ["基准", "完整跑圈"],
                "quality_status": "good",
                "status": "active", "is_active": True,
                "search_text": "AMG GT Route A baseline full_lap",
                "duration_seconds": 12.3, "created_at": "2026-05-30",
                "notes": "test", "tune_name": "stock_default",
            },
            {
                "run_id": "r2", "session_id": "s2",
                "display_title": "AMG GT · Free · Free",
                "car_id": "car_ordinal_4265", "car_name": "Mercedes-AMG GT",
                "route_mode": "free_roam", "route_name": "Free",
                "record_type": "free_drive", "record_type_label": "Free",
                "tag_keys": ["normal_driving"],
                "tag_ids": ["intent_tag__normal_driving"],
                "tag_labels": ["正常驾驶"],
                "quality_status": "warning",
                "status": "active", "is_active": True,
                "search_text": "AMG GT Free normal_driving",
                "duration_seconds": 8.7, "created_at": "2026-05-29",
                "notes": "", "tune_name": "stock_default",
            },
            {
                "run_id": "r3", "session_id": "s3",
                "display_title": "demo · unset · Normal",
                "car_id": "car_demo_car", "car_name": "demo car",
                "route_mode": "unset", "route_name": "unknown",
                "record_type": "normal_recording", "record_type_label": "Normal",
                "tag_keys": [],
                "tag_ids": [],
                "tag_labels": [],
                "quality_status": "warning",
                "status": "archived", "is_active": False,
                "search_text": "demo unknown",
                "duration_seconds": 0, "created_at": "2026-05-28",
                "notes": "", "tune_name": "baseline_001",
            },
        ]

    def _filter(self, **kw):
        return DesktopDataService.filter_run_records(self.records, **kw)

    def test_filter_by_car_id(self):
        self.assertEqual(len(self._filter(car_id="car_ordinal_4265")), 2)

    def test_filter_by_route_timed(self):
        self.assertEqual(len(self._filter(route_mode="timed_route")), 1)

    def test_filter_by_route_unset(self):
        self.assertEqual(len(self._filter(route_mode="unset", include_archived=True)), 1)

    def test_filter_by_record_type(self):
        self.assertEqual(len(self._filter(record_type="lap_recording")), 1)

    def test_filter_by_single_tag(self):
        self.assertEqual(len(self._filter(tag_keys=["baseline"])), 1)

    def test_filter_by_multi_tag_and(self):
        self.assertEqual(len(self._filter(tag_keys=["baseline", "full_lap"])), 1)

    def test_filter_by_multi_tag_and_no_match(self):
        self.assertEqual(len(self._filter(tag_keys=["baseline", "normal_driving"])), 0)

    def test_filter_by_keyword(self):
        self.assertEqual(len(self._filter(keyword="baseline")), 1)

    def test_combo_filter(self):
        self.assertEqual(len(self._filter(car_id="car_ordinal_4265", route_mode="free_roam", record_type="free_drive")), 1)

    def test_empty_filter(self):
        self.assertEqual(len(self._filter()), 2)

    def test_include_archived_filter(self):
        self.assertEqual(len(self._filter(include_archived=True)), 3)

    def test_missing_fields_no_crash(self):
        bad_records = [{"run_id": "x"}]
        self.assertEqual(len(DesktopDataService.filter_run_records(bad_records, car_id="x")), 0)

    def test_quality_filter(self):
        self.assertEqual(len(self._filter(quality_status="good")), 1)

    def test_filter_by_tag_id(self):
        result = self._filter(tag_ids=["intent_tag__baseline"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["session_id"], "s1")


class TestRunMetadataUpdate(unittest.TestCase):
    """Test SQLite-backed CRUD: notes, tags, archive."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "desktop.db"
        seed_demo_database(self.db_path)
        self.ds = DesktopDataService(db_path=self.db_path)
        self.test_sid = "demo_run_10"

    def tearDown(self):
        self.tmp.cleanup()

    def test_update_notes(self):
        ok = self.ds.update_run_notes(self.test_sid, "CRUD test note")
        self.assertTrue(ok)
        runs = self.ds._load_runs()
        for run in runs:
            if run.get("session_id") == self.test_sid:
                self.assertEqual(run.get("notes"), "CRUD test note")

    def test_add_tag(self):
        ok = self.ds.add_tag_to_run(self.test_sid, "baseline")
        self.assertTrue(ok)
        runs = self.ds._load_runs()
        for run in runs:
            if run.get("session_id") == self.test_sid:
                self.assertIn("baseline", run.get("tags", []))

    def test_remove_tag(self):
        self.ds.add_user_tag("general_tag", "test_remove_me", "移除测试")
        self.ds.add_tag_to_run(self.test_sid, "test_remove_me")
        ok = self.ds.remove_tag_from_run(self.test_sid, "test_remove_me")
        self.assertTrue(ok)
        runs = self.ds._load_runs()
        for run in runs:
            if run.get("session_id") == self.test_sid:
                self.assertNotIn("test_remove_me", run.get("tags", []))

    def test_archive(self):
        ok = self.ds.archive_run(self.test_sid)
        self.assertTrue(ok)
        runs = self.ds._load_runs()
        for run in runs:
            if run.get("session_id") == self.test_sid:
                self.assertEqual(run.get("status"), "archived")

    def test_archived_not_in_list(self):
        self.ds.archive_run(self.test_sid)
        records = self.ds.list_run_records()
        sids = [record["session_id"] for record in records]
        self.assertNotIn(self.test_sid, sids)

    def test_tag_id_filter_and_chinese_label(self):
        self.assertTrue(self.ds.add_user_tag("general_tag", "cn_review", "中文复查"))
        self.assertTrue(self.ds.add_tag_to_run(self.test_sid, "cn_review"))
        records = self.ds.list_run_records()
        target = next(record for record in records if record["session_id"] == self.test_sid)
        self.assertIn("general_tag__cn_review", target.get("tag_ids", []))
        self.assertIn("中文复查", target.get("tag_labels", []))
        filtered = self.ds.filter_run_records(records, tag_ids=["general_tag__cn_review"])
        self.assertEqual([record["session_id"] for record in filtered], [self.test_sid])
        self.assertTrue(self.ds.remove_tag_id_from_run(self.test_sid, "general_tag__cn_review"))
        records = self.ds.list_run_records()
        self.assertEqual(self.ds.filter_run_records(records, tag_ids=["general_tag__cn_review"]), [])

    def test_setup_snapshot_update(self):
        ok = self.ds.update_setup_snapshot(
            "setup_amg_stage2",
            {
                "pi": 951,
                "car_class": "S1",
                "drivetrain": "AWD",
                "performance_ratings": {"speed": 8.1, "handling": 7.9},
            },
        )
        self.assertTrue(ok)
        snapshots = self.ds.list_setup_snapshots_for_tune("tune_amg_stage2_baseline")
        updated = next(item for item in snapshots if item["setup_snapshot_id"] == "setup_amg_stage2")
        self.assertEqual(updated["pi"], 951)

    def test_tune_parameter_placeholder_and_save(self):
        self.assertEqual(self.ds.list_tune_parameter_definitions(), [])
        self.assertEqual(self.ds.list_tune_parameter_values("tune_amg_stage2_baseline"), [])
        from fh6_tuning_sim.db.connection import transaction

        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tune_parameter_definitions (
                    tune_parameter_id, parameter_key, category, label_zh, unit,
                    min_value, max_value, step, value_type, description, is_enabled, display_order
                ) VALUES ('param_tire_pressure_front', 'tire_pressure_front', 'tires', '前胎压', 'psi', 15, 55, 0.5, 'float', '', 1, 1)
                """
            )
        values = self.ds.list_tune_parameter_values("tune_amg_stage2_baseline")
        self.assertEqual(values[0]["label_zh"], "前胎压")
        self.assertTrue(self.ds.save_tune_parameter_values("tune_amg_stage2_baseline", [{"tune_parameter_id": "param_tire_pressure_front", "value_real": 28.5, "value_text": "28.5"}]))
        values = self.ds.list_tune_parameter_values("tune_amg_stage2_baseline")
        self.assertEqual(values[0]["value_real"], 28.5)


if __name__ == "__main__":
    unittest.main()
