from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from fh6_tuning_sim.analysis.feature_engineering import add_time_lap_state_features


DRIVETRAIN_TYPE_MAP = {
    0: "FWD",
    1: "RWD",
    2: "AWD",
}


def _num(frame: pd.DataFrame, name: str, default: float = 0.0) -> pd.Series:
    if name not in frame:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[name], errors="coerce")


def _count_sum(frame: pd.DataFrame, columns: list[str]) -> int:
    available = [column for column in columns if column in frame]
    if not available:
        return 0
    return int(frame[available].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum())


def _mode_value(frame: pd.DataFrame, column: str, *, ignore_zero: bool = False) -> Any:
    if column not in frame:
        return None
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if ignore_zero and (series != 0).any():
        series = series[series != 0]
    if series.empty:
        return None
    modes = series.mode()
    value = modes.iloc[0] if not modes.empty else series.iloc[-1]
    if float(value).is_integer():
        return int(value)
    return float(value)


def _is_known(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return bool(text) and text not in {"unknown", "none", "null", "未填写", "未设置"}


def _lap_summaries(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if "detected_lap_id" not in frame:
        return []
    summaries: list[dict[str, Any]] = []
    for lap_id, lap_frame in frame.groupby("detected_lap_id", sort=True):
        elapsed = _num(lap_frame, "session_elapsed_seconds")
        lap_elapsed = _num(lap_frame, "detected_lap_elapsed_seconds")
        lap_number = _mode_value(lap_frame, "lap_number_raw")
        summaries.append(
            {
                "detected_lap_id": int(lap_id),
                "lap_number_raw": lap_number,
                "sample_count": int(len(lap_frame)),
                "session_start_seconds": round(float(elapsed.min()), 3) if not elapsed.empty else 0.0,
                "session_end_seconds": round(float(elapsed.max()), 3) if not elapsed.empty else 0.0,
                "duration_seconds": round(float(lap_elapsed.max()), 3) if not lap_elapsed.empty else 0.0,
            }
        )
    return summaries


def _state_tag_counts(frame: pd.DataFrame) -> dict[str, int]:
    mapping = {
        "idle": "state_idle",
        "stopped": "state_stopped",
        "possible_pause": "state_possible_pause",
        "recording_gap": "state_recording_gap",
        "menu_or_no_data": "state_menu_or_no_data",
    }
    counts: dict[str, int] = {}
    for tag, column in mapping.items():
        if column in frame:
            counts[tag] = int(frame[column].fillna(False).astype(bool).sum())
    return counts


def extract_telemetry_identity(frame: pd.DataFrame) -> dict[str, Any]:
    identity_frame = frame
    if {"is_race_on", "speed"}.issubset(frame.columns):
        active = frame[
            (_num(frame, "is_race_on").fillna(0) > 0)
            & (_num(frame, "speed").fillna(0) > 0.5)
        ]
        if not active.empty:
            identity_frame = active

    drivetrain_type = _mode_value(identity_frame, "drivetrain_type", ignore_zero=True)
    return {
        "detected_car_ordinal": _mode_value(identity_frame, "car_ordinal", ignore_zero=True),
        "detected_car_class": _mode_value(identity_frame, "car_class", ignore_zero=True),
        "detected_performance_index": _mode_value(identity_frame, "car_performance_index", ignore_zero=True),
        "detected_drivetrain_type": drivetrain_type,
        "detected_drivetrain": DRIVETRAIN_TYPE_MAP.get(drivetrain_type),
        "detected_num_cylinders": _mode_value(identity_frame, "num_cylinders", ignore_zero=True),
        "detected_car_group": _mode_value(identity_frame, "car_group", ignore_zero=True),
    }


def compute_data_quality(frame: pd.DataFrame) -> dict[str, Any]:
    frame = add_time_lap_state_features(frame)
    packet_count = int(len(frame))
    if packet_count == 0:
        return {
            "packet_count": 0,
            "duration_seconds": 0.0,
            "estimated_sample_rate": 0.0,
            "run_quality_score": 0,
            "data_integrity_score": 0,
            "quality_status": "bad",
            "quality_warnings": ["packet_count is 0"],
        }

    timestamp = _num(frame, "timestamp_ms").dropna()
    session_elapsed = _num(frame, "session_elapsed_seconds").dropna()
    if not timestamp.empty:
        timestamp_start = float(timestamp.min())
        timestamp_end = float(timestamp.max())
        gaps = timestamp.sort_values().diff().dropna()
    else:
        timestamp_start = None
        timestamp_end = None
        gaps = pd.Series(dtype="float64")

    duration_seconds = (
        max(float(session_elapsed.max() - session_elapsed.min()), 0.0)
        if not session_elapsed.empty
        else 0.0
    )
    estimated_sample_rate = packet_count / duration_seconds if duration_seconds > 0 else 0.0
    timestamp_gap_mean = float(gaps.mean()) if not gaps.empty else 0.0
    timestamp_gap_max = float(gaps.max()) if not gaps.empty else 0.0
    large_gap_count = int((gaps > 250.0).sum()) if not gaps.empty else 0

    is_race_on = _num(frame, "is_race_on")
    speed = _num(frame, "speed")
    missing_value_count = int(frame.isna().sum().sum())

    suspension_columns = [
        "normalized_suspension_travel_front_left",
        "normalized_suspension_travel_front_right",
        "normalized_suspension_travel_rear_left",
        "normalized_suspension_travel_rear_right",
    ]
    suspension_bottoming_count = 0
    existing_suspension = [column for column in suspension_columns if column in frame]
    if existing_suspension:
        suspension_bottoming_count = int(
            (
                frame[existing_suspension]
                .apply(pd.to_numeric, errors="coerce")
                .fillna(0)
                .max(axis=1)
                > 0.92
            ).sum()
        )

    smashable_event_count = int((_num(frame, "smashable_vel_diff").fillna(0).abs() > 0.1).sum())
    rumble_strip_event_count = _count_sum(
        frame,
        [
            "wheel_on_rumble_strip_front_left",
            "wheel_on_rumble_strip_front_right",
            "wheel_on_rumble_strip_rear_left",
            "wheel_on_rumble_strip_rear_right",
        ],
    )
    puddle_event_count = _count_sum(
        frame,
        [
            "wheel_in_puddle_front_left",
            "wheel_in_puddle_front_right",
            "wheel_in_puddle_rear_left",
            "wheel_in_puddle_rear_right",
        ],
    )

    speed_valid = speed.dropna()
    speed_valid_ratio = float(speed_valid.size / packet_count)
    zero_speed_ratio = float((speed.fillna(0) <= 0.1).sum() / packet_count)
    is_race_on_ratio = float((is_race_on.fillna(0) > 0).sum() / packet_count)

    warnings: list[str] = []
    data_integrity_score = 100.0

    if duration_seconds < 15:
        warnings.append("duration is short")
        data_integrity_score -= 15
    if estimated_sample_rate and estimated_sample_rate < 20:
        warnings.append("estimated sample rate is low")
        data_integrity_score -= 20
    if large_gap_count > max(3, packet_count * 0.01):
        warnings.append("large timestamp gaps detected")
        data_integrity_score -= 20
    if speed_valid_ratio < 0.98:
        warnings.append("speed has missing/invalid values")
        data_integrity_score -= 15
    if missing_value_count > packet_count * 5:
        warnings.append("many missing values")
        data_integrity_score -= 20

    detected_lap_count = int(frame["detected_lap_id"].nunique()) if "detected_lap_id" in frame else 0
    detected_lap_reset_count = int(frame.get("detected_lap_reset", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
    state_tag_counts = _state_tag_counts(frame)
    unmarked_pause_samples = state_tag_counts.get("possible_pause", 0) + state_tag_counts.get("recording_gap", 0)
    if unmarked_pause_samples > max(10, packet_count * 0.05):
        warnings.append("pause/gap state should be reviewed")
        data_integrity_score -= 10

    data_integrity_score = max(0.0, min(100.0, data_integrity_score))
    if packet_count == 0 or speed_valid_ratio < 0.5 or missing_value_count > packet_count * 20:
        status = "bad"
    elif data_integrity_score < 75 or warnings:
        status = "warning"
    else:
        status = "good"

    identity = extract_telemetry_identity(frame)

    return {
        "packet_count": packet_count,
        "duration_seconds": round(duration_seconds, 3),
        "estimated_sample_rate": round(estimated_sample_rate, 3),
        "timestamp_start": timestamp_start,
        "timestamp_end": timestamp_end,
        "timestamp_gap_mean": round(timestamp_gap_mean, 3),
        "timestamp_gap_max": round(timestamp_gap_max, 3),
        "large_gap_count": large_gap_count,
        "is_race_on_ratio": round(is_race_on_ratio, 4),
        "speed_valid_ratio": round(speed_valid_ratio, 4),
        "zero_speed_ratio": round(zero_speed_ratio, 4),
        "smashable_event_count": smashable_event_count,
        "rumble_strip_event_count": rumble_strip_event_count,
        "puddle_event_count": puddle_event_count,
        "suspension_bottoming_count": suspension_bottoming_count,
        "behavior_event_counts": {
            "smashable": smashable_event_count,
            "rumble_strip": rumble_strip_event_count,
            "puddle": puddle_event_count,
            "suspension_bottoming": suspension_bottoming_count,
        },
        "state_tag_counts": state_tag_counts,
        "detected_lap_count": detected_lap_count,
        "detected_lap_reset_count": detected_lap_reset_count,
        "lap_summaries": _lap_summaries(frame),
        "missing_value_count": missing_value_count,
        **identity,
        "data_integrity_score": round(data_integrity_score, 1),
        "run_quality_score": round(data_integrity_score, 1),
        "modeling_readiness_score": round(data_integrity_score, 1),
        "comparability_score": round(data_integrity_score, 1),
        "quality_status": status,
        "quality_warnings": warnings,
    }


def add_context_quality(
    quality: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
    tune: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    tune = tune or {}
    result = dict(quality)
    context_fields = {
        "vehicle": metadata.get("car_name") or tune.get("car_name") or result.get("detected_car_ordinal"),
        "tune": metadata.get("tune_name") or tune.get("tune_name"),
        "scenario": metadata.get("test_scenario"),
        "route": metadata.get("route_name"),
        "surface": metadata.get("surface_type"),
        "purpose_or_tags": metadata.get("purpose") or metadata.get("tags"),
    }
    known_count = sum(1 for value in context_fields.values() if _is_known(value) or (isinstance(value, list) and len(value) > 0))
    metadata_score = round(known_count / len(context_fields) * 100, 1)
    data_score = float(result.get("data_integrity_score", 0.0) or 0.0)

    comparability_score = round(data_score * 0.45 + metadata_score * 0.55, 1)
    modeling_readiness_score = round(data_score * 0.65 + metadata_score * 0.35, 1)
    run_quality_score = round(data_score * 0.55 + metadata_score * 0.45, 1)
    context_warnings = [
        field
        for field, value in context_fields.items()
        if not (_is_known(value) or (isinstance(value, list) and len(value) > 0))
    ]

    warnings = list(result.get("quality_warnings", []))
    if context_warnings:
        warnings.append("missing context: " + ", ".join(context_warnings))

    if run_quality_score < 45:
        status = "bad"
    elif run_quality_score < 75 or warnings:
        status = "warning"
    else:
        status = "good"

    result.update(
        {
            "metadata_completeness_score": metadata_score,
            "context_fields": context_fields,
            "missing_context_fields": context_warnings,
            "comparability_score": comparability_score,
            "modeling_readiness_score": modeling_readiness_score,
            "run_quality_score": run_quality_score,
            "quality_status": status,
            "quality_warnings": warnings,
            "quality_definition": (
                "质量表示数据是否有清楚上下文、能否被解释、能否比较、能否用于后续建模；"
                "推头、甩尾、打滑、失控属于行为标签，不是质量惩罚。"
            ),
        }
    )
    return result


def compute_data_quality_for_csv(path: str | Path) -> dict[str, Any]:
    frame = pd.read_csv(path)
    return compute_data_quality(frame)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check FH6 telemetry data quality.")
    parser.add_argument("input", help="Raw or processed telemetry CSV.")
    parser.add_argument("--output", help="Optional JSON output path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    quality = compute_data_quality_for_csv(args.input)
    payload = json.dumps(quality, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote quality JSON: {output}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
