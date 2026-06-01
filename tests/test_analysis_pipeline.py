import unittest
from pathlib import Path
import tempfile

import pandas as pd

from fh6_tuning_sim.analysis.data_quality import compute_data_quality
from fh6_tuning_sim.analysis.diagnosis import run_diagnosis
from fh6_tuning_sim.analysis.feature_engineering import add_features, add_time_lap_state_features
from fh6_tuning_sim.data_management.annotation_store import annotations_for_target, upsert_annotation
from fh6_tuning_sim.data_management.route_profile import build_route_profile
from fh6_tuning_sim.models.dataset import build_windows


def make_understeer_frame(rows: int = 90) -> pd.DataFrame:
    samples = []
    for index in range(rows):
        samples.append(
            {
                "timestamp_ms": index * 16,
                "current_race_time": index * 0.016,
                "speed": 20.0,
                "accel": 200,
                "brake": 0,
                "clutch": 0,
                "hand_brake": 0,
                "steer": 70,
                "normalized_driving_line": 0,
                "normalized_ai_brake_difference": 0,
                "angular_velocity_y": 0.20,
                "acceleration_x": 6.0,
                "acceleration_z": 0.5,
                "tire_combined_slip_front_left": 0.95,
                "tire_combined_slip_front_right": 0.95,
                "tire_combined_slip_rear_left": 0.55,
                "tire_combined_slip_rear_right": 0.55,
                "tire_slip_ratio_front_left": 0.1,
                "tire_slip_ratio_front_right": 0.1,
                "tire_slip_ratio_rear_left": 0.1,
                "tire_slip_ratio_rear_right": 0.1,
                "tire_slip_angle_front_left": 0.2,
                "tire_slip_angle_front_right": 0.2,
                "tire_slip_angle_rear_left": 0.1,
                "tire_slip_angle_rear_right": 0.1,
                "normalized_suspension_travel_front_left": 0.5,
                "normalized_suspension_travel_front_right": 0.5,
                "normalized_suspension_travel_rear_left": 0.5,
                "normalized_suspension_travel_rear_right": 0.5,
            }
        )
    return pd.DataFrame(samples)


class AnalysisPipelineTests(unittest.TestCase):
    def test_understeer_rule_triggers_from_engineered_features(self) -> None:
        processed = add_features(make_understeer_frame())
        findings = run_diagnosis(processed, drivetrain="AWD")
        self.assertIn("understeer", {finding.code for finding in findings})

    def test_dataset_builder_shapes(self) -> None:
        processed = add_features(make_understeer_frame())
        x, y, input_columns, target_columns = build_windows(
            processed,
            past_samples=30,
            future_samples=6,
        )
        self.assertEqual(x.shape, (55, 30, len(input_columns)))
        self.assertEqual(y.shape, (55, len(target_columns)))

    def test_lap_detection_preserves_continuous_session_time(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "timestamp_ms": index * 1000,
                    "current_race_time": index,
                    "current_lap": lap_time,
                    "lap_number": lap_number,
                    "speed": 30.0,
                    "is_race_on": 1,
                }
                for index, (lap_time, lap_number) in enumerate(
                    [
                        (0.0, 1),
                        (1.0, 1),
                        (2.0, 1),
                        (10.0, 1),
                        (0.2, 2),
                        (1.2, 2),
                    ]
                )
            ]
        )

        processed = add_time_lap_state_features(frame)

        self.assertEqual(processed["detected_lap_id"].nunique(), 2)
        self.assertEqual(int(processed["detected_lap_reset"].sum()), 1)
        self.assertTrue(processed["session_elapsed_seconds"].is_monotonic_increasing)
        self.assertAlmostEqual(float(processed["session_elapsed_seconds"].iloc[-1]), 5.0)

    def test_behavior_events_are_not_quality_penalties(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "timestamp_ms": index * 16,
                    "current_race_time": index * 0.016,
                    "current_lap": index * 0.016,
                    "lap_number": 1,
                    "speed": 25.0,
                    "is_race_on": 1,
                    "smashable_vel_diff": 1.0,
                }
                for index in range(1200)
            ]
        )

        quality = compute_data_quality(frame)

        self.assertEqual(quality["quality_status"], "good")
        self.assertEqual(quality["behavior_event_counts"]["smashable"], 1200)
        self.assertFalse(
            any("smashable" in warning or "collision" in warning for warning in quality["quality_warnings"])
        )

    def test_route_profile_builds_from_measurement_lap(self) -> None:
        rows = []
        for index in range(160):
            rows.append(
                {
                    "timestamp_ms": index * 100,
                    "current_race_time": index * 0.1,
                    "current_lap": index * 0.1,
                    "lap_number": 1,
                    "sample_index": index,
                    "speed": 10.0,
                    "position_x": float(index),
                    "position_y": 2.0,
                    "position_z": 0.0,
                    "yaw": 0.0,
                    "pitch": 0.0,
                    "roll": 0.0,
                }
            )
        frame = pd.DataFrame(rows)

        profile = build_route_profile(
            frame,
            session_id="survey_run_001",
            route_name="test_route",
            run_type="track_boundary_survey",
            survey_type="right_boundary",
            car_id="car_test",
            tune_id="tune_test",
            dataset_group_id="group_test",
        )

        self.assertEqual(profile["route_id"], "route_test_route")
        self.assertEqual(profile["survey_type"], "right_boundary")
        self.assertEqual(profile["source_survey_runs"]["right_boundary_run_ids"], ["survey_run_001"])
        self.assertGreater(profile["route_length_m"], 100.0)
        self.assertTrue(profile["profile_quality_flags"]["has_position"])
        self.assertEqual(profile["point_count"], 160)

    def test_manual_review_annotations_are_separate_from_raw_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "annotations.json"
            annotation = upsert_annotation(
                target_type="run",
                target_id="run_001",
                tag_ids=["intentional_understeer", "understeer"],
                source="manual",
                note="driver feedback",
                run_id="run_001",
                path=index_path,
            )
            found = annotations_for_target("run", "run_001", path=index_path)

            self.assertEqual(annotation["source"], "manual")
            self.assertEqual(found[0]["tag_ids"], ["intentional_understeer", "understeer"])
            self.assertTrue(index_path.exists())


if __name__ == "__main__":
    unittest.main()
