from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fh6_tuning_sim.data_management.dictionaries import DICTIONARY_SPECS, label_of
from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect
from fh6_tuning_sim.db.legacy_migration import migrate_legacy_json
from fh6_tuning_sim.db.migrations import init_schema
from fh6_tuning_sim.db.repositories import (
    SnapshotFreezeRepository,
    BuildRepository,
    CarRepository,
    ExperimentRepository,
    RecordTypeRepository,
    RouteRepository,
    RunRepository,
    SetupSnapshotRepository,
    TagRepository,
    TuneParameterRepository,
    TuneRepository,
    UpgradeStoreRepository,
)
from fh6_tuning_sim.db.repositories.utils import utc_now
from fh6_tuning_sim.db.services.recording_context_service import RecordingContextService
from fh6_tuning_sim.runtime_paths import (
    app_root,
    ensure_database_from_seed,
    ensure_runtime_dirs,
    runtime_mode_label,
)
from fh6_tuning_sim.ui_desktop.i18n.snapshot_labels import (
    DATA_OWNERSHIP_LINES,
    VEHICLE_DATA_REQUIRED_KEYS,
)

ROOT = app_root()
G_FORCE = 9.80665
WATTS_PER_METRIC_HP = 735.49875
METRICS_UNITS_VERSION = 2


class DesktopDataService:
    """SQLite-backed facade used by PySide6 pages.

    The method names and returned dictionaries stay compatible with the v0.5
    JSON service while the data now comes from SQLite repositories.
    """

    TYPE_LABEL_MAP = {
        "lap_recording": "完整跑圈",
        "full_lap": "完整跑圈",
        "free_drive": "自由驾驶",
        "drag_strip": "直线加速",
        "hard_braking": "重刹测试",
        "heavy_braking": "重刹测试",
        "low_speed_corner": "低速弯",
        "mid_speed_corner": "中速弯",
        "high_speed_corner": "高速弯",
        "track_survey": "赛道测量",
        "track_boundary_survey": "赛道测量",
        "normal_recording": "普通记录",
        "other": "其他",
    }
    ROUTE_MODE_LABEL_MAP = {
        "timed_route": "计时赛 / 路线",
        "free_drive": "自由驾驶",
        "unset": "未设置",
    }
    QUALITY_LABEL_MAP = {
        "good": "良好",
        "warning": "注意",
        "draft": "草稿",
        "usable": "可用",
        "bad": "较差",
        "unknown": "未知",
        "archived": "已归档",
    }

    def __init__(self, root: str | Path = ROOT, db_path: str | Path | None = None) -> None:
        self._root = Path(root)
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self._ensure_database()
        self.cars = CarRepository(self.db_path)
        self.builds = BuildRepository(self.db_path)
        self.tunes = TuneRepository(self.db_path)
        self.snapshots = SetupSnapshotRepository(self.db_path)
        self._freeze = SnapshotFreezeRepository(self.db_path)
        self.runs_repo = RunRepository(self.db_path)
        self.tags = TagRepository(self.db_path)
        self.record_types = RecordTypeRepository(self.db_path)
        self.tune_parameters = TuneParameterRepository(self.db_path)
        self.upgrades = UpgradeStoreRepository(self.db_path)
        self.routes_repo = RouteRepository(self.db_path)
        self.experiments = ExperimentRepository(self.db_path)
        self.recording_context = RecordingContextService(self.db_path)

    def _ensure_database(self) -> None:
        ensure_runtime_dirs()
        if self.db_path.exists():
            init_schema(self.db_path)
        elif self.db_path == DEFAULT_DB_PATH:
            if ensure_database_from_seed(self.db_path):
                init_schema(self.db_path)
            else:
                migrate_legacy_json(self.db_path, backup_existing_db=False)
        else:
            init_schema(self.db_path)

    def runtime_paths(self) -> dict[str, str]:
        return {
            "mode": runtime_mode_label(),
            "app_root": str(self._root),
            "db": str(self.db_path),
            "raw": str(self._root / "data" / "raw"),
            "processed": str(self._root / "data" / "processed"),
            "sessions": str(self._root / "data" / "sessions"),
            "reports": str(self._root / "reports"),
            "configs": str(self._root / "configs"),
            "dictionaries": str(self._root / "configs" / "dictionaries"),
            "udp_host": "127.0.0.1",
            "udp_port": "9999",
        }

    @property
    def platform(self) -> dict[str, Any]:
        return {"schema_version": 2, "cars": self.list_cars()}

    @property
    def runs(self) -> list[dict[str, Any]]:
        return self._load_runs()

    def _load_platform(self) -> dict[str, Any]:
        return self.platform

    def _load_runs(self) -> list[dict[str, Any]]:
        return [self._legacy_run_dict(record) for record in self.runs_repo.query_run_records(include_archived=True)]

    def list_cars(self) -> list[dict[str, Any]]:
        return [self._car_view_model(car) for car in self.cars.list_cars()]

    def get_car(self, car_id: str) -> dict[str, Any] | None:
        car = self.cars.get_car(car_id)
        if car is None:
            return None
        model = self._car_view_model(car)
        model["car_group"] = car.get("car_group")
        model["tune_versions"] = self._tune_versions_for_car(car_id)
        model["dataset_groups"] = self.list_dataset_groups_for_car(car_id)
        model["scenario_count"] = len({run.get("route_name") for run in self.list_runs_for_car(car_id) if run.get("route_name")})
        model["builds"] = self.list_builds_for_car(car_id)
        return model

    def list_builds_for_car(self, car_id: str, include_drafts: bool = False) -> list[dict[str, Any]]:
        def _is_draft(row: dict[str, Any]) -> bool:
            return str(row.get("status") or "") == "draft"

        return [
            {
                "build_id": row.get("build_id"),
                "car_id": row.get("car_id"),
                "display_name": row.get("display_name"),
                "build_key": row.get("build_key"),
                "pi": row.get("pi"),
                "car_class": row.get("car_class"),
                "status": row.get("status"),
                "notes": row.get("notes") or "",
                "source": row.get("source") or "",
                "tune_count": len(self.tunes.list_by_build(str(row.get("build_id")))),
            }
            for row in self.builds.list_by_car(car_id)
            if include_drafts or not _is_draft(row)
        ]

    def get_build_detail(self, build_id: str) -> dict[str, Any] | None:
        build = self.builds.get_build(build_id)
        if build is None:
            return None
        car = self.cars.get_car(str(build.get("car_id")))
        tunes = self.list_tunes_for_build(build_id)
        runs = self.list_runs_for_build(build_id)
        snapshot = self.builds.latest_build_snapshot(build_id)
        return {
            **build,
            "car_name": car.get("display_name") if car else "",
            "build_snapshot": snapshot,
            "upgrade_selections": self.builds.list_upgrade_selections(build_id),
            "tunes": tunes,
            "runs": runs,
            "run_count": len(runs),
            "tune_count": len(tunes),
        }

    def list_tunes_for_build(self, build_id: str) -> list[dict[str, Any]]:
        return [
            {
                "tune_id": row.get("tune_id"),
                "build_id": row.get("build_id"),
                "name": row.get("display_name"),
                "display_name": row.get("display_name"),
                "version": row.get("version") or "",
                "status": row.get("status"),
                "notes": row.get("notes") or "",
            }
            for row in self.tunes.list_by_build(build_id)
        ]

    def get_tune_detail(self, tune_id: str) -> dict[str, Any] | None:
        tune = self.tunes.get_tune(tune_id)
        if tune is None:
            return None
        build = self.builds.get_build(str(tune.get("build_id")))
        car = self.cars.get_car(str(build.get("car_id"))) if build else None
        snapshots = self.list_setup_snapshots_for_tune(tune_id)
        runs = self.list_runs_for_tune(tune_id)
        return {
            **tune,
            "build": build,
            "car": car,
            "setup_snapshots": snapshots,
            "runs": runs,
            "parameters": self.list_tune_parameter_values(tune_id),
            "run_count": len(runs),
            "setup_snapshot_count": len(snapshots),
        }

    def list_setup_snapshots_for_tune(self, tune_id: str) -> list[dict[str, Any]]:
        return [
            {
                "setup_snapshot_id": row.get("setup_snapshot_id"),
                "car_id": row.get("car_id"),
                "build_id": row.get("build_id"),
                "tune_id": row.get("tune_id"),
                "snapshot_name": row.get("snapshot_name") or "未命名快照",
                "pi": row.get("pi"),
                "car_class": row.get("car_class"),
                "drivetrain": row.get("drivetrain"),
                "power": row.get("power"),
                "torque": row.get("torque"),
                "weight": row.get("weight"),
                "front_weight_percent": row.get("front_weight_percent"),
                "tire_compound": row.get("tire_compound"),
                "performance_ratings": row.get("performance_ratings"),
                "source": row.get("source"),
                "notes": row.get("notes") or "",
            }
            for row in self.snapshots.list_by_tune(tune_id)
        ]

    def update_setup_snapshot(self, setup_snapshot_id: str, updates: dict[str, Any]) -> bool:
        return self.snapshots.update_snapshot(setup_snapshot_id, updates)

    def list_tune_parameter_definitions(self) -> list[dict[str, Any]]:
        return self.tune_parameters.list_definitions()

    def list_tune_parameter_values(self, tune_id: str) -> list[dict[str, Any]]:
        return self.tune_parameters.list_values(tune_id)

    def save_tune_parameter_values(self, tune_id: str, values: list[dict[str, Any]]) -> bool:
        self.tune_parameters.save_values(tune_id, values)
        return True

    def ensure_default_recording_context(self, car_id: str) -> dict[str, Any]:
        return self.recording_context.ensure_default_context(car_id)

    def validate_recording_context(self, context: dict[str, Any]) -> dict[str, Any]:
        result = self.recording_context.validate(context)
        return {"is_valid": result.is_valid, "missing": result.missing, "context": result.context}

    def snapshot_vehicle_data_status(self, setup_snapshot_id: str) -> dict[str, Any]:
        if not setup_snapshot_id:
            return {
                "setup_snapshot_id": "",
                "is_complete": False,
                "saved_keys": [],
                "missing_keys": list(VEHICLE_DATA_REQUIRED_KEYS),
                "saved_count": 0,
                "required_count": len(VEHICLE_DATA_REQUIRED_KEYS),
            }
        rows = self._freeze.get_vehicle_data(setup_snapshot_id)
        saved_keys = {
            str(item.get("data_key") or "").strip()
            for item in rows
            if str(item.get("data_key") or "").strip() and str(item.get("value") or "").strip()
        }
        missing = [key for key in VEHICLE_DATA_REQUIRED_KEYS if key not in saved_keys]
        return {
            "setup_snapshot_id": setup_snapshot_id,
            "is_complete": len(missing) == 0,
            "saved_keys": sorted(saved_keys),
            "missing_keys": missing,
            "saved_count": len(saved_keys),
            "required_count": len(VEHICLE_DATA_REQUIRED_KEYS),
        }

    def snapshot_has_required_vehicle_data(self, setup_snapshot_id: str) -> bool:
        return bool(self.snapshot_vehicle_data_status(setup_snapshot_id).get("is_complete"))

    def count_runs_for_snapshot(self, setup_snapshot_id: str, include_archived: bool = False) -> int:
        return len(self.runs_repo.query_run_records(setup_snapshot_id=setup_snapshot_id, include_archived=include_archived))

    def data_ownership_lines(self) -> list[str]:
        return list(DATA_OWNERSHIP_LINES)

    def list_runs_for_car(self, car_id: str) -> list[dict[str, Any]]:
        return [self._legacy_run_dict(record) for record in self.runs_repo.query_run_records(car_id=car_id)]

    def list_runs_for_build(self, build_id: str) -> list[dict[str, Any]]:
        return [self._legacy_run_dict(record) for record in self.runs_repo.query_run_records(build_id=build_id)]

    def list_runs_for_tune(self, tune_id: str) -> list[dict[str, Any]]:
        return [self._legacy_run_dict(record) for record in self.runs_repo.query_run_records(tune_id=tune_id)]

    def list_dataset_groups_for_car(self, car_id: str) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for record in self.runs_repo.query_run_records(car_id=car_id, include_archived=True):
            key = "__".join([str(record.get("route_id") or "route_unset"), str(record.get("record_type") or "unknown")])
            group = groups.setdefault(
                key,
                {
                    "dataset_group_id": f"{car_id}__group__{key}",
                    "name": f"{record.get('route_name') or '未设置'} / {record.get('record_type') or 'unknown'}",
                    "route_name": record.get("route_name") or "未设置",
                    "purpose": "baseline",
                    "run_ids": [],
                    "status": "active",
                    "tags": [],
                    "notes": "",
                },
            )
            group["run_ids"].append(record["run_id"])
        return list(groups.values())

    def list_unassigned_runs(self) -> list[dict[str, Any]]:
        return []

    def list_all_runs(self) -> list[dict[str, Any]]:
        return self._load_runs()

    def search_runs(
        self,
        car_id: str = "",
        route: str = "",
        run_type: str = "",
        tags: list[str] | None = None,
        keyword: str = "",
    ) -> list[dict[str, Any]]:
        records = self.runs_repo.query_run_records(car_id=car_id, record_type=run_type, keyword=keyword)
        if route:
            kw = route.lower()
            records = [record for record in records if kw in str(record.get("route_name", "")).lower()]
        if tags:
            tag_set = set(tags)
            records = [record for record in records if tag_set & set(record.get("tag_keys", []))]
        return [self._legacy_run_dict(record) for record in records]

    def list_record_types(self) -> list[dict[str, Any]]:
        return self.record_types.list_all()

    def search_database_entities(self, keyword: str) -> list[dict[str, Any]]:
        """Search across tags, record_types, route_modes with entity_type."""
        results: list[dict[str, Any]] = []
        kw = keyword.strip().lower()
        if not kw:
            return results
        # Search tags
        for tag in self.tags.list_by_category(include_inactive=True):
            label = str(tag.get("label_zh") or "")
            key = str(tag.get("tag_key") or "")
            if kw in label.lower() or kw in key.lower():
                results.append({
                    "entity_type": "tag",
                    "entity_type_label": "标签",
                    "id": tag.get("tag_id"),
                    "label_zh": label,
                    "key": key,
                    "category": tag.get("category"),
                })
        # Search record_types
        for rt in self.record_types.list_all(include_inactive=True):
            label = str(rt.get("label_zh") or "")
            key = str(rt.get("record_type_key") or "")
            if kw in label.lower() or kw in key.lower():
                results.append({
                    "entity_type": "record_type",
                    "entity_type_label": "记录类型",
                    "id": rt.get("record_type_id"),
                    "label_zh": label,
                    "key": key,
                })
        # Search route_modes from routes table
        for route in self.routes_repo.list_routes(include_inactive=True):
            label = str(route.get("display_name") or "")
            mode = str(route.get("route_mode") or "")
            if kw in label.lower() or kw in mode.lower():
                results.append({
                    "entity_type": "route_mode",
                    "entity_type_label": "路线模式",
                    "id": route.get("route_id"),
                    "label_zh": label,
                    "key": mode,
                })
        return results

    def get_upgrade_categories(self, build_id: str = "") -> list[dict[str, Any]]:
        return self.upgrades.list_categories(build_id)

    def get_upgrade_categories_for_car(self, car_id: str) -> list[dict[str, Any]]:
        return self.upgrades.list_categories_for_car(car_id)

    def get_upgrade_slots_for_category(self, upgrade_category_id: str, build_id: str = "") -> list[dict[str, Any]]:
        return self.upgrades.list_slots(upgrade_category_id, build_id)

    def get_upgrade_slots_for_car(self, car_id: str, upgrade_category_id: str) -> list[dict[str, Any]]:
        return self.upgrades.list_slots_for_car(car_id, upgrade_category_id)

    def get_upgrade_options_for_slot(self, slot_id: str, build_id: str = "") -> list[dict[str, Any]]:
        return self.upgrades.list_options(slot_id, build_id)

    def get_upgrade_options_for_car(self, car_id: str, slot_id: str) -> list[dict[str, Any]]:
        return self.upgrades.list_options_for_car(car_id, slot_id)

    def get_upgrade_selection(self, build_id: str, slot_id: str) -> dict[str, Any] | None:
        return self.upgrades.get_selection(build_id, slot_id)

    def save_build_upgrade_selection(self, build_id: str, slot_id: str, option_id: str) -> dict[str, Any]:
        return self.upgrades.save_build_upgrade_selection(build_id, slot_id, option_id)

    def add_upgrade_category(self, category_key: str, label_zh: str, label_en: str = "", display_order: int = 0) -> dict[str, Any]:
        return self.upgrades.create_category(category_key, label_zh, label_en, display_order)

    def add_upgrade_slot(
        self,
        upgrade_category_id: str,
        slot_key: str,
        label_zh: str,
        label_en: str = "",
        sort_order: int = 0,
    ) -> dict[str, Any]:
        return self.upgrades.create_slot(upgrade_category_id, slot_key, label_zh, label_en, sort_order)

    def add_upgrade_option(
        self,
        upgrade_category_id: str,
        slot_id: str,
        option_key: str,
        label_zh: str,
        label_en: str = "",
        default_pi_delta: int | None = None,
        is_stock: bool = False,
        tier: int = 0,
    ) -> dict[str, Any]:
        return self.upgrades.create_option(
            upgrade_category_id=upgrade_category_id,
            slot_id=slot_id,
            option_key=option_key,
            label_zh=label_zh,
            label_en=label_en,
            default_pi_delta=default_pi_delta,
            is_stock=is_stock,
            tier=tier,
        )

    def set_car_upgrade_category_available(self, car_id: str, category_id: str, is_available: bool) -> None:
        self.upgrades.set_car_category_availability(car_id, category_id, is_available)

    def set_car_upgrade_slot_available(self, car_id: str, slot_id: str, is_available: bool) -> None:
        self.upgrades.set_car_slot_availability(car_id, slot_id, is_available)

    def set_car_upgrade_option_available(self, car_id: str, option_id: str, is_available: bool) -> None:
        self.upgrades.set_car_option_availability(car_id, option_id, is_available)

    def build_has_runs(self, build_id: str) -> bool:
        return len(self.list_runs_for_build(build_id)) > 0

    def tune_has_runs(self, tune_id: str) -> bool:
        return len(self.list_runs_for_tune(tune_id)) > 0

    def clone_build_with_selections(self, source_build_id: str, *, display_name: str | None = None) -> dict[str, Any]:
        source = self.builds.get_build(source_build_id)
        if not source:
            raise ValueError(f"build not found: {source_build_id}")
        car_id = str(source.get("car_id") or "")
        if not car_id:
            raise ValueError("source build missing car_id")
        stamp = utc_now().replace("-", "").replace(":", "").replace("T", "_").replace("Z", "")
        base_key = str(source.get("build_key") or "build")
        new_key = f"{base_key}_draft_{stamp}"
        new_name = display_name or f"{source.get('display_name') or 'Build'} Draft {stamp}"
        cloned = self.builds.create_build(
            car_id,
            {
                "display_name": new_name,
                "build_key": new_key,
                "status": "draft",
                "source": "clone_for_recording",
                "notes": f"cloned from {source_build_id}",
            },
        )
        self.builds.update_build(
            str(cloned["build_id"]),
            {
                "pi": source.get("pi"),
                "car_class": source.get("car_class"),
                "pi_source": source.get("pi_source") or "manual_total",
            },
        )
        for item in self.builds.list_upgrade_selections(source_build_id):
            option_id = str(item.get("upgrade_option_id") or "")
            slot_id = str(item.get("slot_id") or "")
            if option_id and slot_id:
                self.upgrades.save_build_upgrade_selection(str(cloned["build_id"]), slot_id, option_id)
        return self.builds.get_build(str(cloned["build_id"])) or cloned

    def clone_tune_with_values(
        self,
        source_tune_id: str,
        target_build_id: str,
        *,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        source = self.tunes.get_tune(source_tune_id)
        if not source:
            raise ValueError(f"tune not found: {source_tune_id}")
        stamp = utc_now().replace("-", "").replace(":", "").replace("T", "_").replace("Z", "")
        source_key = str(source.get("tune_key") or "tune")
        new_key = f"{source_key}_draft_{stamp}"
        new_name = display_name or f"{source.get('display_name') or 'Tune'} Draft"
        cloned = self.tunes.create_tune(
            target_build_id,
            {
                "display_name": new_name,
                "tune_key": new_key,
                "version": f"v{stamp[-4:]}",
                "status": "draft",
                "source": "clone_for_recording",
                "notes": f"cloned from {source_tune_id}",
            },
        )
        values = self.tune_parameters.list_values(source_tune_id)
        payload: list[dict[str, Any]] = []
        for row in values:
            payload.append(
                {
                    "tune_parameter_id": row.get("tune_parameter_id"),
                    "value_real": row.get("value_real"),
                    "value_text": row.get("value_text"),
                    "notes": row.get("notes") or "",
                }
            )
        if payload:
            self.tune_parameters.save_values(str(cloned["tune_id"]), payload)
        return self.tunes.get_tune(str(cloned["tune_id"])) or cloned

    def ensure_recording_draft_build(self, build_id: str) -> dict[str, Any]:
        if self.build_has_runs(build_id):
            return self.clone_build_with_selections(build_id)
        build = self.builds.get_build(build_id)
        if not build:
            raise ValueError(f"build not found: {build_id}")
        return build

    def ensure_recording_draft_tune(self, tune_id: str, target_build_id: str) -> dict[str, Any]:
        tune = self.tunes.get_tune(tune_id)
        if not tune:
            raise ValueError(f"tune not found: {tune_id}")
        tune_build_id = str(tune.get("build_id") or "")
        if tune_build_id != target_build_id or self.tune_has_runs(tune_id):
            return self.clone_tune_with_values(tune_id, target_build_id)
        return tune

    def create_new_recording_build(self, car_id: str) -> dict[str, Any]:
        base = self.builds.ensure_default_stock_build(car_id)
        base_id = str(base.get("build_id") or "")
        if not base_id:
            raise ValueError(f"default stock build missing for car: {car_id}")
        car = self.cars.get_car(car_id) or {}
        name = f"{car.get('display_name') or 'Car'} 记录前临时 Build"
        created = self.clone_build_with_selections(base_id, display_name=name)
        self.tunes.ensure_baseline_tune(str(created.get("build_id") or ""))
        return created

    def cleanup_draft_builds_without_runs(self, car_id: str) -> int:
        removed = 0
        for build in self.builds.list_by_car(car_id, include_archived=True):
            build_id = str(build.get("build_id") or "")
            if not build_id:
                continue
            is_draft = str(build.get("status") or "") == "draft" or "clone_for_recording" in str(build.get("source") or "")
            if not is_draft:
                continue
            if self.build_has_runs(build_id):
                continue
            for tune in self.tunes.list_by_build(build_id, include_archived=True):
                self.tunes.archive_tune(str(tune.get("tune_id") or ""))
            if self.builds.archive_build(build_id):
                removed += 1
        return removed

    def archive_build(self, build_id: str) -> bool:
        return self.builds.archive_build(build_id)

    def archive_tune(self, tune_id: str) -> bool:
        return self.tunes.archive_tune(tune_id)

    def can_delete_build(self, build_id: str) -> tuple[bool, str]:
        run_count = len(self.list_runs_for_build(build_id))
        if run_count > 0:
            return False, f"该 Build 已关联 {run_count} 条 Run，不能删除。"
        return True, ""

    def delete_build_if_no_runs(self, build_id: str) -> tuple[bool, str]:
        ok, reason = self.can_delete_build(build_id)
        if not ok:
            return False, reason
        for tune in self.tunes.list_by_build(build_id, include_archived=True):
            self.tunes.archive_tune(str(tune.get("tune_id") or ""))
        if not self.builds.archive_build(build_id):
            return False, "删除失败：数据库未更新。"
        return True, "Build 已删除。"

    def archive_build_with_related(self, build_id: str) -> tuple[bool, str]:
        build = self.builds.get_build(build_id)
        if not build:
            return False, "Build 不存在。"
        for run in self.list_runs_for_build(build_id):
            run_id = str(run.get("run_id") or run.get("session_id") or "")
            if run_id:
                self.archive_run(run_id)
        for tune in self.tunes.list_by_build(build_id, include_archived=True):
            tune_id = str(tune.get("tune_id") or "")
            if not tune_id:
                continue
            for snap in self.snapshots.list_by_tune(tune_id, include_archived=True):
                snap_id = str(snap.get("setup_snapshot_id") or "")
                if snap_id:
                    self.snapshots.update_snapshot(snap_id, {"is_active": 0, "notes": (snap.get("notes") or "") + " [archived_with_build]"})
            self.tunes.archive_tune(tune_id)
        self.builds.archive_build(build_id)
        return True, "Build 及关联 Run/Tune/Snapshot 已归档。"

    def list_routes(self) -> list[dict[str, Any]]:
        return self.routes_repo.list_routes()

    def create_route(self, display_name: str, route_mode: str, route_type: str = "road") -> dict[str, Any]:
        return self.routes_repo.create_route(
            {
                "display_name": display_name,
                "route_mode": route_mode or "timed_route",
                "route_type": route_type or "road",
                "source": "manual",
            }
        )

    def list_tags_by_category(self) -> dict[str, dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for row in self.tags.list_by_category(include_inactive=True):
            category = str(row.get("category") or "general_tag")
            spec = DICTIONARY_SPECS.get(category, {"name_zh": category, "name_en": category})
            group = grouped.setdefault(category, {"name_zh": spec["name_zh"], "name_en": spec["name_en"], "items": []})
            group["items"].append(
                {
                    "key": row.get("tag_key"),
                    "label_zh": row.get("label_zh") or row.get("tag_key"),
                    "label_en": row.get("label_en") or row.get("tag_key"),
                    "category": category,
                    "is_active": bool(row.get("is_active")),
                    "tag_id": row.get("tag_id"),
                }
            )
        return grouped

    def add_user_tag(self, category: str, key: str, label_zh: str) -> bool:
        try:
            self.tags.create_tag(category, key, label_zh, is_system=False)
            return True
        except Exception:
            return False

    def can_archive_tag(self, tag_id: str) -> tuple[bool, str]:
        usage = self.tags.tag_usage_counts(tag_id)
        if usage["run_tags"] > 0:
            return False, f"该标签已被 {usage['run_tags']} 条记录引用，不能删除。"
        if usage["annotation_tags"] > 0:
            return False, f"该标签已被 {usage['annotation_tags']} 条注释引用，不能删除。"
        return True, ""

    def archive_tag(self, tag_id: str) -> tuple[bool, str]:
        can_delete, reason = self.can_archive_tag(tag_id)
        if not can_delete:
            return False, reason
        ok = self.tags.archive_tag(tag_id)
        if not ok:
            return False, "删除失败：数据库未更新。"
        return True, "标签已删除。"

    def list_user_tags(self) -> list[dict[str, Any]]:
        return [
            {
                "key": row.get("tag_key"),
                "label_zh": row.get("label_zh") or row.get("tag_key"),
                "label_en": row.get("label_en") or row.get("tag_key"),
                "category": row.get("category"),
                "is_active": bool(row.get("is_active")),
                "tag_id": row.get("tag_id"),
            }
            for row in self.tags.list_by_category(include_inactive=True)
            if not row.get("is_system")
        ]

    def dashboard_stats(self) -> dict[str, Any]:
        cars = self.list_cars()
        all_runs = self.runs_repo.query_run_records(include_archived=True)
        active_runs = [run for run in all_runs if run.get("status") != "archived" and run.get("is_active")]
        return {
            "car_count": len(cars),
            "run_count": len(active_runs),
            "unassigned_run_count": 0,
            "recent_runs": [self._legacy_run_dict(run) for run in active_runs[:5]],
            "cars": cars,
            "build_count": sum(len(self.list_builds_for_car(str(car["car_id"]))) for car in cars),
            "setup_snapshot_count": len({run.get("setup_snapshot_id") for run in all_runs}),
        }

    def update_car(self, car_id: str, updates: dict) -> bool:
        mapped = dict(updates)
        if "performance_index" in mapped:
            mapped["default_pi"] = mapped.pop("performance_index")
        if "drivetrain" in mapped:
            mapped["default_drivetrain"] = mapped.pop("drivetrain")
        if "car_class" in mapped:
            mapped["default_car_class"] = mapped.pop("car_class")
        return self.cars.update_car(car_id, mapped)

    def update_run_notes(self, session_id: str, notes: str) -> bool:
        return self.runs_repo.update_run_notes(session_id, notes)

    def update_tune(self, tune_id: str, updates: dict[str, Any]) -> bool:
        return self.tunes.update_tune(tune_id, updates)

    def add_tag_to_run(self, session_id: str, tag_key: str) -> bool:
        tag_id = self._resolve_tag_id(tag_key)
        if not tag_id:
            tag = self.tags.create_tag("general_tag", tag_key, tag_key, is_system=False)
            tag_id = str(tag["tag_id"])
        return self.runs_repo.add_tag_to_run(session_id, tag_id)

    def add_tag_id_to_run(self, session_id: str, tag_id: str) -> bool:
        if not self.tags.get_tag(tag_id):
            return False
        return self.runs_repo.add_tag_to_run(session_id, tag_id)

    def remove_tag_from_run(self, session_id: str, tag_key: str) -> bool:
        tag_id = self._resolve_tag_id(tag_key)
        return self.runs_repo.remove_tag_from_run(session_id, tag_id) if tag_id else False

    def remove_tag_id_from_run(self, session_id: str, tag_id: str) -> bool:
        if not self.tags.get_tag(tag_id):
            return False
        return self.runs_repo.remove_tag_from_run(session_id, tag_id)

    def archive_run(self, session_id: str) -> bool:
        return self.runs_repo.archive_run(session_id)

    def create_run_from_recording(
        self,
        *,
        session_id: str,
        csv_path: str,
        context: dict[str, Any],
        packet_count: int = 0,
        duration_seconds: float = 0.0,
    ) -> dict[str, Any]:
        validation = self.recording_context.validate(context)
        if not validation.is_valid:
            raise ValueError("recording context incomplete: " + ", ".join(validation.missing))
        route_id = self._resolve_route_id(
            str(context.get("route_id") or "").strip(),
            str(context.get("route_mode") or "unset"),
        )
        intent_tag_ids = []
        for tag_key in validation.context.get("intent_tags", []):
            tag_id = self._resolve_tag_id(str(tag_key))
            if tag_id:
                intent_tag_ids.append(tag_id)
        if not intent_tag_ids:
            fallback_key = "uncategorized"
            fallback_tag = self.tags.tag_id_for_key(fallback_key, "intent_tag")
            if not fallback_tag:
                created = self.tags.create_tag("intent_tag", fallback_key, "未分类", is_system=False)
                fallback_tag = str(created.get("tag_id") or "")
            if fallback_tag:
                intent_tag_ids.append(str(fallback_tag))
        run = self.runs_repo.create_run(
            {
                "run_id": session_id,
                "session_id": session_id,
                "car_id": validation.context["car_id"],
                "build_id": validation.context["build_id"],
                "tune_id": validation.context["tune_id"],
                "setup_snapshot_id": validation.context["setup_snapshot_id"],
                "route_id": route_id,
                "route_mode": validation.context["route_mode"],
                "record_type": validation.context["record_type"],
                "raw_csv_path": self._relative_path(csv_path),
                "duration_seconds": duration_seconds,
                "packet_count": packet_count,
                "quality_status": "draft",
                "metrics_json": json.dumps(self._summarize_csv_metrics(csv_path), ensure_ascii=False),
                "notes": validation.context.get("notes") or "",
            },
            intent_tag_ids,
        )
        self.builds.update_build(validation.context["build_id"], {"status": "active", "is_active": 1})
        self.tunes.update_tune(validation.context["tune_id"], {"status": "active", "is_active": 1})
        return run

    def list_run_records(self, include_archived: bool = False) -> list[dict[str, Any]]:
        return self.runs_repo.query_run_records(include_archived=include_archived)

    def recompute_run_metrics(self, run_id: str) -> bool:
        run = self.get_run_detail(run_id)
        if not run:
            return False
        csv_path = str(run.get("raw_csv_path") or "").strip()
        if not csv_path:
            return False
        metrics = self._summarize_csv_metrics(csv_path)
        if not metrics:
            return False
        packet_count = int(metrics.get("packet_count") or run.get("packet_count") or 0)
        return self.runs_repo.update_run_metrics(
            str(run.get("run_id") or run.get("session_id") or run_id),
            json.dumps(metrics, ensure_ascii=False),
            packet_count=packet_count,
        )

    def metrics_need_unit_refresh(self, metrics_raw: Any) -> bool:
        if isinstance(metrics_raw, dict):
            metrics = metrics_raw
        else:
            text = str(metrics_raw or "").strip()
            if text in ("", "{}", "null"):
                return True
            try:
                metrics = json.loads(text)
            except Exception:
                return True
        return int(metrics.get("metrics_units_version") or 0) < METRICS_UNITS_VERSION

    def backfill_missing_run_metrics(self, *, record_type: str = "") -> int:
        updated = 0
        for run in self.runs_repo.query_run_records(include_archived=True, record_type=record_type):
            metrics_raw = run.get("metrics_json")
            has_metrics = False
            if isinstance(metrics_raw, dict):
                has_metrics = bool(metrics_raw)
            elif isinstance(metrics_raw, str):
                text = metrics_raw.strip()
                has_metrics = bool(text and text not in ("{}", "null"))
            if has_metrics:
                continue
            run_id = str(run.get("run_id") or run.get("session_id") or "")
            if run_id and self.recompute_run_metrics(run_id):
                updated += 1
        return updated

    @staticmethod
    def filter_run_records(
        records: list[dict[str, Any]],
        car_id: str = "",
        build_id: str = "",
        tune_id: str = "",
        setup_snapshot_id: str = "",
        route_mode: str = "",
        record_type: str = "",
        tag_keys: list[str] | None = None,
        tag_ids: list[str] | None = None,
        quality_status: str = "",
        keyword: str = "",
        tag_match_mode: str = "AND",
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        result = records
        if car_id:
            result = [r for r in result if r.get("car_id") == car_id]
        if build_id:
            result = [r for r in result if r.get("build_id") == build_id]
        if tune_id:
            result = [r for r in result if r.get("tune_id") == tune_id]
        if setup_snapshot_id:
            result = [r for r in result if r.get("setup_snapshot_id") == setup_snapshot_id]
        if route_mode:
            result = [r for r in result if r.get("route_mode") == route_mode]
        if record_type:
            result = [r for r in result if r.get("record_type") == record_type]
        if quality_status:
            result = [r for r in result if r.get("quality_status") == quality_status]
        if not include_archived:
            result = [r for r in result if r.get("status") != "archived" and r.get("is_active", True)]
        if tag_ids:
            tset = set(tag_ids)
            if tag_match_mode == "AND":
                result = [r for r in result if tset.issubset(set(r.get("tag_ids", [])))]
            else:
                result = [r for r in result if tset & set(r.get("tag_ids", []))]
        if tag_keys:
            tset = set(tag_keys)
            if tag_match_mode == "AND":
                result = [r for r in result if tset.issubset(set(r.get("tag_keys", [])))]
            else:
                result = [r for r in result if tset & set(r.get("tag_keys", []))]
        if keyword:
            kw = keyword.lower()
            result = [r for r in result if kw in str(r.get("search_text", "")).lower()]
        return result

    @staticmethod
    def run_display_title(run: dict) -> str:
        car = run.get("car_name", "未知车辆")
        route = run.get("route_name", "未知路线")
        rtype = run.get("run_type") or run.get("record_type") or ""
        type_label = DesktopDataService.TYPE_LABEL_MAP.get(rtype, rtype or "自由驾驶")
        return f"{car} · {route} · {type_label}"

    @staticmethod
    def run_subtitle(run: dict) -> str:
        sid = run.get("session_id", "")
        dur = float(run.get("duration_seconds", 0) or 0)
        quality = DesktopDataService.QUALITY_LABEL_MAP.get(run.get("quality_status", "unknown"), run.get("quality_status", "unknown"))
        return f"session: {sid}  |  {dur:.0f}s  |  {quality}"

    @classmethod
    def label_record_type(cls, key: str | None) -> str:
        return cls.TYPE_LABEL_MAP.get(str(key or ""), str(key or "未设置"))

    @classmethod
    def label_route_mode(cls, key: str | None) -> str:
        return cls.ROUTE_MODE_LABEL_MAP.get(str(key or ""), str(key or "未设置"))

    @classmethod
    def label_quality(cls, key: str | None) -> str:
        return cls.QUALITY_LABEL_MAP.get(str(key or ""), str(key or "未知"))

    def confirm_setup_snapshot(
        self,
        setup_snapshot_id: str,
        vehicle_data: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Confirm a snapshot: freeze build/tune/vehicle data, set confirmed_at."""
        snap = self.snapshots.get_snapshot(setup_snapshot_id)
        if not snap:
            return False
        build_id = str(snap.get("build_id") or "")
        tune_id = str(snap.get("tune_id") or "")

        # Freeze build items
        build_items = []
        for sel in self.builds.list_upgrade_selections(build_id):
            build_items.append({
                "category_label_zh": sel.get("category_label"),
                "slot_label_zh": sel.get("slot_label_zh"),
                "option_label_zh": sel.get("option_label"),
                "pi_delta": sel.get("pi_delta"),
                "unit": sel.get("unit"),
            })
        self._freeze.freeze_build_items(setup_snapshot_id, build_items)

        # Freeze tune values
        tune_values = []
        for val in self.tune_parameters.list_values(tune_id):
            value = val.get("value_real")
            if value is None:
                value = val.get("default_value")
            if value is None:
                value = val.get("min_value")
            tune_values.append({
                "section_label_zh": val.get("section_label_zh") or val.get("category"),
                "parameter_label_zh": val.get("label_zh"),
                "value": value,
                "unit": val.get("unit"),
            })
        self._freeze.freeze_tune_values(setup_snapshot_id, tune_values)

        # Freeze vehicle data
        self._freeze.freeze_vehicle_data(setup_snapshot_id, vehicle_data or [])

        # Generate frozen summary
        frozen_json = self._freeze.build_frozen_summary_json(setup_snapshot_id)

        # Confirm snapshot
        snap = self.snapshots.get_snapshot(setup_snapshot_id) or snap
        return self.snapshots.confirm_snapshot(
            setup_snapshot_id,
            confirmed_pi=snap.get("pi"),
            confirmed_class=snap.get("car_class"),
            frozen_summary_json=frozen_json,
        )

    def upsert_snapshot_vehicle_data(self, setup_snapshot_id: str, vehicle_data: list[dict[str, Any]]) -> bool:
        snap = self.snapshots.get_snapshot(setup_snapshot_id)
        if not snap:
            return False
        self._freeze.freeze_vehicle_data(setup_snapshot_id, vehicle_data or [])
        frozen_json = self._freeze.build_frozen_summary_json(setup_snapshot_id)
        return self.snapshots.confirm_snapshot(
            setup_snapshot_id,
            confirmed_pi=snap.get("pi"),
            confirmed_class=snap.get("car_class"),
            frozen_summary_json=frozen_json,
        )

    def get_run_detail(self, run_id: str) -> dict[str, Any] | None:
        """Return full run detail with joined names and tag items."""
        records = self.runs_repo.query_run_records(keyword="", include_archived=True)
        for r in records:
            if r.get("run_id") == run_id or r.get("session_id") == run_id:
                return r
        return None

    def copy_snapshot_context(self, source_snapshot_id: str, target_snapshot_id: str) -> bool:
        source = self.snapshots.get_snapshot(source_snapshot_id)
        target = self.snapshots.get_snapshot(target_snapshot_id)
        if not source or not target:
            return False
        self.snapshots.update_snapshot(
            target_snapshot_id,
            {
                "pi": source.get("pi"),
                "car_class": source.get("car_class"),
                "notes": source.get("notes") or "",
            },
        )
        vehicle_data = self._freeze.get_vehicle_data(source_snapshot_id)
        self.confirm_setup_snapshot(target_snapshot_id, vehicle_data)
        return True

    def _car_view_model(self, car: dict[str, Any]) -> dict[str, Any]:
        car_id = str(car.get("car_id") or "")
        runs = self.runs_repo.query_run_records(car_id=car_id)
        return {
            "car_id": car_id,
            "display_name": car.get("display_name", "未命名车辆"),
            "car_ordinal": car.get("car_ordinal"),
            "car_class": car.get("default_car_class") or "unknown",
            "performance_index": car.get("stock_pi") or car.get("default_pi") or 0,
            "drivetrain": car.get("default_drivetrain") or "unknown",
            "drivetrain_label": label_of("drivetrain", car.get("default_drivetrain") or "unknown"),
            "status": car.get("status", "active"),
            "run_count": len(runs),
            "tune_count": sum(len(self.tunes.list_by_build(str(build["build_id"]))) for build in self.builds.list_by_car(car_id)),
            "dataset_group_count": len(self.list_dataset_groups_for_car(car_id)),
            "avg_quality_score": 0.0,
            "avg_modeling_readiness": 0.0,
            "tags": [],
            "notes": car.get("notes", ""),
        }

    def _tune_versions_for_car(self, car_id: str) -> list[dict[str, Any]]:
        result = []
        for build in self.builds.list_by_car(car_id):
            result.extend(self.list_tunes_for_build(str(build["build_id"])))
        return result

    def _legacy_run_dict(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": record.get("session_id"),
            "run_id": record.get("run_id"),
            "created_at": record.get("created_at"),
            "created_at_utc": record.get("created_at"),
            "car_id": record.get("car_id"),
            "car_name": record.get("car_name"),
            "build_id": record.get("build_id"),
            "build_name": record.get("build_name"),
            "tune_id": record.get("tune_id"),
            "tune_name": record.get("tune_name"),
            "setup_snapshot_id": record.get("setup_snapshot_id"),
            "setup_snapshot_name": record.get("setup_snapshot_name"),
            "route_id": record.get("route_id"),
            "route_name": record.get("route_name"),
            "route_mode": record.get("route_mode"),
            "run_type": record.get("record_type"),
            "record_type": record.get("record_type"),
            "raw_csv_path": record.get("raw_csv_path", ""),
            "processed_csv_path": record.get("processed_csv_path", ""),
            "metrics_json": record.get("metrics_json", "{}"),
            "duration_seconds": record.get("duration_seconds", 0),
            "quality_status": record.get("quality_status", "unknown"),
            "tags": list(record.get("tag_keys") or []),
            "intent_tags": list(record.get("tag_keys") or []),
            "tag_keys": list(record.get("tag_keys") or []),
            "tag_ids": list(record.get("tag_ids") or []),
            "tag_labels": list(record.get("tag_labels") or []),
            "tag_items": list(record.get("tag_items") or []),
            "notes": record.get("notes", ""),
            "status": record.get("status", "active"),
            "is_active": record.get("is_active", True),
            "display_title": record.get("display_title"),
            "search_text": record.get("search_text", ""),
        }

    def _resolve_tag_id(self, tag_key: str) -> str | None:
        if "__" in tag_key and self.tags.get_tag(tag_key):
            return tag_key
        for category in ("intent_tag", "general_tag", "behavior_tag", "data_status", "quality_status"):
            tag_id = self.tags.tag_id_for_key(tag_key, category)
            if tag_id:
                return tag_id
        return None

    def _route_id_for_mode(self, route_mode: str) -> str:
        for route in self.routes_repo.list_routes(include_inactive=True):
            if route.get("route_mode") == route_mode:
                return str(route.get("route_id"))
        if route_mode == "free_drive":
            return "route_free_drive"
        if route_mode == "timed_route":
            return "route_horizon_highway_loop"
        return "route_unset"

    def _resolve_route_id(self, route_id: str, route_mode: str) -> str:
        routes = self.routes_repo.list_routes(include_inactive=True)
        existing_ids = {str(r.get("route_id") or "") for r in routes}
        if route_id and route_id in existing_ids:
            return route_id
        by_mode = self._route_id_for_mode(route_mode)
        if by_mode in existing_ids:
            return by_mode
        if routes:
            return str(routes[0].get("route_id") or "route_unset")
        return "route_unset"

    def _summarize_csv_metrics(self, csv_path: str) -> dict[str, Any]:
        path = Path(csv_path)
        if not path.exists():
            alt = self._root / str(csv_path)
            if alt.exists():
                path = alt
        if not path.exists():
            return {}
        packet_count = 0
        speed_max = speed_sum = 0.0
        rpm_max = rpm_sum = 0.0
        power_w_max = power_ps_max = torque_max = 0.0
        accel_x_g_max = accel_y_g_max = 0.0
        throttle_max = brake_max = 0.0
        slip_max = tire_temp_max = 0.0
        distance_max = 0.0
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                packet_count += 1
                speed_mps = self._optional_f(row.get("speed"))
                speed = speed_mps * 3.6 if speed_mps is not None else self._f(row.get("speed_kph"))
                rpm = self._f(row.get("current_engine_rpm"), self._f(row.get("engine_rpm")))
                power_w = self._optional_f(row.get("power"))
                if power_w is None:
                    power_kw = self._optional_f(row.get("power_kw"))
                    power_w = power_kw * 1000.0 if power_kw is not None else 0.0
                power_ps = power_w / WATTS_PER_METRIC_HP
                torque = self._f(row.get("torque"))
                accel_x = abs(self._f(row.get("acceleration_x"), self._f(row.get("accel_x")))) / G_FORCE
                accel_y = abs(self._f(row.get("acceleration_y"), self._f(row.get("accel_y")))) / G_FORCE
                throttle = self._f(row.get("accel"), self._f(row.get("throttle")))
                brake = self._f(row.get("brake"))
                distance = self._f(row.get("distance_traveled"))
                slip = max(
                    abs(self._f(row.get("tire_slip_ratio_front_left"))),
                    abs(self._f(row.get("tire_slip_ratio_front_right"))),
                    abs(self._f(row.get("tire_slip_ratio_rear_left"))),
                    abs(self._f(row.get("tire_slip_ratio_rear_right"))),
                )
                tire_temp = max(
                    self._f(row.get("tire_temp_front_left")),
                    self._f(row.get("tire_temp_front_right")),
                    self._f(row.get("tire_temp_rear_left")),
                    self._f(row.get("tire_temp_rear_right")),
                )
                speed_max = max(speed_max, speed)
                speed_sum += speed
                rpm_max = max(rpm_max, rpm)
                rpm_sum += rpm
                power_w_max = max(power_w_max, power_w)
                power_ps_max = max(power_ps_max, power_ps)
                torque_max = max(torque_max, torque)
                accel_x_g_max = max(accel_x_g_max, accel_x)
                accel_y_g_max = max(accel_y_g_max, accel_y)
                throttle_max = max(throttle_max, throttle)
                brake_max = max(brake_max, brake)
                slip_max = max(slip_max, slip)
                tire_temp_max = max(tire_temp_max, tire_temp)
                distance_max = max(distance_max, distance)
        if packet_count <= 0:
            return {}
        return {
            "metrics_units_version": METRICS_UNITS_VERSION,
            "packet_count": packet_count,
            "max_speed_kph": round(speed_max, 3),
            "avg_speed_kph": round(speed_sum / packet_count, 3),
            "max_rpm": round(rpm_max, 3),
            "avg_rpm": round(rpm_sum / packet_count, 3),
            "max_power_ps": round(power_ps_max, 3),
            "max_power_w": round(power_w_max, 3),
            "max_torque_nm": round(torque_max, 3),
            "max_longitudinal_g": round(accel_x_g_max, 4),
            "max_lateral_g": round(accel_y_g_max, 4),
            "max_throttle": round(throttle_max, 3),
            "max_brake": round(brake_max, 3),
            "max_tire_slip": round(slip_max, 4),
            "max_tire_temp": round(tire_temp_max, 3),
            "distance_m": round(distance_max, 3),
        }

    def _relative_path(self, path: str) -> str:
        try:
            return str(Path(path).resolve().relative_to(self._root.resolve()))
        except Exception:
            return path

    @staticmethod
    def _f(value: Any, fallback: float = 0.0) -> float:
        try:
            if value in (None, ""):
                return fallback
            return float(value)
        except Exception:
            return fallback

    @staticmethod
    def _optional_f(value: Any) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except Exception:
            return None
