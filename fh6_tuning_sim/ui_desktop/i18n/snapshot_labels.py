from __future__ import annotations

VEHICLE_DATA_FIELDS = [
    ("最高速度", "kph", "top_speed"),
    ("0-100 kph", "s", "accel_0_100"),
    ("马力", "PS", "horsepower"),
    ("扭矩", "N-m", "torque_val"),
    ("车重", "kg", "weight_val"),
    ("功率重量比", "PS/kg", "power_weight_ratio"),
    ("侧向 G 力", "", "lateral_g"),
    ("空气动力学效率", "", "aero_efficiency"),
    ("空气动力学平衡", "", "aero_balance"),
    ("机械平衡", "", "mech_balance"),
    ("悬挂系统", "", "suspension_type"),
    ("轮胎踏面胶料", "", "tire_compound_type"),
    ("传动系统", "", "drivetrain_type"),
    ("刹车距离 97-0", "m", "brake_97_0_m"),
    ("刹车距离 161-0", "m", "brake_161_0_m"),
    ("侧向 G 97km/h", "", "lateral_g_97"),
    ("侧向 G 193km/h", "", "lateral_g_193"),
    ("加速 0-97km/h", "s", "accel_0_97_s"),
    ("加速 0-161km/h", "s", "accel_0_161_s"),
]

VEHICLE_DATA_REQUIRED_KEYS = [item[2] for item in VEHICLE_DATA_FIELDS]

DATA_OWNERSHIP_LINES = [
    "Build：记录硬件/升级槽位选择。",
    "Tune：记录调校参数值（归属到 Build）。",
    "Snapshot：冻结 Build + Tune + 车辆数据面板，作为 Run 前事实快照。",
    "Run：记录原始遥测 CSV 与统计摘要，并绑定 car/build/tune/snapshot。",
]

