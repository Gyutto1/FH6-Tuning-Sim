from __future__ import annotations

RECORD_TYPES = [
    ("完整跑圈", "full_lap"),
    ("自由驾驶", "free_drive"),
    ("直线加速", "drag_strip"),
    ("重刹测试", "hard_braking"),
    ("低速弯", "low_speed_corner"),
    ("中速弯", "mid_speed_corner"),
    ("高速弯", "high_speed_corner"),
    ("赛道测量", "track_survey"),
    ("普通记录", "normal_recording"),
    ("其他", "other"),
]

ROUTE_MODES = [
    ("计时赛 / 路线", "timed_route"),
    ("自由驾驶", "free_drive"),
    ("未设置", "unset"),
]

STEP_NAMES = ["预设", "升级", "调校", "快照", "命名", "路线/标签", "准备开始"]
