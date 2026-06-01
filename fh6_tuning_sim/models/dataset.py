from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fh6_tuning_sim.analysis.feature_engineering import add_features


DEFAULT_INPUT_COLUMNS = [
    "speed",
    "yaw_rate",
    "lateral_accel",
    "longitudinal_accel",
    "front_combined_slip_avg",
    "rear_combined_slip_avg",
    "front_suspension_avg",
    "rear_suspension_avg",
    "throttle_norm",
    "brake_norm",
    "steer_norm",
]

DEFAULT_TARGET_COLUMNS = [
    "speed",
    "yaw_rate",
    "lateral_accel",
    "longitudinal_accel",
    "front_combined_slip_avg",
    "rear_combined_slip_avg",
    "front_suspension_avg",
    "rear_suspension_avg",
]


def build_windows(
    frame: pd.DataFrame,
    *,
    input_columns: list[str] | None = None,
    target_columns: list[str] | None = None,
    past_samples: int = 60,
    future_samples: int = 12,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    data = frame if "yaw_rate" in frame else add_features(frame)
    input_columns = input_columns or DEFAULT_INPUT_COLUMNS
    target_columns = target_columns or DEFAULT_TARGET_COLUMNS

    missing = [name for name in input_columns + target_columns if name not in data]
    if missing:
        raise ValueError(f"Missing columns for dataset build: {missing}")

    values_x = data[input_columns].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(
        dtype=np.float32
    )
    values_y = data[target_columns].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(
        dtype=np.float32
    )

    total = len(data) - past_samples - future_samples + 1
    if total <= 0:
        raise ValueError(
            "Not enough rows for requested windows: "
            f"rows={len(data)}, past={past_samples}, future={future_samples}"
        )

    x = np.empty((total, past_samples, len(input_columns)), dtype=np.float32)
    y = np.empty((total, len(target_columns)), dtype=np.float32)

    for index in range(total):
        x[index] = values_x[index : index + past_samples]
        target_index = index + past_samples + future_samples - 1
        y[index] = values_y[target_index]

    return x, y, input_columns, target_columns


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build supervised FH6 prediction windows.")
    parser.add_argument("input", help="Processed or raw telemetry CSV.")
    parser.add_argument("--output", required=True, help="Output .npz path.")
    parser.add_argument("--past-samples", type=int, default=60)
    parser.add_argument("--future-samples", type=int, default=12)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frame = pd.read_csv(args.input)
    x, y, input_columns, target_columns = build_windows(
        frame,
        past_samples=args.past_samples,
        future_samples=args.future_samples,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        x=x,
        y=y,
        input_columns=np.array(input_columns),
        target_columns=np.array(target_columns),
        past_samples=args.past_samples,
        future_samples=args.future_samples,
    )
    print(f"Wrote dataset: {output} x={x.shape} y={y.shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

