from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd

from fh6_tuning_sim.analysis.data_quality import add_context_quality, compute_data_quality_for_csv
from fh6_tuning_sim.config import load_json, write_json
from fh6_tuning_sim.data_management.json_store import safe_load_json, safe_save_json
from fh6_tuning_sim.data_management.platform_store import (
    stable_car_id,
    stable_group_id,
    stable_tune_id,
    sync_platform_with_runs,
)


ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "data" / "index"
RUNS_INDEX_PATH = INDEX_DIR / "runs_index.json"


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _path_if_exists(path: Path) -> Path | None:
    return path if path.exists() else None


def _session_id_from_meta(path: Path) -> str:
    suffix = "_meta"
    stem = path.stem
    return stem[: -len(suffix)] if stem.endswith(suffix) else stem


def read_index(index_path: str | Path = RUNS_INDEX_PATH) -> list[dict[str, Any]]:
    path = Path(index_path)
    data = safe_load_json(path, {"runs": []})
    runs = data.get("runs", [])
    return runs if isinstance(runs, list) else []


def write_index(runs: list[dict[str, Any]], index_path: str | Path = RUNS_INDEX_PATH) -> None:
    safe_save_json(
        index_path,
        {
            "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "runs": sorted(runs, key=lambda item: item.get("created_at", ""), reverse=True),
        },
    )


def build_run_record(session_id: str, *, root: str | Path = ROOT) -> dict[str, Any]:
    root_path = Path(root)
    raw_path = root_path / "data" / "raw" / f"{session_id}.csv"
    processed_path = root_path / "data" / "processed" / f"{session_id}_processed.csv"
    metadata_path = root_path / "data" / "sessions" / f"{session_id}_meta.json"
    tune_path = root_path / "data" / "sessions" / f"{session_id}_tune.json"
    plot_path = root_path / "reports" / f"{session_id}_timeseries.png"
    report_path = root_path / "reports" / f"{session_id}_report.md"
    dataset_path = root_path / "data" / "datasets" / f"{session_id}_dataset.npz"

    metadata = load_json(metadata_path, required=False)
    tune = load_json(tune_path, required=False)
    quality = compute_data_quality_for_csv(raw_path) if raw_path.exists() else {}
    quality = add_context_quality(quality, metadata=metadata, tune=tune) if quality else {}
    review = metadata.get("run_review", {}) if isinstance(metadata.get("run_review", {}), dict) else {}

    created_at = metadata.get("started_at_utc") or metadata.get("created_at") or ""
    record = {
        "session_id": session_id,
        "created_at": created_at,
        "car_name": metadata.get("car_name") or tune.get("car_name") or "unknown",
        "car_ordinal": metadata.get("car_ordinal") or tune.get("car_ordinal") or quality.get("detected_car_ordinal"),
        "car_class": metadata.get("car_class") or tune.get("car_class") or quality.get("detected_car_class") or "unknown",
        "performance_index": metadata.get("performance_index") or tune.get("performance_index") or quality.get("detected_performance_index"),
        "drivetrain": metadata.get("drivetrain") or tune.get("drivetrain") or quality.get("detected_drivetrain") or "unknown",
        "car_group": metadata.get("car_group") or tune.get("car_group") or quality.get("detected_car_group"),
        "detected_car_ordinal": quality.get("detected_car_ordinal"),
        "detected_car_class": quality.get("detected_car_class"),
        "detected_performance_index": quality.get("detected_performance_index"),
        "detected_drivetrain_type": quality.get("detected_drivetrain_type"),
        "detected_drivetrain": quality.get("detected_drivetrain"),
        "detected_num_cylinders": quality.get("detected_num_cylinders"),
        "detected_car_group": quality.get("detected_car_group"),
        "use_case": metadata.get("use_case") or tune.get("use_case") or "unknown",
        "run_type": metadata.get("run_type") or "normal_recording",
        "survey_type": metadata.get("survey_type"),
        "is_for_route_profile": bool(metadata.get("is_for_route_profile", False)),
        "survey_speed_note": metadata.get("survey_speed_note", ""),
        "route_name": metadata.get("route_name") or "unknown",
        "surface_type": metadata.get("surface_type") or "unknown",
        "test_scenario": metadata.get("test_scenario") or "unknown",
        "purpose": metadata.get("purpose") or "",
        "purpose_tags": metadata.get("purpose_tags", []),
        "driver_input_style": metadata.get("driver_input_style") or "unknown",
        "tune_name": metadata.get("tune_name") or tune.get("tune_name") or "unknown",
        "tune_version": metadata.get("tune_version") or tune.get("tune_version") or "",
        "duration_seconds": quality.get("duration_seconds", 0.0),
        "packet_count": quality.get("packet_count", metadata.get("rows_written", 0)),
        "estimated_sample_rate": quality.get("estimated_sample_rate", 0.0),
        "raw_csv_path": _rel(_path_if_exists(raw_path)),
        "processed_csv_path": _rel(_path_if_exists(processed_path)),
        "plot_path": _rel(_path_if_exists(plot_path)),
        "report_path": _rel(_path_if_exists(report_path)),
        "dataset_path": _rel(_path_if_exists(dataset_path)),
        "tune_snapshot_path": _rel(_path_if_exists(tune_path)),
        "metadata_path": _rel(_path_if_exists(metadata_path)),
        "notes": metadata.get("notes", ""),
        "tags": metadata.get("tags", []),
        "intent_tags": review.get("intent_tags", []),
        "behavior_tags": review.get("behavior_tags", []),
        "data_status_tags": review.get("data_status_tags", []),
        "quality_state_tags": review.get("quality_state_tags", []),
        "handling_scores": review.get("handling_scores", {}),
        "subjective_scores": review.get("subjective_scores", {}),
        "review_notes": review.get("notes", ""),
        "quality_status": quality.get("quality_status", "unknown"),
        "quality_warnings": quality.get("quality_warnings", []),
        "metadata_completeness_score": quality.get("metadata_completeness_score", 0.0),
        "run_quality_score": quality.get("run_quality_score", 0.0),
        "comparability_score": quality.get("comparability_score", 0.0),
        "modeling_readiness_score": quality.get("modeling_readiness_score", 0.0),
        "state_tag_counts": quality.get("state_tag_counts", {}),
        "detected_lap_count": quality.get("detected_lap_count", 0),
        "detected_lap_reset_count": quality.get("detected_lap_reset_count", 0),
        "laps": quality.get("lap_summaries", []),
        "segments": metadata.get("segments", []),
        "quality": quality,
    }
    record["car_id"] = stable_car_id(record)
    record["tune_id"] = stable_tune_id(record["car_id"], record)
    record["dataset_group_id"] = stable_group_id(record["car_id"], record)
    return record


def upsert_run(record: dict[str, Any], index_path: str | Path = RUNS_INDEX_PATH) -> list[dict[str, Any]]:
    runs = read_index(index_path)
    runs = [item for item in runs if item.get("session_id") != record.get("session_id")]
    runs.append(record)
    write_index(runs, index_path)
    sync_platform_with_runs(runs)
    return runs


def index_session(session_id: str, *, index_path: str | Path = RUNS_INDEX_PATH) -> dict[str, Any]:
    record = build_run_record(session_id)
    upsert_run(record, index_path)
    return record


def rebuild_index(*, root: str | Path = ROOT, index_path: str | Path = RUNS_INDEX_PATH) -> list[dict[str, Any]]:
    root_path = Path(root)
    metadata_files = sorted((root_path / "data" / "sessions").glob("*_meta.json"))
    records = [build_run_record(_session_id_from_meta(path), root=root_path) for path in metadata_files]
    write_index(records, index_path)
    sync_platform_with_runs(records)
    return records


def runs_dataframe(index_path: str | Path = RUNS_INDEX_PATH) -> pd.DataFrame:
    runs = read_index(index_path)
    if not runs:
        return pd.DataFrame()
    return pd.DataFrame(runs)
