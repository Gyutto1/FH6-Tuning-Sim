from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd

from fh6_tuning_sim.analysis.feature_engineering import add_features


@dataclass
class DiagnosisFinding:
    code: str
    title: str
    severity: str
    frame_count: int
    frame_rate: float
    evidence: list[str]
    suggestions: list[str]


def _pct(mask: pd.Series, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(float(mask.sum()) / total, 4)


def _mean(frame: pd.DataFrame, column: str, mask: pd.Series | None = None) -> float:
    if column not in frame:
        return 0.0
    series = pd.to_numeric(frame[column], errors="coerce")
    if mask is not None:
        series = series[mask]
    value = series.mean()
    return 0.0 if pd.isna(value) else round(float(value), 4)


def _max(frame: pd.DataFrame, column: str, mask: pd.Series | None = None) -> float:
    if column not in frame:
        return 0.0
    series = pd.to_numeric(frame[column], errors="coerce")
    if mask is not None:
        series = series[mask]
    value = series.max()
    return 0.0 if pd.isna(value) else round(float(value), 4)


def _severity(rate: float, high: float = 0.08, medium: float = 0.03) -> str:
    if rate >= high:
        return "high"
    if rate >= medium:
        return "medium"
    return "low"


def ensure_processed(frame: pd.DataFrame) -> pd.DataFrame:
    if "front_combined_slip_avg" in frame and "throttle_norm" in frame:
        return frame
    return add_features(frame)


def driven_slip(frame: pd.DataFrame, drivetrain: str) -> pd.Series:
    drive = drivetrain.upper()
    if drive == "FWD":
        return frame["front_slip_ratio_avg"]
    if drive == "RWD":
        return frame["rear_slip_ratio_avg"]
    return (frame["front_slip_ratio_avg"] + frame["rear_slip_ratio_avg"]) / 2.0


def run_diagnosis(frame: pd.DataFrame, *, drivetrain: str = "AWD") -> list[DiagnosisFinding]:
    data = ensure_processed(frame)
    total = len(data)
    findings: list[DiagnosisFinding] = []

    if total == 0:
        return findings

    understeer = (
        (data["speed_kmh"] > 25)
        & (data["steer_norm"].abs() > 0.35)
        & (data["front_combined_slip_avg"] > 0.75)
        & (data["front_combined_slip_avg"] > data["rear_combined_slip_avg"] + 0.15)
        & (data["yaw_rate_abs"] < 0.55)
    )
    if understeer.any():
        rate = _pct(understeer, total)
        findings.append(
            DiagnosisFinding(
                code="understeer",
                title="疑似转向不足",
                severity=_severity(rate),
                frame_count=int(understeer.sum()),
                frame_rate=rate,
                evidence=[
                    f"前轮综合滑移均值（事件期间）: {_mean(data, 'front_combined_slip_avg', understeer)}",
                    f"后轮综合滑移均值（事件期间）: {_mean(data, 'rear_combined_slip_avg', understeer)}",
                    f"横摆角速度绝对值均值（事件期间）: {_mean(data, 'yaw_rate_abs', understeer)} rad/s",
                ],
                suggestions=[
                    "稍微软化前防倾杆或加硬后防倾杆。",
                    "如果模式重复出现，检查前胎压和前外倾角。",
                ],
            )
        )

    oversteer = (
        (data["speed_kmh"] > 20)
        & (data["is_cornering"])
        & (data["rear_combined_slip_avg"] > 0.80)
        & (data["rear_combined_slip_avg"] > data["front_combined_slip_avg"] + 0.20)
        & (data["yaw_rate_abs"] > 0.45)
    )
    if oversteer.any():
        rate = _pct(oversteer, total)
        findings.append(
            DiagnosisFinding(
                code="oversteer",
                title="疑似转向过度",
                severity=_severity(rate),
                frame_count=int(oversteer.sum()),
                frame_rate=rate,
                evidence=[
                    f"后轮综合滑移均值（事件期间）: {_mean(data, 'rear_combined_slip_avg', oversteer)}",
                    f"前轮综合滑移均值（事件期间）: {_mean(data, 'front_combined_slip_avg', oversteer)}",
                    f"横摆角速度峰值（事件期间）: {_max(data, 'yaw_rate_abs', oversteer)} rad/s",
                ],
                suggestions=[
                    "软化后防倾杆，或在胎温支持的情况下提高后胎压。",
                    "对于 RWD/AWD，考虑减小后差速器加速锁止率。",
                ],
            )
        )

    slip = driven_slip(data, drivetrain)
    wheelspin = (
        (data["throttle_norm"] > 0.65)
        & (data["speed_kmh"] > 15)
        & (slip > 0.45)
        & (data["speed_delta_per_sec"] < 1.5)
    )
    if wheelspin.any():
        rate = _pct(wheelspin, total)
        findings.append(
            DiagnosisFinding(
                code="exit_wheelspin",
                title="疑似出弯打滑",
                severity=_severity(rate),
                frame_count=int(wheelspin.sum()),
                frame_rate=rate,
                evidence=[
                    f"驱动轮滑移比均值（事件期间）: {round(float(slip[wheelspin].mean()), 4)}",
                    f"油门均值（事件期间）: {_mean(data, 'throttle_norm', wheelspin)}",
                    f"速度加速度代理值（事件期间）: {_mean(data, 'speed_delta_per_sec', wheelspin)} m/s^2",
                ],
                suggestions=[
                    "如果抓地力丢失可复现，减小驱动轴差速器加速锁止率。",
                    "对于抓地为主的公路调校，拉长低挡位或软化后弹簧/防倾杆。",
                ],
            )
        )

    braking_instability = (
        (data["brake_norm"] > 0.50)
        & (data["speed_kmh"] > 30)
        & (data["yaw_rate_abs"] > 0.35)
        & (data["left_right_combined_slip_delta"] > 0.20)
    )
    if braking_instability.any():
        rate = _pct(braking_instability, total)
        findings.append(
            DiagnosisFinding(
                code="braking_instability",
                title="疑似制动不稳定",
                severity=_severity(rate),
                frame_count=int(braking_instability.sum()),
                frame_rate=rate,
                evidence=[
                    f"制动均值（事件期间）: {_mean(data, 'brake_norm', braking_instability)}",
                    f"左右综合滑移差均值: {_mean(data, 'left_right_combined_slip_delta', braking_instability)}",
                    f"横摆角速度绝对值均值（事件期间）: {_mean(data, 'yaw_rate_abs', braking_instability)} rad/s",
                ],
                suggestions=[
                    "如果重刹时后部不稳定，将制动平衡稍微向前调整。",
                    "如果入弯前出现类似抱死的滑移，降低制动压力。",
                ],
            )
        )

    bottoming = data["max_suspension_travel"] > 0.92
    if bottoming.any():
        rate = _pct(bottoming, total)
        findings.append(
            DiagnosisFinding(
                code="suspension_bottoming",
                title="疑似悬挂触底",
                severity=_severity(rate, high=0.05, medium=0.015),
                frame_count=int(bottoming.sum()),
                frame_rate=rate,
                evidence=[
                    f"悬挂行程归一化峰值: {_max(data, 'max_suspension_travel')}",
                    f"前悬挂均值（事件期间）: {_mean(data, 'front_suspension_avg', bottoming)}",
                    f"后悬挂均值（事件期间）: {_mean(data, 'rear_suspension_avg', bottoming)}",
                ],
                suggestions=[
                    "如果在普通路面出现触底，提高车身高度。",
                    "如果压缩峰值在载荷转移时重复出现，增加弹簧刚度或压缩阻尼。",
                ],
            )
        )

    return sorted(
        findings,
        key=lambda item: ({"high": 0, "medium": 1, "low": 2}[item.severity], -item.frame_count),
    )


def dataframe_summary(frame: pd.DataFrame) -> dict[str, Any]:
    data = ensure_processed(frame)
    if data.empty:
        return {
            "frames": 0,
            "duration_sec": 0.0,
            "max_speed_kmh": 0.0,
            "best_lap": None,
        }

    duration = 0.0
    if "timestamp_ms" in data:
        timestamp = pd.to_numeric(data["timestamp_ms"], errors="coerce")
        timestamp = timestamp.dropna()
        if not timestamp.empty:
            duration = float((timestamp.max() - timestamp.min()) / 1000.0)
    if not duration and "current_race_time" in data:
        race_time = pd.to_numeric(data["current_race_time"], errors="coerce").dropna()
        if not race_time.empty:
            duration = float(race_time.max() - race_time.min())

    best_lap = None
    if "best_lap" in data:
        non_zero = pd.to_numeric(data["best_lap"], errors="coerce")
        non_zero = non_zero[non_zero > 0]
        if not non_zero.empty:
            best_lap = round(float(non_zero.min()), 3)

    return {
        "frames": int(len(data)),
        "duration_sec": round(duration, 3),
        "max_speed_kmh": round(float(data["speed_kmh"].max()), 2),
        "avg_speed_kmh": round(float(data["speed_kmh"].mean()), 2),
        "best_lap": best_lap,
        "cornering_frame_rate": _pct(data["is_cornering"], len(data)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run rule-based FH6 diagnosis.")
    parser.add_argument("input", help="Processed or raw telemetry CSV.")
    parser.add_argument("--drivetrain", default="AWD", choices=["FWD", "RWD", "AWD"])
    parser.add_argument("--json", dest="json_output", help="Optional JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frame = pd.read_csv(args.input)
    findings = run_diagnosis(frame, drivetrain=args.drivetrain)
    payload = {
        "summary": dataframe_summary(frame),
        "findings": [asdict(item) for item in findings],
    }

    if args.json_output:
        path = Path(args.json_output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote diagnosis JSON: {path}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
