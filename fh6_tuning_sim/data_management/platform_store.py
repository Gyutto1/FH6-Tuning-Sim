from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fh6_tuning_sim.config import load_json, write_json
from fh6_tuning_sim.data_management.dictionaries import label_of, option_values
from fh6_tuning_sim.data_management.json_store import safe_load_json, safe_save_json
from fh6_tuning_sim.data_management.session_naming import sanitize_filename


ROOT = Path(__file__).resolve().parents[2]
PLATFORM_DIR = ROOT / "data" / "platform"
PLATFORM_INDEX_PATH = PLATFORM_DIR / "platform_index.json"
SESSIONS_DIR = ROOT / "data" / "sessions"

HANDLING_SCORE_KEYS = ["response", "stability", "predictability", "recoverability", "input_effort"]
SUBJECTIVE_SCORE_KEYS = [
    "steering_response",
    "stability",
    "exit_traction",
    "predictability",
    "recoverability",
    "ease_of_driving",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def number_or_none(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def stable_car_id(record: dict[str, Any]) -> str:
    ordinal = number_or_none(record.get("detected_car_ordinal") or record.get("car_ordinal"))
    if ordinal not in (None, 0):
        return f"car_ordinal_{int(ordinal)}"
    name = clean_text(record.get("car_name"), "unknown_car")
    return f"car_{sanitize_filename(name)}"


def stable_tune_id(car_id: str, record: dict[str, Any]) -> str:
    tune_name = clean_text(record.get("tune_name"), "unknown_tune")
    tune_version = clean_text(record.get("tune_version"), "v00")
    return f"{car_id}__tune__{sanitize_filename(tune_name)}__{sanitize_filename(tune_version)}"


def infer_purpose(record: dict[str, Any]) -> str:
    explicit = clean_text(record.get("purpose"))
    if explicit:
        return explicit
    purpose_keys = set(option_values("dataset_purpose", include_inactive=True))
    for tag in clean_list(record.get("tags")):
        if tag in purpose_keys:
            return tag
    return "baseline"


def stable_group_id(car_id: str, record: dict[str, Any]) -> str:
    scenario = clean_text(record.get("test_scenario"), "unknown")
    route = clean_text(record.get("route_name"), "unknown")
    surface = clean_text(record.get("surface_type"), "unknown")
    purpose = infer_purpose(record)
    return "__".join(
        [
            car_id,
            "group",
            sanitize_filename(scenario),
            sanitize_filename(route),
            sanitize_filename(surface),
            sanitize_filename(purpose),
        ]
    )


def empty_platform() -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": 1,
        "created_at_utc": now,
        "updated_at_utc": now,
        "cars": [],
        "run_reviews": {},
        "archived": {},
    }


def read_platform(path: str | Path = PLATFORM_INDEX_PATH) -> dict[str, Any]:
    platform_path = Path(path)
    data = safe_load_json(platform_path, empty_platform())
    if not isinstance(data, dict) or not data:
        return empty_platform()
    data.setdefault("schema_version", 1)
    data.setdefault("created_at_utc", utc_now())
    data.setdefault("updated_at_utc", utc_now())
    data.setdefault("cars", [])
    data.setdefault("run_reviews", {})
    data.setdefault("archived", {})
    if not isinstance(data["cars"], list):
        data["cars"] = []
    if not isinstance(data["run_reviews"], dict):
        data["run_reviews"] = {}
    return data


def write_platform(platform: dict[str, Any], path: str | Path = PLATFORM_INDEX_PATH) -> None:
    platform["updated_at_utc"] = utc_now()
    safe_save_json(path, platform)


def find_car(platform: dict[str, Any], car_id: str) -> dict[str, Any] | None:
    for car in platform.get("cars", []):
        if car.get("car_id") == car_id:
            return car
    return None


def _upsert_car(platform: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    car_id = stable_car_id(record)
    car = find_car(platform, car_id)
    if car is None:
        car = {
            "car_id": car_id,
            "display_name": clean_text(record.get("car_name"), "未命名车辆"),
            "car_ordinal": number_or_none(record.get("detected_car_ordinal") or record.get("car_ordinal")),
            "car_class": clean_text(record.get("detected_car_class") or record.get("car_class"), "unknown"),
            "performance_index": number_or_none(record.get("detected_performance_index") or record.get("performance_index")),
            "drivetrain": clean_text(record.get("detected_drivetrain") or record.get("drivetrain"), "unknown"),
            "car_group": record.get("detected_car_group") or record.get("car_group"),
            "status": "active",
            "tags": [],
            "notes": "",
            "tune_versions": [],
            "dataset_groups": [],
            "created_at_utc": now,
            "updated_at_utc": now,
        }
        platform.setdefault("cars", []).append(car)
    else:
        for target, source in [
            ("display_name", "car_name"),
            ("car_class", "detected_car_class"),
            ("performance_index", "detected_performance_index"),
            ("drivetrain", "detected_drivetrain"),
            ("car_group", "detected_car_group"),
        ]:
            value = record.get(source)
            if value not in (None, "", "unknown"):
                car[target] = value
        ordinal = number_or_none(record.get("detected_car_ordinal") or record.get("car_ordinal"))
        if ordinal not in (None, 0):
            car["car_ordinal"] = ordinal
        car.setdefault("tune_versions", [])
        car.setdefault("dataset_groups", [])
        car.setdefault("tags", [])
        car.setdefault("notes", "")
        car.setdefault("status", "active")
        car["updated_at_utc"] = now
    return car


def _upsert_tune(car: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    tune_id = stable_tune_id(str(car["car_id"]), record)
    tunes = car.setdefault("tune_versions", [])
    tune = next((item for item in tunes if item.get("tune_id") == tune_id), None)
    if tune is None:
        tune = {
            "tune_id": tune_id,
            "name": clean_text(record.get("tune_name"), "unknown_tune"),
            "version": clean_text(record.get("tune_version"), "v00"),
            "status": "active",
            "tags": [],
            "notes": "",
            "use_case": clean_text(record.get("use_case"), "unknown"),
            "tune_snapshot_path": record.get("tune_snapshot_path"),
            "created_at_utc": now,
            "updated_at_utc": now,
        }
        tunes.append(tune)
    else:
        tune["name"] = clean_text(record.get("tune_name"), tune.get("name", "unknown_tune"))
        tune["version"] = clean_text(record.get("tune_version"), tune.get("version", "v00"))
        tune["use_case"] = clean_text(record.get("use_case"), tune.get("use_case", "unknown"))
        if record.get("tune_snapshot_path"):
            tune["tune_snapshot_path"] = record.get("tune_snapshot_path")
        tune.setdefault("tags", [])
        tune.setdefault("notes", "")
        tune.setdefault("status", "active")
        tune["updated_at_utc"] = now
    return tune


def _upsert_dataset_group(car: dict[str, Any], tune: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    group_id = stable_group_id(str(car["car_id"]), record)
    groups = car.setdefault("dataset_groups", [])
    group = next((item for item in groups if item.get("dataset_group_id") == group_id), None)
    scenario = clean_text(record.get("test_scenario"), "unknown")
    route = clean_text(record.get("route_name"), "unknown")
    surface = clean_text(record.get("surface_type"), "unknown")
    purpose = infer_purpose(record)
    tags = clean_list(record.get("tags"))
    purpose_tags = [tag for tag in tags if tag in set(option_values("dataset_purpose", include_inactive=True))]
    name = f"{label_of('test_scenario', scenario)} / {route} / {label_of('dataset_purpose', purpose)}"

    if group is None:
        group = {
            "dataset_group_id": group_id,
            "name": name,
            "scenario_key": scenario,
            "purpose": purpose,
            "purpose_tags": purpose_tags,
            "route_name": route,
            "surface_type": surface,
            "tune_ids": [tune["tune_id"]],
            "run_ids": [],
            "segments": [],
            "status": "active",
            "tags": tags,
            "notes": "",
            "created_at_utc": now,
            "updated_at_utc": now,
        }
        groups.append(group)
    else:
        group.update(
            {
                "name": clean_text(group.get("name"), name),
                "scenario_key": scenario,
                "purpose": purpose,
                "purpose_tags": sorted(set(clean_list(group.get("purpose_tags")) + purpose_tags)),
                "route_name": route,
                "surface_type": surface,
                "updated_at_utc": now,
            }
        )
        tune_ids = clean_list(group.get("tune_ids"))
        if str(tune["tune_id"]) not in tune_ids:
            tune_ids.append(str(tune["tune_id"]))
        group["tune_ids"] = tune_ids
        group["tags"] = sorted(set(clean_list(group.get("tags")) + tags))
        group.setdefault("run_ids", [])
        group.setdefault("segments", [])
        group.setdefault("status", "active")
        group.setdefault("notes", "")
    session_id = clean_text(record.get("session_id"))
    if session_id and session_id not in group["run_ids"]:
        group["run_ids"].append(session_id)
    return group


def sync_platform_with_runs(runs: list[dict[str, Any]], *, path: str | Path = PLATFORM_INDEX_PATH) -> dict[str, Any]:
    platform = read_platform(path)
    for record in runs:
        if not isinstance(record, dict) or not record.get("session_id"):
            continue
        car = _upsert_car(platform, record)
        tune = _upsert_tune(car, record)
        _upsert_dataset_group(car, tune, record)
    platform["cars"] = sorted(platform.get("cars", []), key=lambda item: str(item.get("display_name", "")).lower())
    write_platform(platform, path)
    return platform


def review_defaults() -> dict[str, Any]:
    return {
        "intent_tags": [],
        "behavior_tags": [],
        "data_status_tags": [],
        "quality_state_tags": [],
        "purpose_tags": [],
        "handling_scores": {key: None for key in HANDLING_SCORE_KEYS},
        "subjective_scores": {key: None for key in SUBJECTIVE_SCORE_KEYS},
        "notes": "",
    }


def normalize_review(raw: Any) -> dict[str, Any]:
    defaults = review_defaults()
    raw = raw if isinstance(raw, dict) else {}
    review = dict(defaults)
    review["intent_tags"] = clean_list(raw.get("intent_tags"))
    review["behavior_tags"] = clean_list(raw.get("behavior_tags"))
    review["data_status_tags"] = clean_list(raw.get("data_status_tags"))
    review["quality_state_tags"] = clean_list(raw.get("quality_state_tags"))
    review["purpose_tags"] = clean_list(raw.get("purpose_tags"))
    review["notes"] = clean_text(raw.get("notes"))

    handling_raw = raw.get("handling_scores", {}) if isinstance(raw.get("handling_scores", {}), dict) else {}
    subjective_raw = raw.get("subjective_scores", {}) if isinstance(raw.get("subjective_scores", {}), dict) else {}
    review["handling_scores"] = {
        key: number_or_none(handling_raw.get(key)) for key in HANDLING_SCORE_KEYS
    }
    review["subjective_scores"] = {
        key: number_or_none(subjective_raw.get(key)) for key in SUBJECTIVE_SCORE_KEYS
    }
    if raw.get("updated_at_utc"):
        review["updated_at_utc"] = raw.get("updated_at_utc")
    return review


def get_run_review(session_id: str, *, path: str | Path = PLATFORM_INDEX_PATH) -> dict[str, Any]:
    platform = read_platform(path)
    raw = platform.get("run_reviews", {}).get(session_id, {})
    metadata_path = SESSIONS_DIR / f"{session_id}_meta.json"
    if not raw and metadata_path.exists():
        metadata = load_json(metadata_path, required=False)
        raw = metadata.get("run_review", {})
    return normalize_review(raw)


def save_run_review(session_id: str, review: dict[str, Any], *, path: str | Path = PLATFORM_INDEX_PATH) -> dict[str, Any]:
    normalized = normalize_review(review)
    normalized["updated_at_utc"] = utc_now()
    platform = read_platform(path)
    platform.setdefault("run_reviews", {})[session_id] = normalized
    write_platform(platform, path)

    metadata_path = SESSIONS_DIR / f"{session_id}_meta.json"
    if metadata_path.exists():
        metadata = load_json(metadata_path, required=False)
        metadata["run_review"] = normalized
        existing_tags = clean_list(metadata.get("tags"))
        merged_tags = sorted(
            set(
                existing_tags
                + normalized["intent_tags"]
                + normalized["behavior_tags"]
                + normalized["data_status_tags"]
                + normalized["quality_state_tags"]
                + normalized["purpose_tags"]
            )
        )
        metadata["tags"] = merged_tags
        write_json(metadata_path, metadata)
    from fh6_tuning_sim.data_management.annotation_store import upsert_annotation

    upsert_annotation(
        target_type="run",
        target_id=session_id,
        tag_ids=(
            normalized["intent_tags"]
            + normalized["behavior_tags"]
            + normalized["data_status_tags"]
            + normalized["quality_state_tags"]
            + normalized["purpose_tags"]
        ),
        source="manual",
        confidence=1.0,
        note=normalized.get("notes", ""),
        run_id=session_id,
    )
    return normalized


def summarize_car(car: dict[str, Any], runs_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    groups = car.get("dataset_groups", []) if isinstance(car.get("dataset_groups"), list) else []
    run_ids: list[str] = []
    for group in groups:
        run_ids.extend(clean_list(group.get("run_ids")))
    unique_run_ids = sorted(set(run_ids))
    run_records = [runs_by_id[run_id] for run_id in unique_run_ids if run_id in runs_by_id]
    quality_scores = [float(item.get("run_quality_score", 0) or 0) for item in run_records]
    readiness_scores = [float(item.get("modeling_readiness_score", 0) or 0) for item in run_records]
    return {
        "run_count": len(run_records),
        "tune_count": len(car.get("tune_versions", [])),
        "dataset_group_count": len(groups),
        "scenario_count": len({group.get("scenario_key") for group in groups if group.get("scenario_key")}),
        "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0.0,
        "avg_modeling_readiness": round(sum(readiness_scores) / len(readiness_scores), 1) if readiness_scores else 0.0,
    }


def behavior_counts_for_car(car: dict[str, Any], run_reviews: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    run_ids: set[str] = set()
    for group in car.get("dataset_groups", []):
        run_ids.update(clean_list(group.get("run_ids")))
    for run_id in run_ids:
        review = normalize_review(run_reviews.get(run_id, {}))
        for tag in review.get("behavior_tags", []):
            counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def average_scores_for_car(car: dict[str, Any], run_reviews: dict[str, Any], score_group: str) -> dict[str, float]:
    run_ids: set[str] = set()
    for group in car.get("dataset_groups", []):
        run_ids.update(clean_list(group.get("run_ids")))
    values: dict[str, list[float]] = {}
    for run_id in run_ids:
        review = normalize_review(run_reviews.get(run_id, {}))
        scores = review.get(score_group, {}) if isinstance(review.get(score_group), dict) else {}
        for key, value in scores.items():
            number = number_or_none(value)
            if number is not None:
                values.setdefault(key, []).append(float(number))
    return {key: round(sum(items) / len(items), 2) for key, items in values.items() if items}
