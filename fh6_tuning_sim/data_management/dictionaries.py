from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.data_management.json_store import safe_load_json, safe_save_json


ROOT = Path(__file__).resolve().parents[2]
DICTIONARY_DIR = ROOT / "configs" / "dictionaries"


def _item(
    key: str,
    label_zh: str,
    label_en: str | None = None,
    description_zh: str = "",
    description_en: str = "",
    sort_order: int = 0,
    is_active: bool = True,
) -> dict[str, Any]:
    return {
        "key": key,
        "label_zh": label_zh,
        "label_en": label_en or key,
        "description_zh": description_zh,
        "description_en": description_en,
        "is_active": is_active,
        "sort_order": sort_order,
    }


DEFAULT_DICTIONARIES: dict[str, dict[str, Any]] = {
    "use_case": {
        "filename": "use_cases.json",
        "name_zh": "用途类型",
        "name_en": "Use Cases",
        "items": [
            _item("road_grip", "公路抓地", "Road Grip", sort_order=10),
            _item("drift", "漂移", "Drift", sort_order=20),
            _item("rally", "拉力", "Rally", sort_order=30),
            _item("drag", "直线加速", "Drag", sort_order=40),
            _item("general", "通用测试", "General Test", sort_order=50),
        ],
    },
    "drivetrain": {
        "filename": "drivetrain_types.json",
        "name_zh": "驱动形式",
        "name_en": "Drivetrain Types",
        "items": [
            _item("FWD", "前驱", "FWD", sort_order=10),
            _item("RWD", "后驱", "RWD", sort_order=20),
            _item("AWD", "四驱", "AWD", sort_order=30),
            _item("unknown", "未知", "Unknown", sort_order=40),
        ],
    },
    "surface_type": {
        "filename": "surface_types.json",
        "name_zh": "路面类型",
        "name_en": "Surface Types",
        "items": [
            _item("asphalt", "沥青路", "Asphalt", sort_order=10),
            _item("dirt", "泥地", "Dirt", sort_order=20),
            _item("mixed", "混合路面", "Mixed", sort_order=30),
            _item("snow", "雪地", "Snow", sort_order=40),
            _item("wet", "湿地", "Wet", sort_order=50),
            _item("unknown", "未知", "Unknown", sort_order=60),
        ],
    },
    "test_scenario": {
        "filename": "test_scenarios.json",
        "name_zh": "测试场景",
        "name_en": "Test Scenarios",
        "items": [
            _item("free_drive", "自由驾驶", "Free Drive", sort_order=10),
            _item("full_lap", "完整跑圈", "Full Lap", sort_order=20),
            _item("straight_acceleration", "直线加速", "Straight Acceleration", sort_order=30),
            _item("heavy_braking", "重刹测试", "Heavy Braking", sort_order=40),
            _item("low_speed_corner", "低速弯", "Low-speed Corner", sort_order=50),
            _item("medium_speed_corner", "中速弯", "Medium-speed Corner", sort_order=60),
            _item("high_speed_corner", "高速弯", "High-speed Corner", sort_order=70),
            _item("corner_entry", "入弯", "Corner Entry", sort_order=80),
            _item("corner_mid", "弯中", "Corner Mid", sort_order=90),
            _item("corner_exit", "出弯", "Corner Exit", sort_order=100),
            _item("kerb_bump", "路肩/颠簸", "Kerb / Bump", sort_order=110),
            _item("rally_surface", "拉力/低抓地路面", "Rally / Low Grip Surface", sort_order=120),
            _item("track_boundary_survey", "赛道边界测量", "Track Boundary Survey", "用于建立 Route Profile / 可行驶走廊，不用于圈速评价", sort_order=130),
            _item("lap_run", "计时圈（旧）", "Lap Run (Legacy)", sort_order=900, is_active=False),
            _item("steady_cornering", "稳态过弯（旧）", "Steady Cornering (Legacy)", sort_order=910, is_active=False),
            _item("rally", "拉力（旧）", "Rally (Legacy)", sort_order=920, is_active=False),
            _item("unknown", "未设置", "Unknown", sort_order=999),
        ],
    },
    "dataset_purpose": {
        "filename": "dataset_purposes.json",
        "name_zh": "实验目的",
        "name_en": "Dataset Purposes",
        "items": [
            _item("baseline", "基准", "Baseline", sort_order=10),
            _item("intentional_understeer", "故意推头", "Intentional Understeer", sort_order=20),
            _item("intentional_oversteer", "故意甩尾", "Intentional Oversteer", sort_order=30),
            _item("front_antiroll_bar_test", "前防倾杆测试", "Front Anti-roll Bar Test", sort_order=40),
            _item("rear_diff_test", "后差速器测试", "Rear Differential Test", sort_order=50),
            _item("model_training", "模型训练", "Model Training", sort_order=60),
            _item("handling_evaluation", "操控性评估", "Handling Evaluation", sort_order=70),
        ],
    },
    "intent_tag": {
        "filename": "intent_tags.json",
        "name_zh": "实验意图标签",
        "name_en": "Intent Tags",
        "items": [
            _item("normal_driving", "正常驾驶", "Normal Driving", sort_order=5),
            _item("full_lap", "完整跑圈", "Full Lap", sort_order=6),
            _item("free_drive", "自由驾驶", "Free Drive", sort_order=7),
            _item("straight_acceleration", "直线加速", "Straight Acceleration", sort_order=8),
            _item("heavy_braking", "重刹测试", "Heavy Braking", sort_order=9),
            _item("intentional_understeer", "故意推头", "Intentional Understeer", sort_order=10),
            _item("intentional_oversteer", "故意甩尾", "Intentional Oversteer", sort_order=20),
            _item("intentional_heavy_braking", "故意重刹", "Intentional Heavy Braking", sort_order=30),
            _item("intentional_exit_wheelspin", "故意出弯打滑", "Intentional Exit Wheelspin", sort_order=40),
            _item("intentional_kerb", "故意压路肩", "Intentional Kerb Use", sort_order=50),
            _item("track_boundary_survey", "赛道测量", "Track Survey", sort_order=60),
            _item("other", "其他", "Other", sort_order=999),
        ],
    },
    "behavior_tag": {
        "filename": "behavior_tags.json",
        "name_zh": "车辆行为标签",
        "name_en": "Behavior Tags",
        "items": [
            _item("understeer", "推头", "Understeer", sort_order=10),
            _item("oversteer", "甩尾", "Oversteer", sort_order=20),
            _item("exit_wheelspin", "出弯打滑", "Exit Wheelspin", sort_order=30),
            _item("braking_instability", "刹车不稳", "Braking Instability", sort_order=40),
            _item("suspension_bottoming", "悬挂到底", "Suspension Bottoming", sort_order=50),
            _item("high_speed_instability", "高速不稳", "High-speed Instability", sort_order=60),
            _item("no_obvious_issue", "没有明显问题", "No Obvious Issue", sort_order=70),
        ],
    },
    "run_state_tag": {
        "filename": "run_state_tags.json",
        "name_zh": "记录状态标签",
        "name_en": "Run State Tags",
        "items": [
            _item("idle", "空闲等待", "Idle", sort_order=10),
            _item("stopped", "车辆静止", "Stopped", sort_order=20),
            _item("possible_pause", "可能暂停", "Possible Pause", sort_order=30),
            _item("recording_gap", "记录间隔", "Recording Gap", sort_order=40),
            _item("menu_or_no_data", "菜单/无有效数据", "Menu or No Data", sort_order=50),
        ],
    },
    "handling_dimension": {
        "filename": "handling_dimensions.json",
        "name_zh": "操控性维度",
        "name_en": "Handling Dimensions",
        "items": [
            _item("response", "响应性", "Response", "打方向后车是否愿意转", sort_order=10),
            _item("stability", "稳定性", "Stability", "高速、刹车、弯中是否稳定", sort_order=20),
            _item("predictability", "可预测性", "Predictability", "同样输入下车辆反应是否一致", sort_order=30),
            _item("recoverability", "可恢复性", "Recoverability", "失控后是否容易救回来", sort_order=40),
            _item("input_effort", "输入负担", "Input Effort", "是否需要频繁修正方向/油门/刹车", sort_order=50),
        ],
    },
    "subjective_score": {
        "filename": "subjective_scores.json",
        "name_zh": "主观评分项",
        "name_en": "Subjective Scores",
        "items": [
            _item("steering_response", "转向响应", "Steering Response", sort_order=10),
            _item("stability", "稳定性", "Stability", sort_order=20),
            _item("exit_traction", "出弯牵引", "Exit Traction", sort_order=30),
            _item("predictability", "可预测性", "Predictability", sort_order=40),
            _item("recoverability", "可恢复性", "Recoverability", sort_order=50),
            _item("ease_of_driving", "好开程度", "Ease of Driving", sort_order=60),
        ],
    },
    "quality_status": {
        "filename": "quality_statuses.json",
        "name_zh": "质量状态",
        "name_en": "Quality Statuses",
        "items": [
            _item("draft", "草稿", "Draft", sort_order=10),
            _item("usable", "可用", "Usable", sort_order=20),
            _item("good", "良好", "Good", sort_order=30),
            _item("warning", "注意", "Warning", sort_order=40),
            _item("bad", "较差", "Bad", sort_order=50),
            _item("archived", "已归档", "Archived", sort_order=60),
            _item("unknown", "未知", "Unknown", sort_order=70),
        ],
    },
    "run_type": {
        "filename": "run_types.json",
        "name_zh": "记录类型",
        "name_en": "Run Types",
        "items": [
            _item("normal_recording", "普通记录", "Normal Recording", sort_order=10),
            _item("tune_test", "调校测试", "Tune Test", sort_order=20),
            _item("full_lap", "完整跑圈", "Full Lap", sort_order=30),
            _item("track_boundary_survey", "赛道边界测量", "Track Boundary Survey", "用于建立路线边界和 Route Profile，不参与默认圈速评价", sort_order=40),
        ],
    },
    "survey_type": {
        "filename": "survey_types.json",
        "name_zh": "赛道测量类型",
        "name_en": "Survey Types",
        "items": [
            _item("left_boundary", "左边界", "Left Boundary", sort_order=10),
            _item("right_boundary", "右边界", "Right Boundary", sort_order=20),
            _item("reference_line", "参考线", "Reference Line", sort_order=30),
            _item("kerb_or_optional_area", "可压路肩/可选区域", "Kerb or Optional Area", sort_order=40),
            _item("invalid_area_probe", "无效区域探测", "Invalid Area Probe", sort_order=50),
        ],
    },
    "route_readiness_status": {
        "filename": "route_readiness_statuses.json",
        "name_zh": "路线测量准备度",
        "name_en": "Route Readiness Statuses",
        "items": [
            _item("not_started", "未开始", "Not Started", "还没有可用于安全行驶走廊草稿的测量数据", sort_order=10),
            _item("insufficient", "测量不足", "Insufficient", "测量数量不足，暂不建议生成走廊草稿", sort_order=20),
            _item("draft_available", "草稿可用", "Draft Available", "已有基本测量，可生成可行驶走廊草稿", sort_order=30),
            _item("complete_enough", "较完整", "Complete Enough", "左右边界和参考线测量较完整", sort_order=40),
        ],
    },
    "route_type": {
        "filename": "route_types.json",
        "name_zh": "路线类型",
        "name_en": "Route Types",
        "items": [
            _item("circuit", "封闭赛道", "Circuit", sort_order=10),
            _item("sprint", "点到点", "Sprint", sort_order=20),
            _item("open_route", "开放路线", "Open Route", sort_order=30),
            _item("test_area", "测试区域", "Test Area", sort_order=40),
            _item("unknown", "未设置", "Unknown", sort_order=999),
        ],
    },
    "experiment_type": {
        "filename": "experiment_types.json",
        "name_zh": "实验类型",
        "name_en": "Experiment Types",
        "items": [
            _item("baseline", "基准实验", "Baseline", sort_order=10),
            _item("single_variable_test", "单变量测试", "Single Variable Test", sort_order=20),
            _item("handling_evaluation", "操控性评估", "Handling Evaluation", sort_order=30),
            _item("model_training", "模型训练数据", "Model Training", sort_order=40),
            _item("track_survey", "赛道测量", "Track Survey", sort_order=50),
        ],
    },
    "controlled_variable": {
        "filename": "controlled_variables.json",
        "name_zh": "控制变量",
        "name_en": "Controlled Variables",
        "items": [
            _item("none", "无", "None", sort_order=10),
            _item("front_antiroll_bar", "前防倾杆", "Front Anti-roll Bar", sort_order=20),
            _item("rear_antiroll_bar", "后防倾杆", "Rear Anti-roll Bar", sort_order=30),
            _item("front_tire_pressure", "前胎压", "Front Tire Pressure", sort_order=40),
            _item("rear_tire_pressure", "后胎压", "Rear Tire Pressure", sort_order=50),
            _item("rear_diff_accel", "后差速加速", "Rear Diff Accel", sort_order=60),
            _item("brake_balance", "刹车平衡", "Brake Balance", sort_order=70),
        ],
    },
    "tune_area": {
        "filename": "tune_areas.json",
        "name_zh": "调校区域",
        "name_en": "Tune Areas",
        "items": [
            _item("tires", "轮胎", "Tires", sort_order=10),
            _item("gearing", "齿比", "Gearing", sort_order=20),
            _item("alignment", "定位", "Alignment", sort_order=30),
            _item("antiroll_bars", "防倾杆", "Anti-roll Bars", sort_order=40),
            _item("springs", "弹簧", "Springs", sort_order=50),
            _item("damping", "阻尼", "Damping", sort_order=60),
            _item("aero", "空气动力", "Aero", sort_order=70),
            _item("brakes", "刹车", "Brakes", sort_order=80),
            _item("differential", "差速器", "Differential", sort_order=90),
        ],
    },
    "assist_type": {
        "filename": "assist_types.json",
        "name_zh": "辅助设置",
        "name_en": "Assist Types",
        "items": [
            _item("abs", "ABS", "ABS", sort_order=10),
            _item("traction_control", "牵引力控制", "Traction Control", sort_order=20),
            _item("stability_control", "稳定控制", "Stability Control", sort_order=30),
            _item("shifting", "换挡", "Shifting", sort_order=40),
        ],
    },
    "car_class": {
        "filename": "car_classes.json",
        "name_zh": "车辆等级",
        "name_en": "Car Classes",
        "items": [
            _item("D", "D 级", "D", sort_order=10),
            _item("C", "C 级", "C", sort_order=20),
            _item("B", "B 级", "B", sort_order=30),
            _item("A", "A 级", "A", sort_order=40),
            _item("S1", "S1 级", "S1", sort_order=50),
            _item("S2", "S2 级", "S2", sort_order=60),
            _item("X", "X 级", "X", sort_order=70),
            _item("unknown", "未知", "Unknown", sort_order=999),
        ],
    },
    "data_status": {
        "filename": "data_statuses.json",
        "name_zh": "数据状态",
        "name_en": "Data Statuses",
        "items": [
            _item("normal", "正常", "Normal", sort_order=10),
            _item("has_pause", "有暂停", "Has Pause", sort_order=20),
            _item("has_collision", "有撞击", "Has Collision", sort_order=30),
            _item("incomplete_route", "路线不完整", "Incomplete Route", sort_order=40),
            _item("long_zero_speed", "速度长时间为 0", "Long Zero Speed", sort_order=50),
            _item("uncertain", "不确定", "Uncertain", sort_order=60),
        ],
    },
    "input_style": {
        "filename": "input_styles.json",
        "name_zh": "输入风格",
        "name_en": "Input Styles",
        "items": [_item("controller", "手柄", "Controller", sort_order=10)],
    },
    "assists_shifting": {
        "filename": "shifting_modes.json",
        "name_zh": "换挡模式",
        "name_en": "Shifting Modes",
        "items": [
            _item("manual", "手动", "Manual", sort_order=10),
            _item("auto", "自动", "Auto", sort_order=20),
        ],
    },
    "route": {
        "filename": "routes.json",
        "name_zh": "路线",
        "name_en": "Routes",
        "items": [
            _item("horizon_highway_loop", "高速环线", "Horizon Highway Loop", sort_order=10),
            _item("custom_route", "自定义路线", "Custom Route", sort_order=20),
            _item("unknown", "未设置", "Unknown", sort_order=999),
        ],
    },
    "general_tag": {
        "filename": "general_tags.json",
        "name_zh": "通用标签",
        "name_en": "General Tags",
        "items": [
            _item("baseline", "基准", "Baseline", sort_order=10),
            _item("model_training", "模型训练", "Model Training", sort_order=20),
            _item("handling_evaluation", "操控性评估", "Handling Evaluation", sort_order=30),
            _item("needs_review", "需要复查", "Needs Review", sort_order=40),
        ],
    },
}

DICTIONARY_SPECS = {
    group: {
        "filename": spec["filename"],
        "name_zh": spec["name_zh"],
        "name_en": spec["name_en"],
    }
    for group, spec in DEFAULT_DICTIONARIES.items()
}


def dictionary_file(group: str) -> Path:
    if group not in DICTIONARY_SPECS:
        raise KeyError(f"Unknown dictionary group: {group}")
    return DICTIONARY_DIR / str(DICTIONARY_SPECS[group]["filename"])


def default_dictionary_items(group: str) -> list[dict[str, Any]]:
    return [dict(item) for item in DEFAULT_DICTIONARIES[group]["items"]]


def normalize_dictionary_item(raw: Any, *, fallback_sort: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    key = str(raw.get("key", "")).strip()
    if not key:
        return None
    sort_value = raw.get("sort_order", fallback_sort)
    try:
        sort_order = int(sort_value)
    except (TypeError, ValueError):
        sort_order = fallback_sort

    active_value = raw.get("is_active", True)
    if isinstance(active_value, str):
        is_active = active_value.strip().lower() not in {"0", "false", "no", "off"}
    else:
        is_active = bool(active_value)

    label_zh = str(raw.get("label_zh") or key).strip()
    label_en = str(raw.get("label_en") or key).strip()
    return {
        "key": key,
        "label_zh": label_zh,
        "label_en": label_en,
        "description_zh": str(raw.get("description_zh", "")).strip(),
        "description_en": str(raw.get("description_en", "")).strip(),
        "is_active": is_active,
        "sort_order": sort_order,
    }


def save_dictionary_items(group: str, items: list[dict[str, Any]]) -> None:
    spec = DICTIONARY_SPECS[group]
    safe_save_json(
        dictionary_file(group),
        {
            "group": group,
            "name_zh": spec["name_zh"],
            "name_en": spec["name_en"],
            "items": items,
        },
    )


def read_dictionary_items(
    group: str,
    *,
    include_inactive: bool = True,
    merge_defaults: bool = True,
) -> list[dict[str, Any]]:
    defaults = default_dictionary_items(group)
    file_path = dictionary_file(group)
    if not file_path.exists():
        save_dictionary_items(group, defaults)
        items = defaults
    else:
        payload = safe_load_json(file_path, {"items": []})
        raw_items = payload.get("items", [])
        items = []
        seen: set[str] = set()
        for idx, raw in enumerate(raw_items if isinstance(raw_items, list) else []):
            item = normalize_dictionary_item(raw, fallback_sort=(idx + 1) * 10)
            if not item or item["key"] in seen:
                continue
            seen.add(item["key"])
            items.append(item)

        if merge_defaults:
            for default in defaults:
                if default["key"] not in seen:
                    items.append(default)
                    seen.add(default["key"])

        if not items:
            items = defaults

    items.sort(key=lambda item: (int(item.get("sort_order", 0)), str(item.get("key", ""))))
    if include_inactive:
        return items
    return [item for item in items if bool(item.get("is_active", True))]


def ensure_all_dictionaries() -> None:
    DICTIONARY_DIR.mkdir(parents=True, exist_ok=True)
    for group in DICTIONARY_SPECS:
        items = read_dictionary_items(group, include_inactive=True, merge_defaults=True)
        save_dictionary_items(group, items)


def dictionary_group_label(group: str) -> str:
    return str(DICTIONARY_SPECS[group]["name_zh"])


def option_values(group: str, *, include_inactive: bool = False) -> list[str]:
    return [
        str(item["key"])
        for item in read_dictionary_items(group, include_inactive=include_inactive)
        if str(item.get("key", "")).strip()
    ]


def label_of(group: str, value: Any, *, fallback: str = "未填写") -> str:
    if value is None:
        return fallback
    raw = str(value).strip()
    if not raw:
        return fallback
    items = read_dictionary_items(group, include_inactive=True)
    exact = next((item for item in items if str(item.get("key")) == raw), None)
    if exact:
        return str(exact.get("label_zh") or raw)
    lower = raw.lower()
    case_match = next((item for item in items if str(item.get("key", "")).lower() == lower), None)
    if case_match:
        return str(case_match.get("label_zh") or raw)
    return raw


def labels_for(group: str, values: list[Any]) -> list[str]:
    return [label_of(group, value) for value in values]
