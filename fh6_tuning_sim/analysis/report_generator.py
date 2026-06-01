from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from fh6_tuning_sim.analysis.diagnosis import (
    dataframe_summary,
    ensure_processed,
    run_diagnosis,
)
from fh6_tuning_sim.config import load_json


def _fmt(value: Any, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _drivetrain(metadata: dict[str, Any], tune: dict[str, Any]) -> str:
    value = metadata.get("drivetrain") or tune.get("drivetrain") or "AWD"
    return str(value).upper()


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def run_profile(frame: pd.DataFrame) -> dict[str, Any]:
    data = ensure_processed(frame)
    if data.empty:
        return {
            "classification": "empty",
            "good_for": [],
            "weak_for": ["所有分析"],
            "metrics": {},
        }

    metrics = {
        "full_throttle_rate": float((data["throttle_norm"] > 0.70).mean()),
        "heavy_brake_rate": float((data["brake_norm"] > 0.20).mean()),
        "large_steer_rate": float((data["steer_norm"].abs() > 0.25).mean()),
        "cornering_rate": float(data["is_cornering"].mean()),
        "high_speed_rate": float((data["speed_kmh"] > 160.0).mean()),
        "low_speed_rate": float((data["speed_kmh"] < 60.0).mean()),
    }

    classification = "混合道路行驶"
    good_for = ["通用遥测数据查看"]
    weak_for: list[str] = []

    if metrics["high_speed_rate"] > 0.70 and metrics["full_throttle_rate"] > 0.70:
        classification = "高速/极速行驶"
        good_for = [
            "极速与加速一致性",
            "高速转向稳定性",
            "高速时悬挂压缩特性",
        ]
        weak_for = [
            "低速入弯平衡",
            "带刹入弯平衡",
            "多种弯道类型的全面调校诊断",
        ]
    elif metrics["cornering_rate"] > 0.45 and metrics["large_steer_rate"] > 0.25:
        classification = "过弯为主"
        good_for = [
            "转向不足/转向过度平衡",
            "横摆响应",
            "前后轮轮胎负荷行为",
        ]
    elif metrics["heavy_brake_rate"] > 0.08:
        classification = "制动为主"
        good_for = [
            "制动稳定性",
            "入弯平衡",
            "左右滑移不平衡",
        ]

    if metrics["heavy_brake_rate"] < 0.02:
        weak_for.append("制动结论")
    if metrics["large_steer_rate"] < 0.12:
        weak_for.append("过弯平衡结论")

    return {
        "classification": classification,
        "good_for": good_for,
        "weak_for": list(dict.fromkeys(weak_for)),
        "metrics": metrics,
    }


def generate_report(
    frame: pd.DataFrame,
    *,
    metadata: dict[str, Any] | None = None,
    tune_config: dict[str, Any] | None = None,
) -> str:
    metadata = metadata or {}
    tune_config = tune_config or {}
    drivetrain = _drivetrain(metadata, tune_config)
    findings = run_diagnosis(frame, drivetrain=drivetrain)
    summary = dataframe_summary(frame)
    profile = run_profile(frame)

    car_name = metadata.get("car_name") or tune_config.get("car_name") or "unknown"
    use_case = metadata.get("use_case") or tune_config.get("use_case") or "unknown"
    tune_name = metadata.get("tune_name") or tune_config.get("tune_name") or "unknown"
    session_id = metadata.get("session_id") or "unknown"

    lines = [
        "# FH6 调校诊断报告",
        "",
        "## 会话信息",
        f"- 会话: {_fmt(session_id)}",
        f"- 车辆: {_fmt(car_name)}",
        f"- 调校: {_fmt(tune_name)}",
        f"- 用途: {_fmt(use_case)}",
        f"- 驱动形式: {_fmt(drivetrain)}",
        f"- 时长: {summary['duration_sec']} 秒",
        f"- 帧数: {summary['frames']}",
        f"- 最高速度: {summary['max_speed_kmh']} km/h",
        f"- 平均速度: {summary.get('avg_speed_kmh', 0.0)} km/h",
        f"- 最佳圈速: {_fmt(summary['best_lap'])}",
        "",
        "## 驾驶特征",
        f"- 分类: {profile['classification']}",
        f"- 全油门帧比例: {_pct(profile['metrics'].get('full_throttle_rate', 0.0))}",
        f"- 重刹帧比例: {_pct(profile['metrics'].get('heavy_brake_rate', 0.0))}",
        f"- 大角度转向帧比例: {_pct(profile['metrics'].get('large_steer_rate', 0.0))}",
        f"- 过弯帧比例: {_pct(profile['metrics'].get('cornering_rate', 0.0))}",
        f"- 高速帧 >160 km/h: {_pct(profile['metrics'].get('high_speed_rate', 0.0))}",
        f"- 低速帧 <60 km/h: {_pct(profile['metrics'].get('low_speed_rate', 0.0))}",
        "",
        "### 适用场景",
        *[f"- {item}" for item in profile["good_for"]],
        "",
        "### 覆盖不足",
        *(
            [f"- {item}" for item in profile["weak_for"]]
            if profile["weak_for"]
            else ["- 未检测到明显的覆盖缺失。"]
        ),
        "",
        "## 主要发现",
    ]

    if findings:
        for index, finding in enumerate(findings, start=1):
            lines.append(
                f"{index}. {finding.title} "
                f"({finding.severity}, {finding.frame_count} 帧, "
                f"{finding.frame_rate * 100:.2f}% 数据)."
            )
    else:
        lines.append("本次记录未检测到明显的规则性问题。")

    lines.extend(["", "## 证据详情"])
    if findings:
        for finding in findings:
            lines.append(f"### {finding.title}")
            for item in finding.evidence:
                lines.append(f"- {item}")
    else:
        lines.append("- 规则阈值未在此数据集上触发。")

    lines.extend(["", "## 调校建议"])
    if findings:
        seen: set[str] = set()
        for finding in findings:
            for suggestion in finding.suggestions:
                if suggestion in seen:
                    continue
                seen.add(suggestion)
                lines.append(f"- {suggestion}")
    else:
        lines.append("- 保持当前设置作为基线，与下一次调校进行对比。")

    lines.extend(["", "## 数据质量说明"])
    lines.append(
        "- 诊断结果仅作为参考提示，建议在同一路线重复跑多次确认。"
    )
    lines.append(
        "- 在训练模型之前，标记含有撞车、水坑、回退或异常路线偏离的记录。"
    )
    if metadata.get("official_doc_url"):
        lines.append(f"- 数据包格式参考: {metadata['official_doc_url']}")

    lines.extend(["", "## 机读诊断结果"])
    for finding in findings:
        lines.append(f"- `{finding.code}`: `{asdict(finding)}`")

    return "\n".join(lines) + "\n"




def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate FH6 tuning report.")
    parser.add_argument("input", help="Processed or raw telemetry CSV.")
    parser.add_argument("--metadata", help="Session metadata JSON.")
    parser.add_argument("--tune-config", help="Tune config JSON.")
    parser.add_argument("--output", required=True, help="Markdown report path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frame = pd.read_csv(args.input)
    metadata = load_json(args.metadata, required=False) if args.metadata else {}
    tune_config = load_json(args.tune_config, required=False) if args.tune_config else {}
    report = generate_report(frame, metadata=metadata, tune_config=tune_config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
