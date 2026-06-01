from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fh6_tuning_sim.data_management.annotation_store import read_annotations
from fh6_tuning_sim.data_management.dictionaries import option_values
from fh6_tuning_sim.data_management.json_store import ensure_parent_dir
from fh6_tuning_sim.data_management.platform_store import read_platform
from fh6_tuning_sim.data_management.route_profile import read_route_profiles
from fh6_tuning_sim.data_management.run_index import read_index


ROOT = Path(__file__).resolve().parents[2]
DATA_INTEGRITY_REPORT_PATH = ROOT / "reports" / "data_integrity_report.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _issue(code: str, message: str, *, target_type: str, target_id: str = "", details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "severity": "warning",
        "code": code,
        "target_type": target_type,
        "target_id": target_id,
        "message": message,
        "details": details or {},
    }


def _duplicate_issues(values: list[str], *, code: str, target_type: str, label: str) -> list[dict[str, Any]]:
    counts = Counter(value for value in values if value)
    return [
        _issue(code, f"重复 ID：{value}", target_type=target_type, target_id=value, details={label: value, "count": count})
        for value, count in counts.items()
        if count > 1
    ]


def _platform_refs(platform: dict[str, Any]) -> dict[str, Any]:
    car_ids: set[str] = set()
    tune_ids: set[str] = set()
    group_ids: set[str] = set()
    car_id_list: list[str] = []
    tune_id_list: list[str] = []
    group_id_list: list[str] = []
    for car in platform.get("cars", []) if isinstance(platform.get("cars"), list) else []:
        if not isinstance(car, dict):
            continue
        car_id = str(car.get("car_id") or "").strip()
        if car_id:
            car_ids.add(car_id)
            car_id_list.append(car_id)
        for tune in car.get("tune_versions", []) if isinstance(car.get("tune_versions"), list) else []:
            tune_id = str(tune.get("tune_id") or "").strip()
            if tune_id:
                tune_ids.add(tune_id)
                tune_id_list.append(tune_id)
        for group in car.get("dataset_groups", []) if isinstance(car.get("dataset_groups"), list) else []:
            group_id = str(group.get("dataset_group_id") or "").strip()
            if group_id:
                group_ids.add(group_id)
                group_id_list.append(group_id)
    return {
        "car_ids": car_ids,
        "tune_ids": tune_ids,
        "dataset_group_ids": group_ids,
        "car_id_list": car_id_list,
        "tune_id_list": tune_id_list,
        "dataset_group_id_list": group_id_list,
    }


def _path_exists(root: Path, value: Any) -> bool:
    if not value:
        return False
    path = Path(str(value))
    if not path.is_absolute():
        path = root / path
    return path.exists()


def _valid_tag_ids() -> set[str]:
    groups = [
        "general_tag",
        "intent_tag",
        "behavior_tag",
        "run_state_tag",
        "dataset_purpose",
        "data_status",
        "quality_status",
    ]
    values: set[str] = set()
    for group in groups:
        values.update(option_values(group, include_inactive=True))
    return values


def check_data_integrity(
    *,
    runs: list[dict[str, Any]] | None = None,
    platform: dict[str, Any] | None = None,
    annotations: list[dict[str, Any]] | None = None,
    route_profiles: list[dict[str, Any]] | None = None,
    root: str | Path = ROOT,
) -> dict[str, Any]:
    root_path = Path(root)
    runs = runs if runs is not None else read_index()
    platform = platform if platform is not None else read_platform()
    annotations = annotations if annotations is not None else read_annotations()
    route_profiles = route_profiles if route_profiles is not None else read_route_profiles()

    issues: list[dict[str, Any]] = []
    run_ids = {str(run.get("session_id") or "").strip() for run in runs if isinstance(run, dict)}
    refs = _platform_refs(platform)
    route_keys = set(option_values("route", include_inactive=True))
    valid_tags = _valid_tag_ids()

    issues.extend(_duplicate_issues([str(run.get("session_id") or "").strip() for run in runs], code="duplicate_run_id", target_type="run", label="session_id"))
    issues.extend(_duplicate_issues(refs["car_id_list"], code="duplicate_car_id", target_type="car", label="car_id"))
    issues.extend(_duplicate_issues(refs["tune_id_list"], code="duplicate_tune_id", target_type="tune", label="tune_id"))
    issues.extend(_duplicate_issues(refs["dataset_group_id_list"], code="duplicate_dataset_group_id", target_type="dataset_group", label="dataset_group_id"))
    issues.extend(_duplicate_issues([str(item.get("annotation_id") or "").strip() for item in annotations], code="duplicate_annotation_id", target_type="annotation", label="annotation_id"))
    issues.extend(_duplicate_issues([str(item.get("profile_id") or "").strip() for item in route_profiles], code="duplicate_route_profile_id", target_type="route_profile", label="profile_id"))

    for run in runs:
        if not isinstance(run, dict):
            continue
        session_id = str(run.get("session_id") or "").strip()
        car_id = str(run.get("car_id") or "").strip()
        tune_id = str(run.get("tune_id") or "").strip()
        group_id = str(run.get("dataset_group_id") or "").strip()
        route_name = str(run.get("route_name") or "").strip()
        if car_id and car_id not in refs["car_ids"]:
            issues.append(_issue("orphan_run_car", f"Run 指向不存在的 car：{car_id}", target_type="run", target_id=session_id))
        if tune_id and tune_id not in refs["tune_ids"]:
            issues.append(_issue("orphan_run_tune", f"Run 指向不存在的 tune：{tune_id}", target_type="run", target_id=session_id))
        if group_id and group_id not in refs["dataset_group_ids"]:
            issues.append(_issue("orphan_run_dataset_group", f"Run 指向不存在的数据集组：{group_id}", target_type="run", target_id=session_id))
        if route_name and route_name != "unknown" and route_name not in route_keys:
            issues.append(_issue("invalid_run_route", f"Run 使用了未登记路线：{route_name}", target_type="run", target_id=session_id))
        if not run.get("raw_csv_path"):
            issues.append(_issue("missing_raw_csv_reference", "Run 缺少 raw_csv_path。", target_type="run", target_id=session_id))
        elif not _path_exists(root_path, run.get("raw_csv_path")):
            issues.append(_issue("missing_raw_csv_file", f"raw CSV 文件不存在：{run.get('raw_csv_path')}", target_type="run", target_id=session_id))
        for path_key in ["processed_csv_path", "plot_path", "report_path", "dataset_path"]:
            value = run.get(path_key)
            if value and not _path_exists(root_path, value):
                issues.append(_issue("missing_referenced_file", f"引用文件不存在：{value}", target_type="run", target_id=session_id, details={"field": path_key}))

    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        annotation_id = str(annotation.get("annotation_id") or "").strip()
        target_type = str(annotation.get("target_type") or "").strip()
        target_id = str(annotation.get("target_id") or "").strip()
        run_id = str(annotation.get("run_id") or "").strip()
        if target_type == "run" and target_id and target_id not in run_ids:
            issues.append(_issue("orphan_annotation_target_run", f"Annotation 指向不存在的 run：{target_id}", target_type="annotation", target_id=annotation_id))
        if run_id and run_id not in run_ids:
            issues.append(_issue("orphan_annotation_run", f"Annotation run_id 不存在：{run_id}", target_type="annotation", target_id=annotation_id))
        for tag_id in annotation.get("tag_ids", []) if isinstance(annotation.get("tag_ids"), list) else []:
            tag = str(tag_id).strip()
            if tag and tag not in valid_tags:
                issues.append(_issue("invalid_tag_id", f"Annotation 使用了无效 tag_id：{tag}", target_type="annotation", target_id=annotation_id))

    for profile in route_profiles:
        if not isinstance(profile, dict):
            continue
        profile_id = str(profile.get("profile_id") or "").strip()
        source_session_id = str(profile.get("source_session_id") or "").strip()
        if source_session_id and source_session_id not in run_ids:
            issues.append(_issue("missing_route_profile_source_run", f"Route Profile 来源 run 不存在：{source_session_id}", target_type="route_profile", target_id=profile_id))
        source_runs = profile.get("source_survey_runs", {})
        if isinstance(source_runs, dict):
            for key, values in source_runs.items():
                for run_id in values if isinstance(values, list) else []:
                    run_id_text = str(run_id).strip()
                    if run_id_text and run_id_text not in run_ids:
                        issues.append(_issue("missing_route_profile_source_run", f"Route Profile source_survey_runs 缺少 run：{run_id_text}", target_type="route_profile", target_id=profile_id, details={"field": key}))

    return {
        "generated_at_utc": utc_now(),
        "summary": {
            "run_count": len(runs),
            "car_count": len(refs["car_ids"]),
            "annotation_count": len(annotations),
            "route_profile_count": len(route_profiles),
            "issue_count": len(issues),
        },
        "issues": issues,
    }


def write_data_integrity_report(
    result: dict[str, Any] | None = None,
    path: str | Path = DATA_INTEGRITY_REPORT_PATH,
) -> Path:
    result = result or check_data_integrity()
    report_path = Path(path)
    ensure_parent_dir(report_path)
    summary = result.get("summary", {})
    lines = [
        "# FH6 Tuning Sim Data Integrity Report",
        "",
        f"Generated: {result.get('generated_at_utc', utc_now())}",
        "",
        "## Summary",
        f"- Runs: {summary.get('run_count', 0)}",
        f"- Cars: {summary.get('car_count', 0)}",
        f"- Annotations: {summary.get('annotation_count', 0)}",
        f"- Route Profiles: {summary.get('route_profile_count', 0)}",
        f"- Warnings: {summary.get('issue_count', 0)}",
        "",
        "## Warnings",
    ]
    issues = result.get("issues", [])
    if not issues:
        lines.append("- No integrity warnings found.")
    else:
        for issue in issues:
            target = issue.get("target_id") or issue.get("target_type") or ""
            lines.append(f"- [{issue.get('code')}] {target}: {issue.get('message')}")
    lines.extend(
        [
            "",
            "## Policy",
            "- Integrity issues are reported as warnings and do not block UI startup.",
            "- Prefer archive/disable over hard delete when records are referenced by runs, annotations, or profiles.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
