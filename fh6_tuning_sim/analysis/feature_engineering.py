from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _num(frame: pd.DataFrame, name: str, default: float = 0.0) -> pd.Series:
    if name not in frame:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[name], errors="coerce").fillna(default)


def _avg(frame: pd.DataFrame, names: list[str]) -> pd.Series:
    return pd.concat([_num(frame, name) for name in names], axis=1).mean(axis=1)


def _abs_avg(frame: pd.DataFrame, names: list[str]) -> pd.Series:
    return pd.concat([_num(frame, name).abs() for name in names], axis=1).mean(axis=1)


def _raw_num(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame:
        return pd.Series(pd.NA, index=frame.index, dtype="Float64")
    return pd.to_numeric(frame[name], errors="coerce")


def _continuous_elapsed_seconds(frame: pd.DataFrame) -> pd.Series:
    timestamp_ms = _raw_num(frame, "timestamp_ms")
    race_time_ms = _raw_num(frame, "current_race_time") * 1000.0

    timestamp_diff = timestamp_ms.diff()
    race_time_diff = race_time_ms.diff()

    timestamp_usable = timestamp_diff.dropna().abs().sum() > 0
    base_diff = timestamp_diff if timestamp_usable else race_time_diff
    fallback_diff = race_time_diff if timestamp_usable else timestamp_diff

    # Preserve continuous session time while rejecting negative lap-time resets.
    dt_ms = base_diff.where((base_diff >= 0) & (base_diff <= 5000), fallback_diff)
    dt_ms = dt_ms.where((dt_ms >= 0) & (dt_ms <= 5000), 0).fillna(0)
    return dt_ms.cumsum() / 1000.0


def add_time_lap_state_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()

    data["sample_index"] = range(len(data))
    data["timestamp_ms_raw"] = _raw_num(data, "timestamp_ms")
    data["current_race_time_raw"] = _raw_num(data, "current_race_time")
    data["current_lap_raw"] = _raw_num(data, "current_lap")
    data["lap_number_raw"] = _raw_num(data, "lap_number")
    data["session_elapsed_seconds"] = _continuous_elapsed_seconds(data)

    current_lap = data["current_lap_raw"]
    lap_number = data["lap_number_raw"]
    lap_reset = (current_lap.shift(1) > 5.0) & (current_lap <= 3.0) & (current_lap.diff() < -2.0)
    lap_number_increase = lap_number.diff().fillna(0) > 0
    new_lap = (lap_reset | lap_number_increase).fillna(False)
    if not new_lap.empty:
        new_lap.iloc[0] = False
    data["detected_lap_id"] = new_lap.astype(int).cumsum() + 1
    lap_start_elapsed = data.groupby("detected_lap_id")["session_elapsed_seconds"].transform("first")
    data["detected_lap_elapsed_seconds"] = data["session_elapsed_seconds"] - lap_start_elapsed
    data["detected_lap_reset"] = new_lap

    speed = _num(data, "speed")
    is_race_on = _num(data, "is_race_on")
    dt = data["session_elapsed_seconds"].diff().fillna(0)
    stopped = speed <= 0.1
    recording_gap = dt > 0.25
    possible_pause = (dt > 2.0) | ((is_race_on <= 0) & stopped)
    menu_or_no_data = is_race_on <= 0

    data["state_idle"] = stopped & (is_race_on > 0)
    data["state_stopped"] = stopped
    data["state_possible_pause"] = possible_pause
    data["state_recording_gap"] = recording_gap
    data["state_menu_or_no_data"] = menu_or_no_data

    state_columns = [
        ("idle", "state_idle"),
        ("stopped", "state_stopped"),
        ("possible_pause", "state_possible_pause"),
        ("recording_gap", "state_recording_gap"),
        ("menu_or_no_data", "state_menu_or_no_data"),
    ]
    data["run_state_tags"] = [
        ",".join(tag for tag, column in state_columns if bool(data.at[index, column]))
        for index in data.index
    ]

    return data


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = add_time_lap_state_features(frame)

    data["speed_kmh"] = _num(data, "speed") * 3.6
    data["throttle_norm"] = _num(data, "accel") / 255.0
    data["brake_norm"] = _num(data, "brake") / 255.0
    data["clutch_norm"] = _num(data, "clutch") / 255.0
    data["handbrake_norm"] = _num(data, "hand_brake") / 255.0
    data["steer_norm"] = (_num(data, "steer") / 127.0).clip(-1.0, 1.0)
    data["driving_line_norm"] = (_num(data, "normalized_driving_line") / 127.0).clip(
        -1.0, 1.0
    )
    data["ai_brake_diff_norm"] = (
        _num(data, "normalized_ai_brake_difference") / 127.0
    ).clip(-1.0, 1.0)

    data["front_combined_slip_avg"] = _abs_avg(
        data,
        [
            "tire_combined_slip_front_left",
            "tire_combined_slip_front_right",
        ],
    )
    data["rear_combined_slip_avg"] = _abs_avg(
        data,
        [
            "tire_combined_slip_rear_left",
            "tire_combined_slip_rear_right",
        ],
    )
    data["front_slip_ratio_avg"] = _abs_avg(
        data,
        [
            "tire_slip_ratio_front_left",
            "tire_slip_ratio_front_right",
        ],
    )
    data["rear_slip_ratio_avg"] = _abs_avg(
        data,
        [
            "tire_slip_ratio_rear_left",
            "tire_slip_ratio_rear_right",
        ],
    )
    data["front_slip_angle_avg"] = _abs_avg(
        data,
        [
            "tire_slip_angle_front_left",
            "tire_slip_angle_front_right",
        ],
    )
    data["rear_slip_angle_avg"] = _abs_avg(
        data,
        [
            "tire_slip_angle_rear_left",
            "tire_slip_angle_rear_right",
        ],
    )

    data["front_suspension_avg"] = _avg(
        data,
        [
            "normalized_suspension_travel_front_left",
            "normalized_suspension_travel_front_right",
        ],
    )
    data["rear_suspension_avg"] = _avg(
        data,
        [
            "normalized_suspension_travel_rear_left",
            "normalized_suspension_travel_rear_right",
        ],
    )
    data["left_suspension_avg"] = _avg(
        data,
        [
            "normalized_suspension_travel_front_left",
            "normalized_suspension_travel_rear_left",
        ],
    )
    data["right_suspension_avg"] = _avg(
        data,
        [
            "normalized_suspension_travel_front_right",
            "normalized_suspension_travel_rear_right",
        ],
    )
    data["max_suspension_travel"] = pd.concat(
        [
            _num(data, "normalized_suspension_travel_front_left"),
            _num(data, "normalized_suspension_travel_front_right"),
            _num(data, "normalized_suspension_travel_rear_left"),
            _num(data, "normalized_suspension_travel_rear_right"),
        ],
        axis=1,
    ).max(axis=1)

    data["yaw_rate"] = _num(data, "angular_velocity_y")
    data["yaw_rate_abs"] = data["yaw_rate"].abs()
    data["lateral_accel"] = _num(data, "acceleration_x")
    data["longitudinal_accel"] = _num(data, "acceleration_z")
    data["lateral_g"] = data["lateral_accel"] / 9.80665
    data["longitudinal_g"] = data["longitudinal_accel"] / 9.80665

    timestamp_sec = _num(data, "timestamp_ms") / 1000.0
    race_time_sec = _num(data, "current_race_time")
    dt = timestamp_sec.diff()
    if dt.fillna(0).abs().sum() == 0:
        dt = race_time_sec.diff()
    session_dt = data["session_elapsed_seconds"].diff()
    if session_dt.fillna(0).abs().sum() > 0:
        dt = session_dt
    data["dt"] = dt.replace(0, pd.NA).bfill().fillna(0.0)
    data["speed_delta_mps"] = _num(data, "speed").diff().fillna(0.0)
    data["speed_delta_per_sec"] = (
        data["speed_delta_mps"] / data["dt"].replace(0, pd.NA)
    ).fillna(0.0)

    data["is_throttle"] = data["throttle_norm"] > 0.10
    data["is_braking"] = data["brake_norm"] > 0.10
    data["is_steering"] = data["steer_norm"].abs() > 0.10
    data["is_cornering"] = (data["steer_norm"].abs() > 0.20) | (
        data["yaw_rate_abs"] > 0.20
    )
    data["is_accelerating"] = data["longitudinal_accel"] > 0.50
    data["is_decelerating"] = data["longitudinal_accel"] < -0.50

    data["left_right_combined_slip_delta"] = (
        (
            _num(data, "tire_combined_slip_front_left").abs()
            + _num(data, "tire_combined_slip_rear_left").abs()
        )
        / 2.0
        - (
            _num(data, "tire_combined_slip_front_right").abs()
            + _num(data, "tire_combined_slip_rear_right").abs()
        )
        / 2.0
    ).abs()

    return data


def read_telemetry(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def write_processed(frame: pd.DataFrame, output: str | Path) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".parquet":
        frame.to_parquet(output_path, index=False)
    else:
        frame.to_csv(output_path, index=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate processed FH6 telemetry.")
    parser.add_argument("input", help="Raw telemetry CSV.")
    parser.add_argument("--output", required=True, help="Processed CSV or Parquet.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    raw = read_telemetry(args.input)
    processed = add_features(raw)
    write_processed(processed, args.output)
    print(f"Wrote processed telemetry: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
