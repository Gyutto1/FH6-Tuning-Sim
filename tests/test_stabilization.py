import tempfile
import unittest
from pathlib import Path

from fh6_tuning_sim.data_management.integrity import check_data_integrity, write_data_integrity_report
from fh6_tuning_sim.data_management.json_store import safe_load_json, safe_save_json
from fh6_tuning_sim.data_management.route_profile import route_survey_readiness


class StabilizationTests(unittest.TestCase):
    def test_safe_json_helpers_handle_missing_empty_and_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            default = {"items": []}

            missing = safe_load_json(root / "missing.json", default)
            self.assertEqual(missing, default)
            self.assertIsNot(missing, default)

            empty_path = root / "empty.json"
            empty_path.write_text("", encoding="utf-8")
            self.assertEqual(safe_load_json(empty_path, default), default)

            invalid_path = root / "invalid.json"
            invalid_path.write_text("{bad json", encoding="utf-8")
            self.assertEqual(safe_load_json(invalid_path, default), default)

            saved_path = root / "nested" / "data.json"
            safe_save_json(saved_path, {"items": [{"key": "ok"}]})
            self.assertEqual(safe_load_json(saved_path, default)["items"][0]["key"], "ok")

    def test_route_survey_readiness_thresholds(self) -> None:
        route_name = "horizon_highway_loop"

        not_started = route_survey_readiness(route_name, [])
        self.assertEqual(not_started["status_key"], "not_started")
        self.assertFalse(not_started["can_generate_draft"])

        draft_runs = (
            [{"session_id": f"left_{idx}", "route_name": route_name, "run_type": "track_boundary_survey", "survey_type": "left_boundary"} for idx in range(3)]
            + [{"session_id": f"right_{idx}", "route_name": route_name, "run_type": "track_boundary_survey", "survey_type": "right_boundary"} for idx in range(3)]
            + [{"session_id": "ref_0", "route_name": route_name, "run_type": "track_boundary_survey", "survey_type": "reference_line"}]
        )
        draft = route_survey_readiness(route_name, draft_runs)
        self.assertEqual(draft["status_key"], "draft_available")
        self.assertTrue(draft["can_generate_draft"])
        self.assertEqual(draft["survey_counts"]["left_boundary"], 3)

        complete_runs = draft_runs + (
            [{"session_id": f"left_more_{idx}", "route_name": route_name, "run_type": "track_boundary_survey", "survey_type": "left_boundary"} for idx in range(2)]
            + [{"session_id": f"right_more_{idx}", "route_name": route_name, "run_type": "track_boundary_survey", "survey_type": "right_boundary"} for idx in range(2)]
            + [{"session_id": f"ref_more_{idx}", "route_name": route_name, "run_type": "track_boundary_survey", "survey_type": "reference_line"} for idx in range(2)]
        )
        complete = route_survey_readiness(route_name, complete_runs)
        self.assertEqual(complete["status_key"], "complete_enough")
        self.assertTrue(complete["is_complete_enough"])

    def test_integrity_check_reports_warnings_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_dir = root / "data" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "run_1.csv").write_text("timestamp_ms,speed\n0,1\n", encoding="utf-8")

            platform = {
                "cars": [
                    {
                        "car_id": "car_1",
                        "tune_versions": [{"tune_id": "tune_1"}],
                        "dataset_groups": [{"dataset_group_id": "group_1"}],
                    }
                ]
            }
            runs = [
                {
                    "session_id": "run_1",
                    "car_id": "car_1",
                    "tune_id": "tune_1",
                    "dataset_group_id": "group_1",
                    "route_name": "horizon_highway_loop",
                    "raw_csv_path": "data/raw/run_1.csv",
                },
                {
                    "session_id": "run_2",
                    "car_id": "missing_car",
                    "route_name": "missing_route",
                    "raw_csv_path": "data/raw/missing.csv",
                },
            ]
            annotations = [
                {
                    "annotation_id": "ann_1",
                    "target_type": "run",
                    "target_id": "missing_run",
                    "run_id": "missing_run",
                    "tag_ids": ["not_a_valid_tag"],
                }
            ]
            route_profiles = [
                {
                    "profile_id": "profile_1",
                    "route_name": "horizon_highway_loop",
                    "source_session_id": "missing_survey",
                    "source_survey_runs": {"left_boundary_run_ids": ["missing_survey"]},
                }
            ]

            result = check_data_integrity(
                runs=runs,
                platform=platform,
                annotations=annotations,
                route_profiles=route_profiles,
                root=root,
            )
            codes = {issue["code"] for issue in result["issues"]}
            self.assertIn("orphan_run_car", codes)
            self.assertIn("missing_raw_csv_file", codes)
            self.assertIn("invalid_run_route", codes)
            self.assertIn("invalid_tag_id", codes)
            self.assertIn("missing_route_profile_source_run", codes)

            report_path = write_data_integrity_report(result, root / "reports" / "integrity.md")
            self.assertTrue(report_path.exists())
            self.assertIn("Warnings", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
