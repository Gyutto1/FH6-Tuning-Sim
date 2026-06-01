from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from fh6_tuning_sim.data_management.annotation_store import read_annotations
from fh6_tuning_sim.data_management.dictionaries import DICTIONARY_SPECS, read_dictionary_items
from fh6_tuning_sim.data_management.platform_store import read_platform
from fh6_tuning_sim.data_management.run_index import read_index
from fh6_tuning_sim.data_management.session_naming import sanitize_filename
from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, ROOT, connect
from fh6_tuning_sim.db.migrations import foreign_key_check, init_schema

DEFAULT_BUILD_KEY = "default_stock_build"
DEFAULT_TUNE_KEY = "baseline_tune"
DEFAULT_SETUP_KEY = "default_setup_snapshot"
DEFAULT_INTENT_TAG_ID = "intent_tag__normal_driving"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)


def _copy_backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".bak.{ts}{path.suffix}")
    shutil.copy2(path, backup)
    return backup


def _clean_key(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return sanitize_filename(text if text else default)


def default_build_id(car_id: str) -> str:
    return f"{car_id}__build__{DEFAULT_BUILD_KEY}"


def default_tune_id(car_id: str, tune_name: str | None = None, legacy_tune_id: str | None = None) -> str:
    if legacy_tune_id:
        return str(legacy_tune_id)
    return f"{car_id}__tune__{_clean_key(tune_name, DEFAULT_TUNE_KEY)}__v00"


def default_setup_snapshot_id(car_id: str, build_id: str, tune_id: str) -> str:
    return f"{car_id}__setup__{sanitize_filename(build_id)}__{sanitize_filename(tune_id)}__default"


def _route_mode(run: dict[str, Any]) -> str:
    explicit = str(run.get("route_mode") or "").strip()
    if explicit:
        return explicit
    route = str(run.get("route_name") or "").strip().lower()
    if route in {"", "unknown", "未设置", "unset"}:
        return "unset"
    if route in {"free_drive", "free_roam", "自由驾驶"}:
        return "free_drive"
    return "timed_route"


def _route_id_for_mode(route_mode: str) -> str:
    if route_mode == "free_drive":
        return "route_free_drive"
    if route_mode == "timed_route":
        return "route_horizon_highway_loop"
    return "route_unset"


def _table_count(conn, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _insert_base_routes(conn, now: str) -> None:
    routes = [
        ("route_unset", "unset", "未设置", "unset", "unknown", "unknown"),
        ("route_free_drive", "free_drive", "自由驾驶", "free_drive", "unknown", "open_route"),
        ("route_horizon_highway_loop", "horizon_highway_loop", "高速环线", "timed_route", "asphalt", "circuit"),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO routes (
            route_id, route_key, display_name, route_mode, surface_type, route_type,
            source, notes, is_active, created_at_utc, updated_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, 'seed', '', 1, ?, ?)
        """,
        [(rid, key, name, mode, surface, rtype, now, now) for rid, key, name, mode, surface, rtype in routes],
    )


def _insert_upgrade_categories(conn) -> None:
    categories = [
        ("upgrade_engine", "engine", "发动机", "Engine", 10),
        ("upgrade_aspiration", "aspiration", "进气/增压", "Aspiration", 20),
        ("upgrade_tires", "tires", "轮胎", "Tires", 30),
        ("upgrade_transmission", "transmission", "传动", "Transmission", 40),
        ("upgrade_suspension", "suspension", "悬挂", "Suspension", 50),
        ("upgrade_brakes", "brakes", "刹车", "Brakes", 60),
        ("upgrade_differential", "differential", "差速器", "Differential", 70),
        ("upgrade_aero", "aero", "空气动力", "Aero", 80),
        ("upgrade_weight_reduction", "weight_reduction", "减重", "Weight Reduction", 90),
        ("upgrade_conversion", "conversion", "转换", "Conversion", 100),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO upgrade_categories (
            upgrade_category_id, category_key, label_zh, label_en, display_order, description, is_active
        ) VALUES (?, ?, ?, ?, ?, '', 1)
        """,
        categories,
    )


def _insert_dictionary_tags(conn, now: str) -> None:
    for category in DICTIONARY_SPECS:
        try:
            items = read_dictionary_items(category, include_inactive=True)
        except Exception:
            continue
        for item in items:
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO tags (
                    tag_id, tag_key, category, label_zh, label_en, description, is_system,
                    is_active, display_order, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    f"{category}__{key}",
                    key,
                    category,
                    str(item.get("label_zh") or key),
                    str(item.get("label_en") or key),
                    str(item.get("description_zh") or ""),
                    1 if item.get("is_active", True) else 0,
                    int(item.get("sort_order") or 0),
                    now,
                    now,
                ),
            )


def _upsert_car(conn, car: dict[str, Any], now: str) -> None:
    conn.execute(
        """
        INSERT INTO cars (
            car_id, display_name, car_ordinal, car_group, default_car_class, default_pi,
            default_drivetrain, status, is_active, notes, source, created_at_utc, updated_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'legacy_json', ?, ?)
        ON CONFLICT(car_id) DO UPDATE SET
            display_name=excluded.display_name,
            car_ordinal=COALESCE(excluded.car_ordinal, cars.car_ordinal),
            car_group=COALESCE(excluded.car_group, cars.car_group),
            default_car_class=COALESCE(excluded.default_car_class, cars.default_car_class),
            default_pi=COALESCE(excluded.default_pi, cars.default_pi),
            default_drivetrain=COALESCE(excluded.default_drivetrain, cars.default_drivetrain),
            status=excluded.status,
            is_active=excluded.is_active,
            notes=excluded.notes,
            updated_at_utc=excluded.updated_at_utc
        """,
        (
            car.get("car_id"),
            car.get("display_name") or "未命名车辆",
            car.get("car_ordinal"),
            car.get("car_group"),
            str(car.get("car_class") or "unknown"),
            car.get("performance_index"),
            car.get("drivetrain") or "unknown",
            car.get("status") or "active",
            0 if car.get("is_active") is False else 1,
            car.get("notes") or "",
            now,
            now,
        ),
    )


def _ensure_context_for_run(conn, run: dict[str, Any], platform_cars: dict[str, dict[str, Any]], now: str) -> tuple[str, str, str, str]:
    car_id = str(run.get("car_id") or "").strip()
    if not car_id:
        car_id = f"car_{_clean_key(run.get('car_name'), 'unknown_car')}"
    car = platform_cars.get(car_id) or {
        "car_id": car_id,
        "display_name": run.get("car_name") or "未命名车辆",
        "car_ordinal": run.get("car_ordinal") or run.get("detected_car_ordinal"),
        "car_group": run.get("car_group") or run.get("detected_car_group"),
        "car_class": run.get("car_class") or run.get("detected_car_class"),
        "performance_index": run.get("performance_index") or run.get("detected_performance_index"),
        "drivetrain": run.get("drivetrain") or run.get("detected_drivetrain"),
        "status": "active",
        "notes": "",
    }
    _upsert_car(conn, car, now)

    build_id = default_build_id(car_id)
    conn.execute(
        """
        INSERT OR IGNORE INTO builds (
            build_id, car_id, display_name, build_key, status, is_active, notes, source,
            created_at_utc, updated_at_utc
        ) VALUES (?, ?, '原厂默认', ?, 'active', 1, '', 'legacy_json', ?, ?)
        """,
        (build_id, car_id, DEFAULT_BUILD_KEY, now, now),
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO build_snapshots (
            build_snapshot_id, build_id, snapshot_name, pi, car_class, drivetrain, power,
            torque, weight, tire_compound, upgrade_summary, source, notes, created_at_utc
        ) VALUES (?, ?, '原厂默认快照', ?, ?, ?, NULL, NULL, NULL, NULL, ?, 'legacy_json', '', ?)
        """,
        (
            f"{build_id}__snapshot__default",
            build_id,
            run.get("performance_index") or run.get("detected_performance_index"),
            str(run.get("car_class") or run.get("detected_car_class") or "unknown"),
            run.get("drivetrain") or run.get("detected_drivetrain") or "unknown",
            _json_dumps({"source": "legacy_default_stock_build"}),
            now,
        ),
    )

    tune_id = default_tune_id(car_id, run.get("tune_name"), run.get("tune_id"))
    tune_key = _clean_key(run.get("tune_name"), DEFAULT_TUNE_KEY)
    conn.execute(
        """
        INSERT OR IGNORE INTO tunes (
            tune_id, build_id, display_name, tune_key, version, status, is_active, notes,
            source, created_at_utc, updated_at_utc
        ) VALUES (?, ?, ?, ?, ?, 'active', 1, '', 'legacy_json', ?, ?)
        """,
        (
            tune_id,
            build_id,
            run.get("tune_name") or "baseline_tune",
            tune_key,
            run.get("tune_version") or "v00",
            now,
            now,
        ),
    )

    setup_snapshot_id = default_setup_snapshot_id(car_id, build_id, tune_id)
    ratings = {
        "speed": None,
        "handling": None,
        "acceleration": None,
        "launch": None,
        "braking": None,
        "offroad": None,
    }
    conn.execute(
        """
        INSERT OR IGNORE INTO setup_snapshots (
            setup_snapshot_id, car_id, build_id, tune_id, snapshot_name, pi, car_class,
            drivetrain, power, torque, weight, front_weight_percent, tire_compound,
            performance_ratings, source, notes, is_active, created_at_utc, updated_at_utc
        ) VALUES (?, ?, ?, ?, '默认记录前快照', ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, 'imported', '', 1, ?, ?)
        """,
        (
            setup_snapshot_id,
            car_id,
            build_id,
            tune_id,
            run.get("performance_index") or run.get("detected_performance_index"),
            str(run.get("car_class") or run.get("detected_car_class") or "unknown"),
            run.get("drivetrain") or run.get("detected_drivetrain") or "unknown",
            _json_dumps(ratings),
            now,
            now,
        ),
    )
    return car_id, build_id, tune_id, setup_snapshot_id


def migrate_legacy_json(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    root: str | Path = ROOT,
    backup_existing_db: bool = True,
) -> dict[str, Any]:
    """Import legacy JSON indexes into SQLite without modifying the JSON files."""
    root_path = Path(root)
    db_file = Path(db_path)
    backups: list[str] = []
    if backup_existing_db and db_file.exists():
        backup = _copy_backup(db_file)
        if backup:
            backups.append(str(backup))

    init_schema(db_file)
    platform = read_platform(root_path / "data" / "platform" / "platform_index.json")
    runs = read_index(root_path / "data" / "index" / "runs_index.json")
    annotations = read_annotations(root_path / "data" / "index" / "annotations.json")
    platform_cars = {str(car.get("car_id")): car for car in platform.get("cars", []) if car.get("car_id")}
    now = utc_now()

    conn = connect(db_file)
    try:
        conn.execute("BEGIN")
        _insert_base_routes(conn, now)
        _insert_upgrade_categories(conn)
        _insert_dictionary_tags(conn, now)

        for car in platform.get("cars", []):
            if car.get("car_id"):
                _upsert_car(conn, car, now)

        for run in runs:
            session_id = str(run.get("session_id") or "").strip()
            if not session_id:
                continue
            car_id, build_id, tune_id, setup_snapshot_id = _ensure_context_for_run(conn, run, platform_cars, now)
            route_mode = _route_mode(run)
            route_id = _route_id_for_mode(route_mode)
            run_id = session_id
            quality_payload = {
                "quality": run.get("quality", {}),
                "state_tag_counts": run.get("state_tag_counts", {}),
                "laps": run.get("laps", []),
                "segments": run.get("segments", []),
            }
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, session_id, car_id, build_id, tune_id, setup_snapshot_id, route_id,
                    route_mode, record_type, use_case, raw_csv_path, processed_csv_path, plot_path,
                    report_path, dataset_path, metadata_path, tune_snapshot_path, duration_seconds,
                    packet_count, estimated_sample_rate, quality_status, quality_warnings,
                    metrics_json, notes, review_notes, status, is_active, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    car_id=excluded.car_id,
                    build_id=excluded.build_id,
                    tune_id=excluded.tune_id,
                    setup_snapshot_id=excluded.setup_snapshot_id,
                    route_id=excluded.route_id,
                    route_mode=excluded.route_mode,
                    record_type=excluded.record_type,
                    notes=excluded.notes,
                    review_notes=excluded.review_notes,
                    status=excluded.status,
                    is_active=excluded.is_active,
                    updated_at_utc=excluded.updated_at_utc
                """,
                (
                    run_id,
                    session_id,
                    car_id,
                    build_id,
                    tune_id,
                    setup_snapshot_id,
                    route_id,
                    route_mode,
                    run.get("run_type") or "normal_recording",
                    run.get("use_case"),
                    run.get("raw_csv_path"),
                    run.get("processed_csv_path"),
                    run.get("plot_path"),
                    run.get("report_path"),
                    run.get("dataset_path"),
                    run.get("metadata_path"),
                    run.get("tune_snapshot_path"),
                    run.get("duration_seconds"),
                    run.get("packet_count"),
                    run.get("estimated_sample_rate"),
                    run.get("quality_status"),
                    _json_dumps(run.get("quality_warnings", [])),
                    _json_dumps(quality_payload),
                    run.get("notes") or "",
                    run.get("review_notes") or "",
                    run.get("status") or "active",
                    0 if run.get("is_active") is False else 1,
                    run.get("created_at") or now,
                    now,
                ),
            )
            tag_ids = []
            for tag_key in (run.get("intent_tags") or []) + (run.get("tags") or []):
                tag_key = str(tag_key).strip()
                if not tag_key:
                    continue
                tag_ids.append(f"intent_tag__{tag_key}")
                tag_ids.append(f"general_tag__{tag_key}")
            existing = [tag_id for tag_id in tag_ids if conn.execute("SELECT 1 FROM tags WHERE tag_id = ?", (tag_id,)).fetchone()]
            if not existing:
                existing = [DEFAULT_INTENT_TAG_ID]
            for tag_id in sorted(set(existing)):
                conn.execute(
                    "INSERT OR IGNORE INTO run_tags (run_id, tag_id, tag_role, created_at_utc) VALUES (?, ?, 'intent', ?)",
                    (run_id, tag_id, now),
                )

        for annotation in annotations:
            annotation_id = annotation.get("annotation_id")
            if not annotation_id:
                continue
            run_id = annotation.get("run_id") or annotation.get("target_id")
            if run_id and not conn.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone():
                run_id = None
            conn.execute(
                """
                INSERT OR IGNORE INTO annotations (
                    annotation_id, target_type, target_id, run_id, start_time, end_time, source,
                    confidence, note, payload_json, is_active, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    annotation_id,
                    annotation.get("target_type") or "run",
                    annotation.get("target_id") or "",
                    run_id,
                    annotation.get("start_time"),
                    annotation.get("end_time"),
                    annotation.get("source") or "manual",
                    annotation.get("confidence") or 1.0,
                    annotation.get("note") or "",
                    _json_dumps({"legacy_tag_ids": annotation.get("tag_ids", [])}),
                    0 if annotation.get("is_active") is False else 1,
                    annotation.get("created_at_utc") or now,
                    annotation.get("updated_at_utc") or now,
                ),
            )
            for tag_key in annotation.get("tag_ids", []) or []:
                candidates = [f"intent_tag__{tag_key}", f"general_tag__{tag_key}", f"behavior_tag__{tag_key}"]
                tag_id = next((candidate for candidate in candidates if conn.execute("SELECT 1 FROM tags WHERE tag_id = ?", (candidate,)).fetchone()), None)
                if tag_id:
                    conn.execute(
                        "INSERT OR IGNORE INTO annotation_tags (annotation_id, tag_id) VALUES (?, ?)",
                        (annotation_id, tag_id),
                    )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    conn = connect(db_file)
    try:
        counts = {
            "cars": _table_count(conn, "cars"),
            "builds": _table_count(conn, "builds"),
            "tunes": _table_count(conn, "tunes"),
            "setup_snapshots": _table_count(conn, "setup_snapshots"),
            "runs": _table_count(conn, "runs"),
            "tags": _table_count(conn, "tags"),
            "annotations": _table_count(conn, "annotations"),
        }
        orphan_runs = int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM runs
                WHERE car_id IS NULL OR build_id IS NULL OR tune_id IS NULL OR setup_snapshot_id IS NULL
                   OR car_id = '' OR build_id = '' OR tune_id = '' OR setup_snapshot_id = ''
                """
            ).fetchone()[0]
        )
    finally:
        conn.close()

    return {
        "db_path": str(db_file),
        "legacy_cars": len(platform.get("cars", [])),
        "legacy_runs": len(runs),
        "counts": counts,
        "foreign_key_check": foreign_key_check(db_file),
        "orphan_runs": orphan_runs,
        "backups": backups,
    }
