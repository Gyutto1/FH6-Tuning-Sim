from __future__ import annotations

from pathlib import Path
import json

from fh6_tuning_sim.db.connection import DEMO_DB_PATH, connect
from fh6_tuning_sim.db.migrations import init_schema
from fh6_tuning_sim.db.migration_v4_client_rewire import migrate_v4_client_rewire


def _ratings() -> str:
    return json.dumps(
        {
            "speed": 8.0,
            "handling": 7.5,
            "acceleration": 8.2,
            "launch": 7.1,
            "braking": 7.4,
            "offroad": 3.0,
        },
        ensure_ascii=False,
    )


def seed_demo_database(db_path: str | Path = DEMO_DB_PATH) -> dict[str, int]:
    """Create deterministic demo data for Desktop smoke tests."""
    init_schema(db_path)
    migrate_v4_client_rewire(db_path)
    now = "2026-05-31T00:00:00+00:00"
    conn = connect(db_path)
    try:
        conn.execute("BEGIN")
        cars = [
            ("car_demo_amg", "Mercedes-AMG GT", 4265, 43, "S1", 900, "RWD"),
            ("car_demo_miata", "Mazda MX-5 Demo", 1001, 12, "A", 800, "RWD"),
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO cars (
                car_id, display_name, car_ordinal, car_group, default_car_class,
                stock_pi, default_pi, default_drivetrain, status, is_active, notes, source,
                created_at_utc, updated_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, '', 'demo_seed', ?, ?)
            """,
            [(car_id, name, ordinal, group, cls, pi, pi, drive, now, now) for car_id, name, ordinal, group, cls, pi, drive in cars],
        )

        builds = [
            ("build_amg_stock", "car_demo_amg", "原厂默认", "default_stock_build"),
            ("build_amg_stage2", "car_demo_amg", "Stage 2 AWD", "stage_2_awd"),
            ("build_miata_stock", "car_demo_miata", "原厂默认", "default_stock_build"),
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO builds (
                build_id, car_id, display_name, build_key, status, is_active, notes, source,
                created_at_utc, updated_at_utc
            ) VALUES (?, ?, ?, ?, 'active', 1, '', 'demo_seed', ?, ?)
            """,
            [(bid, cid, name, key, now, now) for bid, cid, name, key in builds],
        )

        tunes = [
            ("tune_amg_stock_baseline", "build_amg_stock", "baseline_tune", "baseline_tune", "v00"),
            ("tune_amg_stock_stable", "build_amg_stock", "high_speed_stability", "high_speed_stability", "v01"),
            ("tune_amg_stage2_baseline", "build_amg_stage2", "stage2_baseline", "stage2_baseline", "v00"),
            ("tune_miata_baseline", "build_miata_stock", "baseline_tune", "baseline_tune", "v00"),
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO tunes (
                tune_id, build_id, display_name, tune_key, version, status, is_active,
                notes, source, created_at_utc, updated_at_utc
            ) VALUES (?, ?, ?, ?, ?, 'active', 1, '', 'demo_seed', ?, ?)
            """,
            [(tid, bid, name, key, version, now, now) for tid, bid, name, key, version in tunes],
        )

        snapshots = [
            ("setup_amg_stock_baseline", "car_demo_amg", "build_amg_stock", "tune_amg_stock_baseline", "AMG Stock Baseline", 900, "S1", "RWD"),
            ("setup_amg_stock_stable", "car_demo_amg", "build_amg_stock", "tune_amg_stock_stable", "AMG Stable", 900, "S1", "RWD"),
            ("setup_amg_stage2", "car_demo_amg", "build_amg_stage2", "tune_amg_stage2_baseline", "AMG Stage 2", 950, "S1", "AWD"),
            ("setup_miata_baseline", "car_demo_miata", "build_miata_stock", "tune_miata_baseline", "Miata Baseline", 800, "A", "RWD"),
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO setup_snapshots (
                setup_snapshot_id, car_id, build_id, tune_id, snapshot_name, pi, car_class,
                drivetrain, power, torque, weight, front_weight_percent, tire_compound,
                performance_ratings, source, notes, is_active, created_at_utc, updated_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 520, 650, 1500, 52, 'sport', ?, 'demo_seed', '', 1, ?, ?)
            """,
            [(sid, cid, bid, tid, name, pi, cls, drive, _ratings(), now, now) for sid, cid, bid, tid, name, pi, cls, drive in snapshots],
        )

        routes = [
            ("route_horizon_loop", "horizon_highway_loop", "高速环线", "timed_route", "asphalt", "circuit"),
            ("route_free_drive", "free_drive", "自由驾驶", "free_drive", "unknown", "open_route"),
            ("route_unset", "unset", "未设置", "unset", "unknown", "unknown"),
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO routes (
                route_id, route_key, display_name, route_mode, surface_type, route_type,
                source, notes, is_active, created_at_utc, updated_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, 'demo_seed', '', 1, ?, ?)
            """,
            [(rid, key, name, mode, surface, rtype, now, now) for rid, key, name, mode, surface, rtype in routes],
        )

        tags = [
            ("intent_tag__normal_driving", "normal_driving", "intent_tag", "普通行驶"),
            ("intent_tag__baseline", "baseline", "intent_tag", "基准"),
            ("intent_tag__full_lap", "full_lap", "intent_tag", "整跑"),
            ("intent_tag__free_drive", "free_drive", "intent_tag", "自由驾驶测试"),
            ("intent_tag__heavy_braking", "heavy_braking", "intent_tag", "重刹"),
            ("behavior_tag__understeer", "understeer", "behavior_tag", "推头"),
            ("behavior_tag__oversteer", "oversteer", "behavior_tag", "甩尾"),
            ("general_tag__needs_review", "needs_review", "general_tag", "需要复查"),
            ("quality_status__good", "good", "quality_status", "良好"),
            ("quality_status__warning", "warning", "quality_status", "注意"),
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO tags (
                tag_id, tag_key, category, label_zh, label_en, description, is_system,
                is_active, display_order, created_at_utc, updated_at_utc
            ) VALUES (?, ?, ?, ?, ?, '', 1, 1, 0, ?, ?)
            """,
            [(tag_id, key, category, label, key, now, now) for tag_id, key, category, label in tags],
        )

        run_specs = [
            ("demo_run_01", "car_demo_amg", "build_amg_stock", "tune_amg_stock_baseline", "setup_amg_stock_baseline", "route_horizon_loop", "timed_route", "full_lap", "active", 1, "baseline highway lap"),
            ("demo_run_02", "car_demo_amg", "build_amg_stock", "tune_amg_stock_baseline", "setup_amg_stock_baseline", "route_horizon_loop", "timed_route", "full_lap", "active", 1, "keyword brake stability"),
            ("demo_run_03", "car_demo_amg", "build_amg_stock", "tune_amg_stock_stable", "setup_amg_stock_stable", "route_horizon_loop", "timed_route", "full_lap", "active", 1, "stable tune"),
            ("demo_run_04", "car_demo_amg", "build_amg_stage2", "tune_amg_stage2_baseline", "setup_amg_stage2", "route_horizon_loop", "timed_route", "full_lap", "active", 1, "stage 2"),
            ("demo_run_05", "car_demo_amg", "build_amg_stage2", "tune_amg_stage2_baseline", "setup_amg_stage2", "route_free_drive", "free_drive", "free_drive", "active", 1, "free roam run"),
            ("demo_run_06", "car_demo_amg", "build_amg_stock", "tune_amg_stock_baseline", "setup_amg_stock_baseline", "route_unset", "unset", "normal_recording", "active", 1, "unset route run"),
            ("demo_run_07", "car_demo_miata", "build_miata_stock", "tune_miata_baseline", "setup_miata_baseline", "route_horizon_loop", "timed_route", "full_lap", "active", 1, "miata baseline"),
            ("demo_run_08", "car_demo_miata", "build_miata_stock", "tune_miata_baseline", "setup_miata_baseline", "route_free_drive", "free_drive", "free_drive", "active", 1, "miata free roam"),
            ("demo_run_09", "car_demo_amg", "build_amg_stock", "tune_amg_stock_baseline", "setup_amg_stock_baseline", "route_horizon_loop", "timed_route", "heavy_braking", "archived", 0, "archived braking run"),
            ("demo_run_10", "car_demo_miata", "build_miata_stock", "tune_miata_baseline", "setup_miata_baseline", "route_unset", "unset", "normal_recording", "active", 1, "needs review unset"),
        ]
        for idx, (run_id, car_id, build_id, tune_id, setup_id, route_id, route_mode, record_type, status, active, notes) in enumerate(run_specs, start=1):
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, session_id, car_id, build_id, tune_id, setup_snapshot_id, route_id,
                    route_mode, record_type, use_case, raw_csv_path, processed_csv_path, plot_path,
                    report_path, dataset_path, metadata_path, tune_snapshot_path, duration_seconds,
                    packet_count, estimated_sample_rate, quality_status, quality_warnings,
                    metrics_json, notes, review_notes, status, is_active, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'demo', NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                    ?, ?, 60.0, ?, '[]', '{}', ?, '', ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run_id,
                    car_id,
                    build_id,
                    tune_id,
                    setup_id,
                    route_id,
                    route_mode,
                    record_type,
                    120.0 + idx,
                    7200 + idx,
                    "warning" if route_mode == "unset" else "good",
                    notes,
                    status,
                    active,
                    f"2026-05-31T00:{idx:02d}:00+00:00",
                    now,
                ),
            )
            tag_id = "intent_tag__free_drive" if route_mode == "free_drive" else "intent_tag__full_lap"
            if record_type == "heavy_braking":
                tag_id = "intent_tag__heavy_braking"
            if record_type == "normal_recording":
                tag_id = "intent_tag__normal_driving"
            conn.execute(
                "INSERT OR REPLACE INTO run_tags (run_id, tag_id, tag_role, created_at_utc) VALUES (?, ?, 'intent', ?)",
                (run_id, tag_id, now),
            )
        conn.execute(
            """
            INSERT OR REPLACE INTO experiment_matrices (
                experiment_matrix_id, car_id, display_name, purpose, status, payload_json,
                notes, is_active, created_at_utc, updated_at_utc
            ) VALUES ('matrix_demo_amg', 'car_demo_amg', 'AMG 测试矩阵占位', 'placeholder',
                'draft', '{}', '0.99 beta placeholder', 1, ?, ?)
            """,
            (now, now),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    conn = connect(db_path)
    try:
        tables = ["cars", "builds", "tunes", "setup_snapshots", "routes", "runs", "tags"]
        return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
    finally:
        conn.close()


if __name__ == "__main__":
    counts = seed_demo_database()
    print(counts)
