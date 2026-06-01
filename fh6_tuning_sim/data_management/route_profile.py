from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import math

import pandas as pd

from fh6_tuning_sim.analysis.feature_engineering import add_time_lap_state_features
from fh6_tuning_sim.config import write_json
from fh6_tuning_sim.data_management.dictionaries import label_of
from fh6_tuning_sim.data_management.json_store import safe_load_json, safe_save_json
from fh6_tuning_sim.data_management.session_naming import sanitize_filename


ROOT = Path(__file__).resolve().parents[2]
ROUTE_PROFILE_DIR = ROOT / "data" / "routes" / "profiles"
ROUTE_PROFILE_INDEX_PATH = ROOT / "data" / "platform" / "route_profiles.json"

POSITION_COLUMNS = ["position_x", "position_y", "position_z"]
PROFILE_POINT_COLUMNS = [
    "sample_index",
    "session_elapsed_seconds",
    "detected_lap_elapsed_seconds",
    "route_distance_m",
    "position_x",
    "position_y",
    "position_z",
    "yaw",
    "pitch",
    "roll",
    "speed",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _num(frame: pd.DataFrame, name: str, default: float = 0.0) -> pd.Series:
    if name not in frame:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[name], errors="coerce").fillna(default)


def _has_position(frame: pd.DataFrame) -> bool:
    return all(column in frame for column in POSITION_COLUMNS)


def _route_id(route_name: str) -> str:
    return f"route_{sanitize_filename(route_name)}"


def _profile_id(route_name: str, session_id: str, lap_id: int) -> str:
    return f"{_route_id(route_name)}__{sanitize_filename(session_id)}__lap{lap_id:02d}"


def _read_profiles_index(path: str | Path = ROUTE_PROFILE_INDEX_PATH) -> dict[str, Any]:
    index_path = Path(path)
    payload = safe_load_json(index_path, {"schema_version": 1, "updated_at_utc": utc_now(), "profiles": []})
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", utc_now())
    payload.setdefault("profiles", [])
    if not isinstance(payload["profiles"], list):
        payload["profiles"] = []
    return payload


def _write_profiles_index(payload: dict[str, Any], path: str | Path = ROUTE_PROFILE_INDEX_PATH) -> None:
    payload["updated_at_utc"] = utc_now()
    safe_save_json(path, payload)


def read_route_profiles(path: str | Path = ROUTE_PROFILE_INDEX_PATH) -> list[dict[str, Any]]:
    return _read_profiles_index(path).get("profiles", [])


def route_survey_readiness(
    route_name: str,
    survey_runs: list[dict[str, Any]],
    profiles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    counts = {
        "left_boundary": 0,
        "right_boundary": 0,
        "reference_line": 0,
        "kerb_or_optional_area": 0,
        "invalid_area_probe": 0,
    }
    source_run_ids = {key: [] for key in counts}
    selected_route = str(route_name).strip()
    for run in survey_runs:
        if not isinstance(run, dict):
            continue
        run_route = str(run.get("route_name") or "").strip()
        if selected_route and run_route and run_route != selected_route:
            continue
        if run.get("run_type") not in {None, "", "track_boundary_survey"}:
            continue
        survey_type = str(run.get("survey_type") or "").strip()
        if survey_type not in counts:
            continue
        counts[survey_type] += 1
        session_id = str(run.get("session_id") or "").strip()
        if session_id:
            source_run_ids[survey_type].append(session_id)

    requirements = {
        "left_boundary": 3,
        "right_boundary": 3,
        "reference_line": 1,
    }
    complete_requirements = {
        "left_boundary": 5,
        "right_boundary": 5,
        "reference_line": 3,
    }
    missing_measurements = [
        {
            "survey_type": survey_type,
            "label": label_of("survey_type", survey_type),
            "current": counts[survey_type],
            "required": required,
            "missing": max(0, required - counts[survey_type]),
        }
        for survey_type, required in requirements.items()
        if counts[survey_type] < required
    ]
    can_generate_draft = not missing_measurements
    has_any_measurement = any(counts.values())
    complete_enough = all(counts[key] >= value for key, value in complete_requirements.items())
    if complete_enough:
        status_key = "complete_enough"
    elif can_generate_draft:
        status_key = "draft_available"
    elif has_any_measurement:
        status_key = "insufficient"
    else:
        status_key = "not_started"

    route_profiles = [
        profile
        for profile in (profiles or [])
        if str(profile.get("route_name", "")).strip() == selected_route
    ]
    return {
        "route_name": route_name,
        "status_key": status_key,
        "status_label": label_of("route_readiness_status", status_key),
        "survey_counts": counts,
        "source_run_ids": source_run_ids,
        "missing_measurements": missing_measurements,
        "can_generate_draft": can_generate_draft,
        "is_complete_enough": complete_enough,
        "profile_count": len(route_profiles),
        "profiles": route_profiles,
        "corridor_label": "可行驶走廊草稿",
        "boundary_quality": "draft" if can_generate_draft else "missing",
    }


def route_profile_status(route_name: str, path: str | Path = ROUTE_PROFILE_INDEX_PATH) -> dict[str, Any]:
    route_profiles = [
        profile
        for profile in read_route_profiles(path)
        if str(profile.get("route_name", "")).strip() == str(route_name).strip()
    ]
    survey_counts = {
        "left_boundary": 0,
        "right_boundary": 0,
        "reference_line": 0,
        "kerb_or_optional_area": 0,
        "invalid_area_probe": 0,
    }
    for profile in route_profiles:
        survey_type = str(profile.get("survey_type") or "").strip()
        if survey_type in survey_counts:
            survey_counts[survey_type] += 1
    has_boundary = survey_counts["left_boundary"] > 0 and survey_counts["right_boundary"] > 0
    has_reference = survey_counts["reference_line"] > 0
    if has_boundary and has_reference:
        boundary_quality = "usable"
    elif route_profiles:
        boundary_quality = "draft"
    else:
        boundary_quality = "missing"
    return {
        "route_name": route_name,
        "profile_count": len(route_profiles),
        "survey_counts": survey_counts,
        "has_boundary_survey": has_boundary,
        "has_reference_line": has_reference,
        "boundary_quality": boundary_quality,
        "profiles": route_profiles,
    }


def select_measurement_lap(frame: pd.DataFrame, requested_lap_id: int | None = None) -> tuple[int, pd.DataFrame]:
    data = add_time_lap_state_features(frame)
    if "detected_lap_id" not in data:
        data["detected_lap_id"] = 1
    if requested_lap_id is not None:
        selected = data[data["detected_lap_id"] == requested_lap_id]
        if selected.empty:
            raise ValueError(f"detected_lap_id not found: {requested_lap_id}")
        return int(requested_lap_id), selected.copy()

    summaries: list[tuple[float, int, int]] = []
    for lap_id, lap_frame in data.groupby("detected_lap_id", sort=True):
        elapsed = _num(lap_frame, "detected_lap_elapsed_seconds")
        duration = float(elapsed.max() - elapsed.min()) if not elapsed.empty else 0.0
        summaries.append((duration, len(lap_frame), int(lap_id)))
    if not summaries:
        return 1, data.copy()
    _, _, lap_id = max(summaries)
    return lap_id, data[data["detected_lap_id"] == lap_id].copy()


def _cumulative_position_distance(frame: pd.DataFrame) -> pd.Series:
    if not _has_position(frame):
        return pd.Series(0.0, index=frame.index, dtype="float64")
    x = _num(frame, "position_x")
    z = _num(frame, "position_z")
    dx = x.diff().fillna(0.0)
    dz = z.diff().fillna(0.0)
    return (dx.pow(2) + dz.pow(2)).pow(0.5).cumsum()


def _route_distance(frame: pd.DataFrame) -> pd.Series:
    distance = _num(frame, "distance_traveled")
    span = float(distance.max() - distance.min()) if not distance.empty else 0.0
    if span > 1.0:
        return distance - float(distance.min())
    return _cumulative_position_distance(frame)


def _downsample(frame: pd.DataFrame, *, max_points: int) -> pd.DataFrame:
    if len(frame) <= max_points:
        return frame
    stride = max(1, math.ceil(len(frame) / max_points))
    return frame.iloc[::stride].copy()


def build_route_profile(
    frame: pd.DataFrame,
    *,
    session_id: str,
    route_name: str,
    source_lap_id: int | None = None,
    run_type: str = "normal_recording",
    survey_type: str | None = None,
    car_id: str | None = None,
    tune_id: str | None = None,
    dataset_group_id: str | None = None,
    max_points: int = 2000,
) -> dict[str, Any]:
    lap_id, lap_frame = select_measurement_lap(frame, source_lap_id)
    if lap_frame.empty:
        raise ValueError("Cannot build route profile from an empty lap")

    lap_frame = lap_frame.copy()
    lap_frame["route_distance_m"] = _route_distance(lap_frame)
    route_length_m = float(lap_frame["route_distance_m"].max() - lap_frame["route_distance_m"].min())
    duration = float(_num(lap_frame, "detected_lap_elapsed_seconds").max())
    speed = _num(lap_frame, "speed")

    if _has_position(lap_frame):
        first = lap_frame.iloc[0]
        last = lap_frame.iloc[-1]
        closed_loop_distance_m = math.sqrt(
            float(last["position_x"] - first["position_x"]) ** 2
            + float(last["position_z"] - first["position_z"]) ** 2
        )
        elevation_delta_m = float(_num(lap_frame, "position_y").max() - _num(lap_frame, "position_y").min())
    else:
        closed_loop_distance_m = None
        elevation_delta_m = None

    profile_frame = _downsample(lap_frame, max_points=max_points)
    for column in PROFILE_POINT_COLUMNS:
        if column not in profile_frame:
            profile_frame[column] = None
    points = profile_frame[PROFILE_POINT_COLUMNS].where(pd.notna(profile_frame[PROFILE_POINT_COLUMNS]), None).to_dict("records")

    profile_id = _profile_id(route_name, session_id, lap_id)
    profile = {
        "schema_version": 1,
        "profile_id": profile_id,
        "route_id": _route_id(route_name),
        "route_name": route_name,
        "profile_type": "measurement_lap",
        "run_type": run_type,
        "survey_type": survey_type,
        "source_survey_runs": {
            "left_boundary_run_ids": [session_id] if survey_type == "left_boundary" else [],
            "right_boundary_run_ids": [session_id] if survey_type == "right_boundary" else [],
            "reference_line_run_ids": [session_id] if survey_type == "reference_line" else [],
            "kerb_or_optional_area_run_ids": [session_id] if survey_type == "kerb_or_optional_area" else [],
            "invalid_area_probe_run_ids": [session_id] if survey_type == "invalid_area_probe" else [],
        },
        "has_boundary_survey": survey_type in {"left_boundary", "right_boundary"},
        "boundary_quality": "draft" if survey_type else "unknown",
        "progress_resolution_m": 1.0,
        "source_session_id": session_id,
        "source_lap_id": lap_id,
        "car_id": car_id,
        "tune_id": tune_id,
        "dataset_group_id": dataset_group_id,
        "created_at_utc": utc_now(),
        "sample_count": int(len(lap_frame)),
        "point_count": int(len(points)),
        "duration_seconds": round(duration, 3),
        "route_length_m": round(route_length_m, 3),
        "closed_loop_distance_m": round(closed_loop_distance_m, 3) if closed_loop_distance_m is not None else None,
        "elevation_delta_m": round(elevation_delta_m, 3) if elevation_delta_m is not None else None,
        "mean_speed_kmh": round(float(speed.mean()) * 3.6, 3),
        "max_speed_kmh": round(float(speed.max()) * 3.6, 3),
        "has_position": _has_position(lap_frame),
        "has_distance_traveled": "distance_traveled" in lap_frame and route_length_m > 1.0,
        "profile_quality_flags": {
            "has_position": _has_position(lap_frame),
            "has_route_length": route_length_m > 100.0,
            "has_lap_boundary": "detected_lap_id" in lap_frame,
            "has_enough_samples": len(lap_frame) >= 120,
        },
        "points": points,
    }
    return profile


def save_route_profile(profile: dict[str, Any]) -> dict[str, Any]:
    ROUTE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    profile_id = str(profile["profile_id"])
    profile_path = ROUTE_PROFILE_DIR / f"{profile_id}.json"
    stored = dict(profile)
    stored["profile_path"] = str(profile_path.relative_to(ROOT))
    write_json(profile_path, stored)

    index = _read_profiles_index()
    summary_keys = [
        "profile_id",
        "route_id",
        "route_name",
        "profile_type",
        "run_type",
        "survey_type",
        "source_survey_runs",
        "has_boundary_survey",
        "boundary_quality",
        "progress_resolution_m",
        "source_session_id",
        "source_lap_id",
        "car_id",
        "tune_id",
        "dataset_group_id",
        "created_at_utc",
        "sample_count",
        "point_count",
        "duration_seconds",
        "route_length_m",
        "closed_loop_distance_m",
        "elevation_delta_m",
        "mean_speed_kmh",
        "max_speed_kmh",
        "has_position",
        "has_distance_traveled",
        "profile_quality_flags",
        "profile_path",
    ]
    summary = {key: stored.get(key) for key in summary_keys}
    profiles = [item for item in index.get("profiles", []) if item.get("profile_id") != profile_id]
    profiles.append(summary)
    index["profiles"] = sorted(profiles, key=lambda item: str(item.get("created_at_utc", "")), reverse=True)
    _write_profiles_index(index)
    return stored


def build_route_profile_from_csv(
    csv_path: str | Path,
    *,
    session_id: str | None = None,
    route_name: str = "unknown",
    source_lap_id: int | None = None,
    run_type: str = "normal_recording",
    survey_type: str | None = None,
    car_id: str | None = None,
    tune_id: str | None = None,
    dataset_group_id: str | None = None,
    max_points: int = 2000,
) -> dict[str, Any]:
    path = Path(csv_path)
    frame = pd.read_csv(path)
    profile = build_route_profile(
        frame,
        session_id=session_id or path.stem,
        route_name=route_name,
        source_lap_id=source_lap_id,
        run_type=run_type,
        survey_type=survey_type,
        car_id=car_id,
        tune_id=tune_id,
        dataset_group_id=dataset_group_id,
        max_points=max_points,
    )
    return save_route_profile(profile)
