from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from fh6_tuning_sim.analysis.feature_engineering import add_features


def _prepare(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "speed_kmh" not in frame:
        frame = add_features(frame)
    return frame


def _metric(frame: pd.DataFrame) -> dict[str, float | None]:
    cornering = frame[frame["is_cornering"]]
    throttle = frame[frame["throttle_norm"] > 0.65]
    braking = frame[frame["brake_norm"] > 0.50]

    yaw_response = (
        cornering["yaw_rate_abs"] / cornering["steer_norm"].abs().replace(0, pd.NA)
    ).replace([float("inf"), -float("inf")], pd.NA)

    best_lap = None
    if "best_lap" in frame:
        laps = pd.to_numeric(frame["best_lap"], errors="coerce")
        laps = laps[laps > 0]
        if not laps.empty:
            best_lap = round(float(laps.min()), 3)

    return {
        "max_speed_kmh": round(float(frame["speed_kmh"].max()), 2),
        "avg_corner_speed_kmh": round(float(cornering["speed_kmh"].mean()), 2)
        if not cornering.empty
        else None,
        "front_slip_corner_avg": round(float(cornering["front_combined_slip_avg"].mean()), 4)
        if not cornering.empty
        else None,
        "rear_slip_corner_avg": round(float(cornering["rear_combined_slip_avg"].mean()), 4)
        if not cornering.empty
        else None,
        "yaw_response_proxy": round(float(yaw_response.mean()), 4)
        if not yaw_response.dropna().empty
        else None,
        "wheelspin_rate": round(float((throttle["rear_slip_ratio_avg"] > 0.45).mean()), 4)
        if not throttle.empty
        else None,
        "braking_instability_proxy": round(
            float((braking["left_right_combined_slip_delta"] > 0.20).mean()), 4
        )
        if not braking.empty
        else None,
        "bottoming_rate": round(float((frame["max_suspension_travel"] > 0.92).mean()), 4),
        "best_lap": best_lap,
    }


def _winner(metric: str, left: float | None, right: float | None) -> str:
    if left is None or right is None:
        return "N/A"
    lower_is_better = {
        "front_slip_corner_avg",
        "rear_slip_corner_avg",
        "wheelspin_rate",
        "braking_instability_proxy",
        "bottoming_rate",
        "best_lap",
    }
    if abs(left - right) < 1e-9:
        return "tie"
    if metric in lower_is_better:
        return "left" if left < right else "right"
    return "left" if left > right else "right"


def compare_runs(
    left_path: str | Path,
    right_path: str | Path,
    *,
    left_name: str = "left",
    right_name: str = "right",
) -> str:
    left = _metric(_prepare(left_path))
    right = _metric(_prepare(right_path))

    lines = [
        "# FH6 Tune Comparison",
        "",
        f"- Left: {left_name}",
        f"- Right: {right_name}",
        "",
        "| Metric | Left | Right | Better |",
        "| --- | ---: | ---: | --- |",
    ]

    for metric in left:
        better = _winner(metric, left[metric], right[metric])
        label = {"left": left_name, "right": right_name}.get(better, better)
        lines.append(f"| {metric} | {left[metric]} | {right[metric]} | {label} |")

    lines.extend(
        [
            "",
            "## Reading Notes",
            "- Higher corner speed and yaw response are generally better for grip driving.",
            "- Lower slip, wheelspin, braking instability, and bottoming rates are generally better.",
            "- Compare runs on the same route and similar traffic/weather context.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare two FH6 telemetry runs.")
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument("--left-name", default="left")
    parser.add_argument("--right-name", default="right")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = compare_runs(
        args.left,
        args.right,
        left_name=args.left_name,
        right_name=args.right_name,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote comparison: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

