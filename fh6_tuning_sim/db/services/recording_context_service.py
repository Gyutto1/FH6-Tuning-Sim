from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH
from fh6_tuning_sim.db.repositories import (
    BuildRepository,
    CarRepository,
    SetupSnapshotRepository,
    TagRepository,
    TuneRepository,
)


@dataclass(frozen=True)
class RecordingContextValidation:
    is_valid: bool
    missing: list[str]
    context: dict[str, Any]


class RecordingContextService:
    """Validate and prepare context before Recording starts."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.cars = CarRepository(self.db_path)
        self.builds = BuildRepository(self.db_path)
        self.tunes = TuneRepository(self.db_path)
        self.snapshots = SetupSnapshotRepository(self.db_path)
        self.tags = TagRepository(self.db_path)

    def ensure_default_context(self, car_id: str) -> dict[str, Any]:
        car = self.cars.get_car(car_id)
        if car is None:
            raise ValueError(f"car not found: {car_id}")
        build = self.builds.ensure_default_stock_build(car_id)
        tune = self.tunes.ensure_baseline_tune(str(build["build_id"]))
        setup = self.snapshots.ensure_default_setup_snapshot(car_id, str(build["build_id"]), str(tune["tune_id"]))
        return {
            "car_id": car_id,
            "build_id": build["build_id"],
            "tune_id": tune["tune_id"],
            "setup_snapshot_id": setup["setup_snapshot_id"],
        }

    def validate(self, context: dict[str, Any]) -> RecordingContextValidation:
        required = [
            "car_id",
            "build_id",
            "tune_id",
            "setup_snapshot_id",
            "route_mode",
            "record_type",
        ]
        missing = [field for field in required if not str(context.get(field) or "").strip()]
        intent_tags = list(context.get("intent_tags") or [])

        car_id = str(context.get("car_id") or "")
        build_id = str(context.get("build_id") or "")
        tune_id = str(context.get("tune_id") or "")
        setup_snapshot_id = str(context.get("setup_snapshot_id") or "")
        if not missing:
            route_mode = str(context.get("route_mode") or "")
            route_id = str(context.get("route_id") or "").strip()
            if route_mode == "timed_route" and not route_id:
                route_id = "route_horizon_highway_loop"
                context["route_id"] = route_id
            if self.cars.get_car(car_id) is None:
                missing.append("car_id:not_found")
            if not self.snapshots.validate_context(car_id, build_id, tune_id, setup_snapshot_id):
                missing.append("context_chain")
            for tag_key in intent_tags:
                if self.tags.tag_id_for_key(str(tag_key), "intent_tag") is None and self.tags.tag_id_for_key(str(tag_key), "general_tag") is None:
                    missing.append(f"intent_tag:not_found:{tag_key}")

        return RecordingContextValidation(
            is_valid=not missing,
            missing=missing,
            context={
                "car_id": car_id,
                "build_id": build_id,
                "tune_id": tune_id,
                "setup_snapshot_id": setup_snapshot_id,
                "route_id": context.get("route_id"),
                "route_mode": context.get("route_mode"),
                "record_type": context.get("record_type"),
                "intent_tags": intent_tags,
                "notes": context.get("notes") or "",
            },
        )

    def validate_or_raise(self, context: dict[str, Any]) -> dict[str, Any]:
        result = self.validate(context)
        if not result.is_valid:
            raise ValueError(f"recording context incomplete: {', '.join(result.missing)}")
        return result.context
