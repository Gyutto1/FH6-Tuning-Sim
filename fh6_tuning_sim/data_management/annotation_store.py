from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fh6_tuning_sim.data_management.json_store import safe_load_json, safe_save_json
from fh6_tuning_sim.data_management.session_naming import sanitize_filename


ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS_INDEX_PATH = ROOT / "data" / "index" / "annotations.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_annotations(path: str | Path = ANNOTATIONS_INDEX_PATH) -> list[dict[str, Any]]:
    index_path = Path(path)
    payload = safe_load_json(index_path, {"annotations": []})
    annotations = payload.get("annotations", [])
    return annotations if isinstance(annotations, list) else []


def write_annotations(annotations: list[dict[str, Any]], path: str | Path = ANNOTATIONS_INDEX_PATH) -> None:
    safe_save_json(
        path,
        {
            "schema_version": 1,
            "updated_at_utc": utc_now(),
            "annotations": sorted(annotations, key=lambda item: str(item.get("updated_at_utc", "")), reverse=True),
        },
    )


def annotation_id_for(target_type: str, target_id: str, source: str) -> str:
    return "ann__" + "__".join([sanitize_filename(target_type), sanitize_filename(target_id), sanitize_filename(source)])


def upsert_annotation(
    *,
    target_type: str,
    target_id: str,
    tag_ids: list[str],
    source: str = "manual",
    confidence: float = 1.0,
    note: str = "",
    run_id: str | None = None,
    start_time: float | None = None,
    end_time: float | None = None,
    path: str | Path = ANNOTATIONS_INDEX_PATH,
) -> dict[str, Any]:
    now = utc_now()
    annotation_id = annotation_id_for(target_type, target_id, source)
    annotations = [item for item in read_annotations(path) if item.get("annotation_id") != annotation_id]
    existing = next((item for item in read_annotations(path) if item.get("annotation_id") == annotation_id), {})
    annotation = {
        "annotation_id": annotation_id,
        "target_type": target_type,
        "target_id": target_id,
        "run_id": run_id,
        "start_time": start_time,
        "end_time": end_time,
        "tag_ids": sorted(set(str(tag).strip() for tag in tag_ids if str(tag).strip())),
        "source": source,
        "confidence": float(confidence),
        "note": note,
        "created_at_utc": existing.get("created_at_utc") or now,
        "updated_at_utc": now,
        "is_active": True,
    }
    annotations.append(annotation)
    write_annotations(annotations, path)
    return annotation


def annotations_for_target(target_type: str, target_id: str, *, path: str | Path = ANNOTATIONS_INDEX_PATH) -> list[dict[str, Any]]:
    return [
        item
        for item in read_annotations(path)
        if item.get("target_type") == target_type and item.get("target_id") == target_id and item.get("is_active", True)
    ]
