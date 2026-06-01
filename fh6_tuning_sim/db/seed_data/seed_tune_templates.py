from __future__ import annotations

from pathlib import Path

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.migration_v2_phase2 import migrate_phase2


def seed_tune_templates(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Seed default tune sections and parameter definitions (AMG GT reference)."""
    migrate_phase2(db_path)

    conn = connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM tune_sections").fetchone()[0]
    if count > 0:
        conn.close()
        return
    conn.close()

    with transaction(db_path) as conn:
        # Tune sections
        sections = [
            ("ts_tires", "tires", "轮胎", "Tires", 1),
            ("ts_gearing", "gearing", "齿轮", "Gearing", 2),
            ("ts_alignment", "alignment", "轮胎定位", "Alignment", 3),
            ("ts_antiroll", "antiroll", "防倾杆", "Anti-roll Bars", 4),
            ("ts_springs", "springs", "弹簧", "Springs", 5),
            ("ts_damping", "damping", "阻尼", "Damping", 6),
            ("ts_aero", "aero", "空气动力学设置", "Aerodynamics", 7),
            ("ts_brakes", "brakes", "刹车", "Brakes", 8),
            ("ts_differential", "differential", "差速器", "Differential", 9),
        ]
        conn.executemany(
            "INSERT INTO tune_sections (section_id, section_key, label_zh, label_en, sort_order, is_active) VALUES (?, ?, ?, ?, ?, 1)",
            sections,
        )

        # Parameter definitions
        params = [
            # Tires
            ("tp_front_tire_pressure", "ts_tires", "front_tire_pressure", "前侧胎压", "Front Tire Pressure", "atm", 1.0, 3.8, 0.1, "slider", "front", None),
            ("tp_rear_tire_pressure", "ts_tires", "rear_tire_pressure", "后侧胎压", "Rear Tire Pressure", "atm", 1.0, 3.8, 0.1, "slider", "rear", None),
            # Gearing (placeholder - v1.0 does basic only)
            ("tp_final_drive", "ts_gearing", "final_drive", "最终传动比", "Final Drive", "", 2.0, 6.0, 0.01, "number_input", "", "gearing"),
            # Alignment
            ("tp_front_camber", "ts_alignment", "front_camber", "前侧外倾角", "Front Camber", "°", -5.0, 5.0, 0.1, "slider", "front", None),
            ("tp_rear_camber", "ts_alignment", "rear_camber", "后侧外倾角", "Rear Camber", "°", -5.0, 5.0, 0.1, "slider", "rear", None),
            ("tp_front_toe", "ts_alignment", "front_toe", "前侧束角", "Front Toe", "°", -5.0, 5.0, 0.1, "slider", "front", None),
            ("tp_rear_toe", "ts_alignment", "rear_toe", "后侧束角", "Rear Toe", "°", -5.0, 5.0, 0.1, "slider", "rear", None),
            ("tp_caster", "ts_alignment", "caster", "前轮后倾角", "Caster", "°", 0.0, 7.0, 0.1, "slider", "front", None),
            # Anti-roll bars
            ("tp_front_arb", "ts_antiroll", "front_arb", "前侧防倾杆", "Front ARB", "", 1.0, 65.0, 0.1, "slider", "front", None),
            ("tp_rear_arb", "ts_antiroll", "rear_arb", "后侧防倾杆", "Rear ARB", "", 1.0, 65.0, 0.1, "slider", "rear", None),
            # Springs
            ("tp_front_spring_rate", "ts_springs", "front_spring_rate", "前侧弹簧硬度", "Front Spring Rate", "N/mm", 464.0, 2320.0, 1.0, "number_input", "front", "springs"),
            ("tp_rear_spring_rate", "ts_springs", "rear_spring_rate", "后侧弹簧硬度", "Rear Spring Rate", "N/mm", 464.0, 2320.0, 1.0, "number_input", "rear", "springs"),
            ("tp_front_ride_height", "ts_springs", "front_ride_height", "前侧车身高度", "Front Ride Height", "cm", 9.0, 12.5, 0.1, "slider", "front", "springs"),
            ("tp_rear_ride_height", "ts_springs", "rear_ride_height", "后侧车身高度", "Rear Ride Height", "cm", 10.5, 14.0, 0.1, "slider", "rear", "springs"),
            # Damping
            ("tp_front_rebound", "ts_damping", "front_rebound", "前侧回弹硬度", "Front Rebound", "", 1.0, 20.0, 0.1, "slider", "front", "springs"),
            ("tp_rear_rebound", "ts_damping", "rear_rebound", "后侧回弹硬度", "Rear Rebound", "", 1.0, 20.0, 0.1, "slider", "rear", "springs"),
            ("tp_front_bump", "ts_damping", "front_bump", "前侧压缩硬度", "Front Bump", "", 1.0, 20.0, 0.1, "slider", "front", "springs"),
            ("tp_rear_bump", "ts_damping", "rear_bump", "后侧压缩硬度", "Rear Bump", "", 1.0, 20.0, 0.1, "slider", "rear", "springs"),
            # Aero
            ("tp_front_downforce", "ts_aero", "front_downforce", "前侧下压力", "Front Downforce", "kgf", 5.8, 173.0, 0.1, "slider", "front", "aero"),
            ("tp_rear_downforce", "ts_aero", "rear_downforce", "后侧下压力", "Rear Downforce", "kgf", 48.0, 207.0, 0.1, "slider", "rear", "aero"),
            # Brakes
            ("tp_brake_balance", "ts_brakes", "brake_balance", "制动力平衡", "Brake Balance", "%", 0.0, 100.0, 1.0, "slider", "", None),
            ("tp_brake_pressure", "ts_brakes", "brake_pressure", "制动力压力", "Brake Pressure", "%", 0.0, 100.0, 1.0, "slider", "", None),
            # Differential
            ("tp_rear_accel", "ts_differential", "rear_accel", "后侧加速", "Rear Acceleration", "%", 0.0, 100.0, 1.0, "slider", "rear", "differential"),
            ("tp_rear_decel", "ts_differential", "rear_decel", "后侧减速", "Rear Deceleration", "%", 0.0, 100.0, 1.0, "slider", "rear", "differential"),
        ]

        for param_id, section_id, key, label_zh, label_en, unit, min_v, max_v, step, display_type, side, unlock in params:
            conn.execute(
                """
                INSERT OR REPLACE INTO tune_parameter_definitions (
                    tune_parameter_id, section_id, parameter_key, category, label_zh, label_en,
                    unit, min_value, max_value, step, value_type, display_type, side,
                    unlock_condition, description, is_enabled, display_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'float', ?, ?, ?, '', 1, 0)
                """,
                (param_id, section_id, key, section_id, label_zh, label_en, unit, min_v, max_v, step, display_type, side, unlock),
            )


if __name__ == "__main__":
    seed_tune_templates()
    conn = connect(DEFAULT_DB_PATH)
    secs = conn.execute("SELECT COUNT(*) FROM tune_sections").fetchone()[0]
    params = conn.execute("SELECT COUNT(*) FROM tune_parameter_definitions").fetchone()[0]
    conn.close()
    print(f"Tune templates seeded: {secs} sections, {params} parameters")
