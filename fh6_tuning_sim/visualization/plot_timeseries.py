from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from fh6_tuning_sim.analysis.feature_engineering import add_features


def _time_axis(frame: pd.DataFrame) -> pd.Series:
    if "timestamp_ms" in frame:
        timestamp = pd.to_numeric(frame["timestamp_ms"], errors="coerce")
        if not timestamp.dropna().empty:
            return (timestamp - timestamp.min()) / 1000.0
    if "current_race_time" in frame:
        time = pd.to_numeric(frame["current_race_time"], errors="coerce")
        if time.fillna(0).abs().sum() > 0:
            return time - time.min()
    return pd.Series(range(len(frame)), index=frame.index, dtype="float64")


def _set_robust_ylim(axis, frame: pd.DataFrame, columns: list[str], *, padding: float = 0.12) -> None:
    values = []
    for column in columns:
        if column in frame:
            values.append(pd.to_numeric(frame[column], errors="coerce"))
    if not values:
        return

    series = pd.concat(values).dropna()
    if series.empty:
        return

    lower = float(series.quantile(0.01))
    upper = float(series.quantile(0.99))
    if lower == upper:
        return

    span = upper - lower
    axis.set_ylim(lower - span * padding, upper + span * padding)


def plot_timeseries(frame: pd.DataFrame, output: str | Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "matplotlib is required for plotting. Install project dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    data = frame if "speed_kmh" in frame else add_features(frame)
    time = _time_axis(data)

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    fig.suptitle("FH6 Telemetry Overview")

    axes[0].plot(time, data["speed_kmh"], label="speed_kmh", color="#1f77b4")
    axes[0].set_ylabel("km/h")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(time, data["throttle_norm"], label="throttle", color="#2ca02c")
    axes[1].plot(time, data["brake_norm"], label="brake", color="#d62728")
    axes[1].plot(time, data["steer_norm"], label="steer", color="#9467bd")
    axes[1].set_ylabel("input")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(time, data["yaw_rate"], label="yaw_rate", color="#ff7f0e")
    axes[2].plot(
        time,
        data["front_combined_slip_avg"],
        label="front_combined_slip",
        color="#17becf",
    )
    axes[2].plot(
        time,
        data["rear_combined_slip_avg"],
        label="rear_combined_slip",
        color="#bcbd22",
    )
    axes[2].set_ylabel("slip / rad/s")
    axes[2].legend(loc="upper right")
    axes[2].grid(True, alpha=0.25)
    _set_robust_ylim(
        axes[2],
        data,
        ["yaw_rate", "front_combined_slip_avg", "rear_combined_slip_avg"],
    )

    axes[3].plot(
        time,
        data["front_suspension_avg"],
        label="front_suspension",
        color="#8c564b",
    )
    axes[3].plot(
        time,
        data["rear_suspension_avg"],
        label="rear_suspension",
        color="#e377c2",
    )
    axes[3].axhline(0.92, color="#7f7f7f", linestyle="--", linewidth=1, label="bottoming threshold")
    axes[3].set_xlabel("time (s)")
    axes[3].set_ylabel("normalized travel")
    axes[3].legend(loc="upper right")
    axes[3].grid(True, alpha=0.25)
    axes[3].set_ylim(-0.05, 1.05)

    fig.tight_layout(rect=(0, 0, 1, 0.97))
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot FH6 telemetry time series.")
    parser.add_argument("input", help="Processed or raw telemetry CSV.")
    parser.add_argument("--output", required=True, help="Output PNG path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frame = pd.read_csv(args.input)
    plot_timeseries(frame, args.output)
    print(f"Wrote plot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
