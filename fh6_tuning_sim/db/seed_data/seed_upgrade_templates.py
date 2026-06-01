from __future__ import annotations

from pathlib import Path

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.migration_v4_client_rewire import migrate_v4_client_rewire


def seed_upgrade_templates(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Seed default upgrade categories, slots, and options idempotently."""
    migrate_v4_client_rewire(db_path)

    with transaction(db_path) as conn:
        # Categories (6 main groups)
        categories = [
            ("uc_engine", "engine", "引擎", "Engine", 1),
            ("uc_platform_handling", "platform_handling", "底盘与操纵性", "Platform and Handling", 2),
            ("uc_drivetrain", "drivetrain", "传动系统", "Drivetrain", 3),
            ("uc_tires", "tires", "轮胎与轮廓", "Tires and Rims", 4),
            ("uc_aero", "aero", "空气动力学套件与外观", "Aero and Appearance", 5),
            ("uc_conversion", "conversion", "车身套件和改装", "Conversion", 6),
        ]
        conn.executemany(
            """
            INSERT INTO upgrade_categories (
                upgrade_category_id, category_key, label_zh, label_en, display_order, is_active
            ) VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(upgrade_category_id) DO UPDATE SET
                category_key = excluded.category_key,
                label_zh = excluded.label_zh,
                label_en = excluded.label_en,
                display_order = excluded.display_order,
                is_active = 1
            """,
            categories,
        )

        # Slots (sub-categories)
        slots = [
            ("us_intake", "uc_engine", "intake", "进气系统", "Intake", 1),
            ("us_fuel", "uc_engine", "fuel", "燃油系统", "Fuel System", 2),
            ("us_ignition", "uc_engine", "ignition", "点火系统", "Ignition", 3),
            ("us_exhaust", "uc_engine", "exhaust", "排气系统", "Exhaust", 4),
            ("us_camshaft", "uc_engine", "camshaft", "凸轮轴", "Camshaft", 5),
            ("us_valves", "uc_engine", "valves", "阀门", "Valves", 6),
            ("us_displacement", "uc_engine", "displacement", "排气量/引擎缸体", "Displacement", 7),
            ("us_pistons", "uc_engine", "pistons", "活塞/压缩系统", "Pistons", 8),
            ("us_twin_turbo", "uc_engine", "twin_turbo", "双涡轮增压器", "Twin Turbo", 9),
            ("us_intercooler", "uc_engine", "intercooler", "中间冷却器", "Intercooler", 10),
            ("us_flywheel", "uc_engine", "flywheel", "飞轮", "Flywheel", 11),
            ("us_springs", "uc_platform_handling", "springs", "弹簧与阻尼器", "Springs and Dampers", 1),
            ("us_chassis", "uc_platform_handling", "chassis", "底盘加固/防滚架", "Chassis Reinforcement", 2),
            ("us_weight", "uc_platform_handling", "weight", "车重减轻", "Weight Reduction", 3),
            ("us_transmission", "uc_drivetrain", "transmission", "变速箱", "Transmission", 1),
            ("us_differential", "uc_drivetrain", "differential", "差速器", "Differential", 2),
            ("us_tire_compound", "uc_tires", "tire_compound", "轮胎胎面材料", "Tire Compound", 1),
            ("us_side_skirts", "uc_aero", "side_skirts", "侧裙", "Side Skirts", 1),
            ("us_engine_swap", "uc_conversion", "engine_swap", "引擎更换", "Engine Swap", 1),
            ("us_drivetrain_swap", "uc_conversion", "drivetrain_swap", "传动系统置换", "Drivetrain Swap", 2),
        ]
        conn.executemany(
            """
            INSERT INTO upgrade_slots (
                slot_id, upgrade_category_id, slot_key, label_zh, label_en, sort_order, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(slot_id) DO UPDATE SET
                upgrade_category_id = excluded.upgrade_category_id,
                slot_key = excluded.slot_key,
                label_zh = excluded.label_zh,
                label_en = excluded.label_en,
                sort_order = excluded.sort_order,
                is_active = 1
            """,
            slots,
        )

        # Options
        options = [
            ("uo_intake_stock", "us_intake", "intake_stock", "原厂进气系统", "Stock Intake", 0, 1, None),
            ("uo_intake_race", "us_intake", "intake_race", "赛车版进气系统", "Race Intake", 1, 0, None),
            ("uo_fuel_stock", "us_fuel", "fuel_stock", "原厂燃油系统", "Stock Fuel", 0, 1, None),
            ("uo_fuel_race", "us_fuel", "fuel_race", "赛车版燃油系统", "Race Fuel", 1, 0, None),
            ("uo_ignition_stock", "us_ignition", "ignition_stock", "原厂点火系统", "Stock Ignition", 0, 1, None),
            ("uo_ignition_race", "us_ignition", "ignition_race", "赛车版点火系统", "Race Ignition", 1, 0, None),
            ("uo_exhaust_stock", "us_exhaust", "exhaust_stock", "原厂排气系统", "Stock Exhaust", 0, 1, None),
            ("uo_exhaust_race", "us_exhaust", "exhaust_race", "赛车版排气系统", "Race Exhaust", 1, 0, None),
            ("uo_cam_stock", "us_camshaft", "cam_stock", "原厂凸轮与气门", "Stock Camshaft", 0, 1, None),
            ("uo_cam_race", "us_camshaft", "cam_race", "赛车版凸轮与气门", "Race Camshaft", 1, 0, None),
            ("uo_valves_stock", "us_valves", "valves_stock", "原厂气门", "Stock Valves", 0, 1, None),
            ("uo_valves_sport", "us_valves", "valves_sport", "跑车版气门", "Sport Valves", 1, 0, None),
            ("uo_valves_race", "us_valves", "valves_race", "赛车版气门", "Race Valves", 2, 0, None),
            ("uo_disp_stock", "us_displacement", "disp_stock", "原厂引擎缸体", "Stock Block", 0, 1, None),
            ("uo_disp_race", "us_displacement", "disp_race", "赛车版引擎缸体", "Race Block", 1, 0, None),
            ("uo_pistons_stock", "us_pistons", "pistons_stock", "原厂活塞压缩系统", "Stock Pistons", 0, 1, None),
            ("uo_pistons_sport", "us_pistons", "pistons_sport", "跑车版活塞压缩系统", "Sport Pistons", 1, 0, None),
            ("uo_pistons_race", "us_pistons", "pistons_race", "赛车版活塞压缩系统", "Race Pistons", 2, 0, None),
            ("uo_turbo_stock", "us_twin_turbo", "turbo_stock", "原厂双涡轮增压器", "Stock Twin Turbo", 0, 1, None),
            ("uo_turbo_race", "us_twin_turbo", "turbo_race", "赛车版双涡轮增压器", "Race Twin Turbo", 1, 0, None),
            ("uo_turbo_race_al", "us_twin_turbo", "turbo_race_al", "带防迟滞赛车版双涡轮", "Race Twin Turbo Anti-lag", 2, 0, None),
            ("uo_ic_stock", "us_intercooler", "ic_stock", "原厂中间冷却器", "Stock Intercooler", 0, 1, None),
            ("uo_ic_race", "us_intercooler", "ic_race", "赛车版中间冷却器", "Race Intercooler", 1, 0, None),
            ("uo_fly_stock", "us_flywheel", "fly_stock", "原厂飞轮", "Stock Flywheel", 0, 1, None),
            ("uo_fly_sport", "us_flywheel", "fly_sport", "跑车版飞轮", "Sport Flywheel", 1, 0, None),
            ("uo_fly_race", "us_flywheel", "fly_race", "赛车版飞轮", "Race Flywheel", 2, 0, None),
            ("uo_springs_stock", "us_springs", "springs_stock", "原厂弹簧与阻尼器", "Stock Springs", 0, 1, None),
            ("uo_springs_rally", "us_springs", "springs_rally", "拉力弹簧与阻尼器", "Rally Springs", 1, 0, "springs,dampers,alignment"),
            ("uo_springs_drift", "us_springs", "springs_drift", "漂移弹簧与阻尼器", "Drift Springs", 2, 0, "springs,dampers,alignment"),
            ("uo_chassis_stock", "us_chassis", "chassis_stock", "原厂底盘加固", "Stock Chassis", 0, 1, None),
            ("uo_chassis_race", "us_chassis", "chassis_race", "赛车版底盘加固", "Race Chassis", 1, 0, None),
            ("uo_weight_stock", "us_weight", "weight_stock", "原厂车重减轻", "Stock Weight", 0, 1, None),
            ("uo_weight_sport", "us_weight", "weight_sport", "跑车版车重减轻", "Sport Weight Reduction", 1, 0, None),
            ("uo_weight_race", "us_weight", "weight_race", "赛车版车重减轻", "Race Weight Reduction", 2, 0, None),
            ("uo_trans_race6", "us_transmission", "trans_race6", "赛车版6速变速箱", "Race 6-Speed", 1, 0, "gearing"),
            ("uo_trans_race8", "us_transmission", "trans_race8", "赛车版8速变速箱", "Race 8-Speed", 1, 0, "gearing"),
            ("uo_trans_race9", "us_transmission", "trans_race9", "赛车版9速变速箱", "Race 9-Speed", 1, 0, "gearing"),
            ("uo_trans_race10", "us_transmission", "trans_race10", "赛车版10速变速箱", "Race 10-Speed", 1, 0, "gearing"),
            ("uo_trans_drift4", "us_transmission", "trans_drift4", "漂移4速变速箱", "Drift 4-Speed", 1, 0, "gearing"),
            ("uo_diff_stock", "us_differential", "diff_stock", "原厂差速器", "Stock Differential", 0, 1, None),
            ("uo_diff_rally", "us_differential", "diff_rally", "拉力赛差速器", "Rally Differential", 1, 0, "differential"),
            ("uo_diff_drift", "us_differential", "diff_drift", "漂移差速器", "Drift Differential", 1, 0, "differential"),
            ("uo_tire_semi", "us_tire_compound", "tire_semi", "半热熔赛车版轮胎", "Semi-Slick Race", 1, 0, None),
            ("uo_tire_horizon_semi", "us_tire_compound", "tire_horizon_semi", "地平线半热熔赛车版轮胎", "Horizon Semi-Slick", 1, 0, None),
            ("uo_tire_slick", "us_tire_compound", "tire_slick", "热熔赛车版轮胎", "Slick Race", 1, 0, None),
            ("uo_tire_drift", "us_tire_compound", "tire_drift", "漂移轮胎", "Drift Tires", 1, 0, None),
            ("uo_tire_rally", "us_tire_compound", "tire_rally", "拉力轮胎", "Rally Tires", 1, 0, None),
            ("uo_tire_offroad", "us_tire_compound", "tire_offroad", "越野赛车版轮胎", "Offroad Race", 1, 0, None),
            ("uo_tire_snow", "us_tire_compound", "tire_snow", "雪地轮胎", "Snow Tires", 1, 0, None),
            ("uo_tire_drag", "us_tire_compound", "tire_drag", "直线加速版轮胎", "Drag Tires", 1, 0, None),
            ("uo_skirts_stock", "us_side_skirts", "skirts_stock", "原厂侧裙", "Stock Side Skirts", 0, 1, None),
            ("uo_skirts_street", "us_side_skirts", "skirts_street", "街车版侧裙", "Street Side Skirts", 1, 0, "aero"),
            ("uo_eswap_stock", "us_engine_swap", "eswap_stock", "原厂动力置换", "Stock Engine", 0, 1, None),
            ("uo_eswap_v12", "us_engine_swap", "eswap_v12", "Racing V12", "Racing V12", 1, 0, None),
            ("uo_eswap_v6t", "us_engine_swap", "eswap_v6t", "1.6L V6T", "1.6L V6T", 1, 0, None),
            ("uo_dswap_stock", "us_drivetrain_swap", "dswap_stock", "原厂传动", "Stock Drivetrain", 0, 1, None),
            ("uo_dswap_awd", "us_drivetrain_swap", "dswap_awd", "全轮驱动", "AWD Conversion", 1, 0, None),
        ]
        for opt_id, slot_id, key, label_zh, label_en, tier, is_stock, unlock_tune in options:
            cat_id = conn.execute("SELECT upgrade_category_id FROM upgrade_slots WHERE slot_id = ?", (slot_id,)).fetchone()
            if not cat_id:
                continue
            conn.execute(
                """
                INSERT INTO upgrade_options (
                    upgrade_option_id, upgrade_category_id, slot_id, option_key, label_zh, label_en,
                    tier, is_stock, unlock_tune_sections, notes, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(upgrade_option_id) DO UPDATE SET
                    upgrade_category_id = excluded.upgrade_category_id,
                    slot_id = excluded.slot_id,
                    option_key = excluded.option_key,
                    label_zh = excluded.label_zh,
                    label_en = excluded.label_en,
                    tier = excluded.tier,
                    is_stock = excluded.is_stock,
                    unlock_tune_sections = excluded.unlock_tune_sections,
                    notes = excluded.notes,
                    is_active = 1
                """,
                (opt_id, cat_id[0], slot_id, key, label_zh, label_en, tier, is_stock, unlock_tune, ""),
            )


if __name__ == "__main__":
    seed_upgrade_templates()
    conn = connect(DEFAULT_DB_PATH)
    cats = conn.execute("SELECT COUNT(*) FROM upgrade_categories").fetchone()[0]
    slots = conn.execute("SELECT COUNT(*) FROM upgrade_slots").fetchone()[0]
    opts = conn.execute("SELECT COUNT(*) FROM upgrade_options").fetchone()[0]
    conn.close()
    print(f"Upgrade templates seeded: {cats} categories, {slots} slots, {opts} options")
