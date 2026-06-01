
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from fh6_tuning_sim.analysis.data_quality import compute_data_quality_for_csv
from fh6_tuning_sim.config import load_json, write_json
from fh6_tuning_sim.data_management.dictionaries import (
    DICTIONARY_SPECS,
    default_dictionary_items,
    dictionary_group_label,
    ensure_all_dictionaries,
    label_of,
    normalize_dictionary_item,
    option_values,
    read_dictionary_items,
    save_dictionary_items,
)
from fh6_tuning_sim.data_management.integrity import check_data_integrity, write_data_integrity_report
from fh6_tuning_sim.data_management.platform_store import (
    HANDLING_SCORE_KEYS,
    PLATFORM_INDEX_PATH,
    SUBJECTIVE_SCORE_KEYS,
    average_scores_for_car,
    behavior_counts_for_car,
    clean_list,
    find_car,
    get_run_review,
    read_platform,
    save_run_review,
    stable_group_id,
    stable_tune_id,
    summarize_car,
    sync_platform_with_runs,
    utc_now,
    write_platform,
)
from fh6_tuning_sim.data_management.run_index import index_session, rebuild_index, read_index
from fh6_tuning_sim.data_management.route_profile import (
    build_route_profile_from_csv,
    read_route_profiles,
    route_profile_status,
    route_survey_readiness,
)
from fh6_tuning_sim.data_management.route_store import list_routes
from fh6_tuning_sim.data_management.session_naming import build_session_id, sanitize_filename
from fh6_tuning_sim.ui.theme import advanced_expander, empty_state, metric_card, section_header, status_badge
from fh6_tuning_sim.ui.recording_controller import RecordingController, process_session

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SESSIONS_DIR = ROOT / "data" / "sessions"
REPORTS_DIR = ROOT / "reports"
DATASETS_DIR = ROOT / "data" / "datasets"
TUNE_CONFIG = ROOT / "configs" / "tune_config.json"
CAR_BINDINGS_FILE = ROOT / "configs" / "cars" / "car_ordinal_bindings.json"

TUNE_FIELD_LABELS = {
    "front_tire_pressure": "前胎压",
    "rear_tire_pressure": "后胎压",
    "final_drive": "终传比",
    "front_camber": "前外倾",
    "rear_camber": "后外倾",
    "front_toe": "前束",
    "rear_toe": "后束",
    "caster": "主销后倾",
    "front_antiroll_bar": "前防倾杆",
    "rear_antiroll_bar": "后防倾杆",
    "front_spring": "前弹簧",
    "rear_spring": "后弹簧",
    "front_ride_height": "前车高",
    "rear_ride_height": "后车高",
    "front_rebound": "前回弹阻尼",
    "rear_rebound": "后回弹阻尼",
    "front_bump": "前压缩阻尼",
    "rear_bump": "后压缩阻尼",
    "front_aero": "前下压力",
    "rear_aero": "后下压力",
    "brake_balance": "刹车平衡",
    "brake_pressure": "刹车压力",
    "front_diff_accel": "前差速加速",
    "front_diff_decel": "前差速减速",
    "rear_diff_accel": "后差速加速",
    "rear_diff_decel": "后差速减速",
    "center_balance": "中央扭矩分配",
}

PAGE_DASHBOARD = "首页"
PAGE_CARS = "车辆库"
PAGE_CAR_DETAIL = "车辆详情"
PAGE_GROUPS = "数据集组"
PAGE_ROUTES = "路线库"
PAGE_ROUTE_DETAIL = "路线详情"
PAGE_RECORD = "开始记录"
PAGE_REVIEW = "记录回顾"
PAGE_TAGS = "标签管理"
PAGE_DICTIONARY = "数据字典管理"
PAGE_SETTINGS = "设置"


def apply_theme() -> None:
    st.markdown(
        """
<style>
:root {
  --fh6-bg: #f7f8f6;
  --fh6-ink: #1f251f;
  --fh6-muted: #6f7567;
  --fh6-card: #ffffff;
  --fh6-line: rgba(49, 58, 44, 0.14);
  --fh6-accent: #2f6f65;
  --fh6-green: #455c42;
}
.stApp { background: var(--fh6-bg); color: var(--fh6-ink); }
.block-container { padding-top: 1.5rem; }
.fh6-card {
  background: var(--fh6-card);
  border: 1px solid var(--fh6-line);
  border-radius: 8px;
  padding: 14px 16px;
}
.fh6-kicker { color: var(--fh6-accent); font-weight: 700; font-size: .8rem; }
.fh6-muted { color: var(--fh6-muted); }
</style>
""",
        unsafe_allow_html=True,
    )


def ensure_dirs() -> None:
    for path in [
        RAW_DIR,
        PROCESSED_DIR,
        SESSIONS_DIR,
        REPORTS_DIR,
        DATASETS_DIR,
        ROOT / "data" / "index",
        ROOT / "data" / "platform",
        ROOT / "configs" / "cars",
        ROOT / "configs" / "tunes",
        ROOT / "configs" / "routes",
        ROOT / "configs" / "thresholds",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    ensure_all_dictionaries()
    if not CAR_BINDINGS_FILE.exists():
        write_json(CAR_BINDINGS_FILE, {"bindings": {}})
    sync_platform_with_runs(read_index())


def get_controller() -> RecordingController:
    if "recording_controller" not in st.session_state:
        st.session_state.recording_controller = RecordingController()
    return st.session_state.recording_controller


def get_run_config() -> dict[str, Any]:
    if "run_config" not in st.session_state:
        tune = load_json(TUNE_CONFIG, required=False)
        st.session_state.run_config = {
            "host": "127.0.0.1",
            "port": 9999,
            "car_name": tune.get("car_name", "Mercedes-AMG GT"),
            "car_ordinal": tune.get("car_ordinal"),
            "car_class": tune.get("car_class", "unknown"),
            "performance_index": tune.get("performance_index"),
            "drivetrain": tune.get("drivetrain", "RWD"),
            "car_group": tune.get("car_group"),
            "power_class": tune.get("power_class", ""),
            "tune_name": tune.get("tune_name", "stock_default"),
            "tune_version": tune.get("tune_version", "v01"),
            "use_case": tune.get("use_case", "road_grip"),
            "run_type": "normal_recording",
            "survey_type": "reference_line",
            "survey_speed_note": "slow_and_steady",
            "route_name": "horizon_highway_loop",
            "surface_type": "asphalt",
            "test_scenario": "free_drive",
            "purpose": "baseline",
            "purpose_tags": ["baseline"],
            "driver_input_style": "controller",
            "assists_abs": True,
            "assists_traction_control": False,
            "assists_stability_control": False,
            "assists_shifting": "manual",
            "tags": ["baseline"],
            "notes": "",
            "tune": tune.get("tune", {}),
            "auto_process": True,
        }
    return st.session_state.run_config


def build_recording_config() -> dict[str, Any]:
    cfg = get_run_config()
    tags = sorted(set(clean_list(cfg.get("tags")) + clean_list(cfg.get("purpose_tags"))))
    session_id = build_session_id(
        car_name=cfg.get("car_name"),
        car_class=cfg.get("car_class"),
        performance_index=cfg.get("performance_index"),
        use_case=cfg.get("use_case"),
        route_name=cfg.get("route_name"),
        test_scenario=cfg.get("test_scenario"),
        tune_name=cfg.get("tune_name"),
        run_number=1,
    )
    metadata = {
        "game": "Forza Horizon 6",
        "car_name": cfg.get("car_name"),
        "car_ordinal": cfg.get("car_ordinal"),
        "car_class": cfg.get("car_class"),
        "performance_index": cfg.get("performance_index"),
        "drivetrain": cfg.get("drivetrain"),
        "car_group": cfg.get("car_group"),
        "power_class": cfg.get("power_class"),
        "use_case": cfg.get("use_case"),
        "run_type": cfg.get("run_type", "normal_recording"),
        "survey_type": cfg.get("survey_type") if cfg.get("run_type") == "track_boundary_survey" else None,
        "is_for_route_profile": cfg.get("run_type") == "track_boundary_survey",
        "survey_speed_note": cfg.get("survey_speed_note", ""),
        "route_name": cfg.get("route_name"),
        "surface_type": cfg.get("surface_type"),
        "test_scenario": cfg.get("test_scenario"),
        "purpose": cfg.get("purpose"),
        "purpose_tags": clean_list(cfg.get("purpose_tags")),
        "driver_input_style": cfg.get("driver_input_style"),
        "assists": {
            "abs": cfg.get("assists_abs"),
            "traction_control": cfg.get("assists_traction_control"),
            "stability_control": cfg.get("assists_stability_control"),
            "shifting": cfg.get("assists_shifting"),
        },
        "tune_name": cfg.get("tune_name"),
        "tune_version": cfg.get("tune_version"),
        "tags": tags,
        "notes": cfg.get("notes", ""),
    }
    tune_config = {
        "car_name": cfg.get("car_name"),
        "car_ordinal": cfg.get("car_ordinal"),
        "car_class": cfg.get("car_class"),
        "performance_index": cfg.get("performance_index"),
        "drivetrain": cfg.get("drivetrain"),
        "use_case": cfg.get("use_case"),
        "tune_name": cfg.get("tune_name"),
        "tune_version": cfg.get("tune_version"),
        "tune": cfg.get("tune", {}),
    }
    return {"session_id": session_id, "host": cfg.get("host", "127.0.0.1"), "port": int(cfg.get("port", 9999)), "metadata": metadata, "tune_config": tune_config, "auto_process": bool(cfg.get("auto_process", True))}


def select_dictionary(group: str, label: str, value: Any, *, key: str) -> str:
    options = option_values(group)
    current = str(value or "")
    if current and current not in options:
        options.append(current)
    if not options:
        return st.text_input(label, value=current, key=key)
    index = options.index(current) if current in options else 0
    return str(st.selectbox(label, options, index=index, format_func=lambda item: label_of(group, item), key=key))


def multiselect_dictionary(group: str, label: str, values: Any, *, key: str) -> list[str]:
    options = option_values(group)
    selected = clean_list(values)
    for item in selected:
        if item not in options:
            options.append(item)
    return list(st.multiselect(label, options, default=selected, format_func=lambda item: label_of(group, item), key=key))


def score_select(label: str, value: Any, *, key: str, help_text: str | None = None) -> int | None:
    options: list[Any] = ["未评分", 1, 2, 3, 4, 5]
    current = int(value) if str(value or "").isdigit() else "未评分"
    index = options.index(current) if current in options else 0
    selected = st.selectbox(label, options, index=index, key=key, help=help_text)
    return None if selected == "未评分" else int(selected)


def runs_by_id() -> dict[str, dict[str, Any]]:
    return {str(item.get("session_id")): item for item in read_index() if item.get("session_id")}


def car_run_ids(car: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for group in car.get("dataset_groups", []):
        ids.extend(clean_list(group.get("run_ids")))
    return sorted(set(ids))


def car_runs(car: dict[str, Any], all_runs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [all_runs[run_id] for run_id in car_run_ids(car) if run_id in all_runs]


def selected_car(platform: dict[str, Any]) -> dict[str, Any] | None:
    cars = platform.get("cars", [])
    if not cars:
        return None
    selected_id = st.session_state.get("selected_car_id")
    if selected_id:
        found = find_car(platform, selected_id)
        if found:
            return found
    return cars[0]


def set_page(page: str, *, car_id: str | None = None, session_id: str | None = None) -> None:
    st.session_state._pending_page = page
    if car_id:
        st.session_state.selected_car_id = car_id
    if session_id:
        st.session_state.selected_review_session_id = session_id
    st.rerun()


def render_platform_header(title: str, caption: str) -> None:
    st.markdown("<div class='fh6-kicker'>FH6 车辆数据平台</div>", unsafe_allow_html=True)
    st.title(title)
    st.caption(caption)


def runs_table(records: list[dict[str, Any]]) -> None:
    if not records:
        st.info("当前没有 run。")
        return
    frame = pd.DataFrame(records)
    columns = [
        "session_id",
        "created_at",
        "car_name",
        "tune_name",
        "run_type",
        "survey_type",
        "test_scenario",
        "purpose",
        "route_name",
        "duration_seconds",
        "packet_count",
        "detected_lap_count",
        "run_quality_score",
        "quality_status",
    ]
    visible = [column for column in columns if column in frame]
    display = frame[visible].copy()
    if "test_scenario" in display:
        display["test_scenario"] = display["test_scenario"].map(lambda value: label_of("test_scenario", value))
    if "purpose" in display:
        display["purpose"] = display["purpose"].map(lambda value: label_of("dataset_purpose", value))
    if "quality_status" in display:
        display["quality_status"] = display["quality_status"].map(lambda value: label_of("quality_status", value))
    if "run_type" in display:
        display["run_type"] = display["run_type"].map(lambda value: label_of("run_type", value))
    if "survey_type" in display:
        display["survey_type"] = display["survey_type"].map(lambda value: label_of("survey_type", value))
    display = display.rename(columns={
        "session_id": "Run ID",
        "created_at": "创建时间",
        "car_name": "车辆",
        "tune_name": "调校",
        "run_type": "记录类型",
        "survey_type": "测量类型",
        "test_scenario": "测试场景",
        "purpose": "目的",
        "route_name": "路线",
        "duration_seconds": "时长(秒)",
        "packet_count": "数据包",
        "detected_lap_count": "检测圈数",
        "run_quality_score": "质量分",
        "quality_status": "质量状态",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)


def page_dashboard() -> None:
    render_platform_header("首页 Dashboard", "入口是车辆库：从车辆进入调校版本、场景数据集组、runs、圈和记录回顾。")
    platform = read_platform()
    all_runs = runs_by_id()
    cars = platform.get("cars", [])
    groups = [group for car in cars for group in car.get("dataset_groups", [])]
    quality_scores = [float(run.get("run_quality_score", 0) or 0) for run in all_runs.values()]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("车辆数量", len(cars))
    with col2:
        metric_card("数据集组", len(groups))
    with col3:
        metric_card("Runs", len(all_runs))
    with col4:
        metric_card("平均质量分", f"{sum(quality_scores) / len(quality_scores):.1f}" if quality_scores else "0.0")

    if not cars:
        empty_state("还没有车辆。可以先到车辆库创建车辆，或在设置里重建旧 run 索引。")
        if st.button("进入车辆库", type="primary"):
            set_page(PAGE_CARS)
        return

    section_header("车辆库入口", "从车辆进入调校、场景数据集组和记录回顾。")
    for row_start in range(0, len(cars), 3):
        cols = st.columns(3)
        for col, car in zip(cols, cars[row_start : row_start + 3]):
            summary = summarize_car(car, all_runs)
            with col:
                st.markdown("<div class='fh6-card'>", unsafe_allow_html=True)
                st.markdown(f"### {car.get('display_name', '未命名车辆')}")
                st.caption(
                    f"{label_of('drivetrain', car.get('drivetrain'))} · "
                    f"PI {car.get('performance_index') or '未设置'} · "
                    f"{car.get('car_class') or 'unknown'}"
                )
                m1, m2, m3 = st.columns(3)
                with m1:
                    metric_card("Runs", summary["run_count"])
                with m2:
                    metric_card("场景", summary["scenario_count"])
                with m3:
                    metric_card("质量", summary["avg_quality_score"])
                if st.button("进入车辆详情", key=f"open_car_{car['car_id']}", type="primary"):
                    set_page(PAGE_CAR_DETAIL, car_id=str(car["car_id"]))
                st.markdown("</div>", unsafe_allow_html=True)

    section_header("最近记录")
    recent_runs = sorted(all_runs.values(), key=lambda item: str(item.get("created_at", "")), reverse=True)[:5]
    if recent_runs:
        runs_table(recent_runs)
    else:
        empty_state("还没有记录。可以从开始记录页面录制第一条 run。")

    section_header("下一步建议")
    suggestions: list[str] = []
    cars_without_runs = [car for car in cars if summarize_car(car, all_runs)["run_count"] == 0]
    if cars_without_runs:
        suggestions.append(f"优先给 {cars_without_runs[0].get('display_name', '未命名车辆')} 录制一次 baseline。")
    route_items = list_routes(include_inactive=False)
    route_runs = list(all_runs.values())
    routes_without_survey = []
    for route in route_items:
        route_key = str(route.get("key"))
        surveys = [run for run in route_runs if run.get("route_name") == route_key and run.get("run_type") == "track_boundary_survey"]
        if not surveys:
            routes_without_survey.append(route.get("label_zh") or route_key)
    if routes_without_survey:
        suggestions.append(f"路线 {routes_without_survey[0]} 还没有测量数据。")
    if not suggestions:
        suggestions.append("继续积累同车、同路线、同场景的可比较 runs。")
    for item in suggestions:
        st.write(f"- {item}")

    section_header("平台原则")
    st.info("数据质量表示上下文、解释性、可比较性和建模可用性。推头、甩尾、打滑、失控是行为标签，不是质量惩罚。")


def page_cars() -> None:
    render_platform_header("车辆库 My Cars", "车辆是主对象。先建车辆，再管理调校版本、场景数据集组和 runs。")
    platform = read_platform()
    all_runs = runs_by_id()

    with st.expander("Car Manager / 新增车辆", expanded=not platform.get("cars")):
        with st.form("create_car_form"):
            col1, col2, col3 = st.columns(3)
            name = col1.text_input("车辆名称", value="")
            pi = col2.number_input("性能分 PI", min_value=0, max_value=999, value=0)
            drivetrain = select_dictionary("drivetrain", "驱动形式", "RWD", key="new_car_drivetrain")
            col1, col2, col3 = st.columns(3)
            car_class = col1.text_input("车辆等级", value="unknown")
            ordinal = col2.number_input("车辆序号 CarOrdinal（可选）", min_value=0, value=0)
            car_group = col3.text_input("车辆分组（可选）", value="")
            notes = st.text_area("备注", value="")
            submitted = st.form_submit_button("创建车辆", type="primary")
        if submitted:
            if not name.strip():
                st.error("车辆名称不能为空。")
            else:
                car_id = f"car_ordinal_{ordinal}" if ordinal else f"car_{sanitize_filename(name)}"
                if find_car(platform, car_id):
                    st.warning("该车辆已经存在。")
                else:
                    platform.setdefault("cars", []).append({
                        "car_id": car_id,
                        "display_name": name.strip(),
                        "car_ordinal": ordinal or None,
                        "car_class": car_class.strip() or "unknown",
                        "performance_index": pi or None,
                        "drivetrain": drivetrain,
                        "car_group": car_group.strip() or None,
                        "status": "active",
                        "tags": [],
                        "notes": notes.strip(),
                        "tune_versions": [],
                        "dataset_groups": [],
                        "created_at_utc": utc_now(),
                        "updated_at_utc": utc_now(),
                    })
                    write_platform(platform)
                    st.session_state.selected_car_id = car_id
                    st.success("车辆已创建。")
                    st.rerun()

    cars = platform.get("cars", [])
    if not cars:
        empty_state("当前没有车辆。请先创建车辆，或在设置中同步旧 run 索引。")
        return

    section_header("车辆列表", "列表展示车辆状态和可建模数据覆盖。")
    rows = []
    for car in cars:
        summary = summarize_car(car, all_runs)
        rows.append({
            "车辆": car.get("display_name"),
            "car_id": car.get("car_id"),
            "驱动": label_of("drivetrain", car.get("drivetrain")),
            "PI": car.get("performance_index"),
            "调校版本": summary["tune_count"],
            "数据集组": summary["dataset_group_count"],
            "Runs": summary["run_count"],
            "建模准备度": summary["avg_modeling_readiness"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    car_labels = {f"{car.get('display_name')} · {car.get('car_id')}": car for car in cars}
    selected_label = st.selectbox("选择车辆编辑", list(car_labels.keys()))
    car = car_labels[selected_label]
    st.session_state.selected_car_id = car["car_id"]

    with st.form("edit_car_form"):
        col1, col2, col3 = st.columns(3)
        display_name = col1.text_input("车辆名称", value=str(car.get("display_name", "")))
        performance_index = col2.number_input("性能分 PI", min_value=0, max_value=999, value=int(car.get("performance_index") or 0))
        drivetrain = select_dictionary("drivetrain", "驱动形式", car.get("drivetrain", "unknown"), key="edit_car_drivetrain")
        col1, col2, col3 = st.columns(3)
        car_class = col1.text_input("车辆等级", value=str(car.get("car_class", "unknown")))
        car_ordinal = col2.number_input("车辆序号", min_value=0, value=int(car.get("car_ordinal") or 0))
        status = col3.selectbox("状态", ["active", "archived"], index=0 if car.get("status") != "archived" else 1, format_func=lambda x: "启用" if x == "active" else "归档")
        tags = st.text_input("车辆标签（逗号分隔）", value=", ".join(clean_list(car.get("tags"))))
        notes = st.text_area("备注", value=str(car.get("notes", "")))
        if st.form_submit_button("保存车辆", type="primary"):
            car.update({
                "display_name": display_name.strip() or car.get("display_name"),
                "performance_index": performance_index or None,
                "drivetrain": drivetrain,
                "car_class": car_class.strip() or "unknown",
                "car_ordinal": car_ordinal or None,
                "status": status,
                "tags": clean_list(tags),
                "notes": notes.strip(),
                "updated_at_utc": utc_now(),
            })
            write_platform(platform)
            st.success("车辆已保存。")
            st.rerun()

    if st.button("进入当前车辆详情", type="primary"):
        set_page(PAGE_CAR_DETAIL, car_id=str(car["car_id"]))


def render_tune_manager(platform: dict[str, Any], car: dict[str, Any]) -> None:
    st.subheader("Tune Manager / 调校版本")
    tunes = car.setdefault("tune_versions", [])
    if tunes:
        st.dataframe(pd.DataFrame([
            {
                "调校ID": tune.get("tune_id"),
                "名称": tune.get("name"),
                "版本": tune.get("version"),
                "用途": label_of("use_case", tune.get("use_case")),
                "状态": "启用" if tune.get("status") != "archived" else "归档",
                "备注": tune.get("notes"),
            }
            for tune in tunes
        ]), use_container_width=True, hide_index=True)
    with st.form("tune_manager_form"):
        col1, col2, col3 = st.columns(3)
        name = col1.text_input("调校名称", value="stock_default")
        version = col2.text_input("版本", value="v01")
        use_case = select_dictionary("use_case", "用途类型（兼容旧字段）", "road_grip", key="tune_use_case")
        tags = st.text_input("标签（逗号分隔）", value="")
        notes = st.text_area("备注", value="")
        submitted = st.form_submit_button("新增/更新调校版本")
    if submitted:
        stub = {"tune_name": name, "tune_version": version, "use_case": use_case}
        tune_id = stable_tune_id(str(car["car_id"]), stub)
        existing = next((item for item in tunes if item.get("tune_id") == tune_id), None)
        payload = {
            "tune_id": tune_id,
            "name": name.strip() or "unknown_tune",
            "version": version.strip() or "v00",
            "status": "active",
            "tags": clean_list(tags),
            "notes": notes.strip(),
            "use_case": use_case,
            "created_at_utc": existing.get("created_at_utc") if existing else utc_now(),
            "updated_at_utc": utc_now(),
        }
        if existing:
            existing.update(payload)
        else:
            tunes.append(payload)
        write_platform(platform)
        st.success("调校版本已保存。")
        st.rerun()


def render_dataset_group_manager(platform: dict[str, Any], car: dict[str, Any]) -> None:
    st.subheader("Dataset Group Manager / 场景数据集组")
    groups = car.setdefault("dataset_groups", [])
    if groups:
        st.dataframe(pd.DataFrame([
            {
                "组名": group.get("name"),
                "主场景": label_of("test_scenario", group.get("scenario_key")),
                "实验目的": label_of("dataset_purpose", group.get("purpose")),
                "路线": group.get("route_name"),
                "路面": label_of("surface_type", group.get("surface_type")),
                "Runs": len(clean_list(group.get("run_ids"))),
                "状态": "启用" if group.get("status") != "archived" else "归档",
            }
            for group in groups
        ]), use_container_width=True, hide_index=True)
    with st.form("dataset_group_form"):
        col1, col2, col3 = st.columns(3)
        scenario = select_dictionary("test_scenario", "主测试场景", "free_drive", key="group_scenario")
        route = select_dictionary("route", "路线", "horizon_highway_loop", key="group_route")
        surface = select_dictionary("surface_type", "路面", "asphalt", key="group_surface")
        col1, col2 = st.columns(2)
        purpose = select_dictionary("dataset_purpose", "实验目的", "baseline", key="group_purpose")
        purpose_tags = multiselect_dictionary("dataset_purpose", "目的标签", [purpose], key="group_purpose_tags")
        name = st.text_input("组名（可留空自动生成）", value="")
        notes = st.text_area("备注", value="")
        submitted = st.form_submit_button("新增/更新数据集组")
    if submitted:
        stub = {"test_scenario": scenario, "route_name": route, "surface_type": surface, "purpose": purpose, "tags": purpose_tags}
        group_id = stable_group_id(str(car["car_id"]), stub)
        existing = next((item for item in groups if item.get("dataset_group_id") == group_id), None)
        group_name = name.strip() or f"{label_of('test_scenario', scenario)} / {route} / {label_of('dataset_purpose', purpose)}"
        payload = {
            "dataset_group_id": group_id,
            "name": group_name,
            "scenario_key": scenario,
            "purpose": purpose,
            "purpose_tags": purpose_tags,
            "route_name": route,
            "surface_type": surface,
            "tune_ids": existing.get("tune_ids", []) if existing else [],
            "run_ids": existing.get("run_ids", []) if existing else [],
            "segments": existing.get("segments", []) if existing else [],
            "status": "active",
            "tags": purpose_tags,
            "notes": notes.strip(),
            "created_at_utc": existing.get("created_at_utc") if existing else utc_now(),
            "updated_at_utc": utc_now(),
        }
        if existing:
            existing.update(payload)
        else:
            groups.append(payload)
        write_platform(platform)
        st.success("数据集组已保存。")
        st.rerun()


def page_car_detail() -> None:
    render_platform_header("车辆详情 Car Detail", "单车视图集中展示调校、场景组、runs、质量、标签和操控评分。")
    platform = read_platform()
    all_runs = runs_by_id()
    car = selected_car(platform)
    if car is None:
        empty_state("还没有车辆。")
        if st.button("去车辆库创建车辆"):
            set_page(PAGE_CARS)
        return

    car_labels = {f"{item.get('display_name')} · {item.get('car_id')}": item for item in platform.get("cars", [])}
    current_label = next((label for label, item in car_labels.items() if item.get("car_id") == car.get("car_id")), list(car_labels)[0])
    chosen_label = st.selectbox("当前车辆", list(car_labels.keys()), index=list(car_labels.keys()).index(current_label))
    car = car_labels[chosen_label]
    st.session_state.selected_car_id = car["car_id"]

    summary = summarize_car(car, all_runs)
    reviews = read_platform().get("run_reviews", {})
    behavior_counts = behavior_counts_for_car(car, reviews)
    handling_avg = average_scores_for_car(car, reviews, "handling_scores")
    subjective_avg = average_scores_for_car(car, reviews, "subjective_scores")

    st.markdown(f"## {car.get('display_name', '未命名车辆')}")
    status_badge("车辆状态：" + ("已归档" if car.get("status") == "archived" else "启用"), "warning" if car.get("status") == "archived" else "success")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_card("调校版本", summary["tune_count"])
    with col2:
        metric_card("数据集组", summary["dataset_group_count"])
    with col3:
        metric_card("Runs", summary["run_count"])
    with col4:
        metric_card("质量分", summary["avg_quality_score"])
    with col5:
        metric_card("建模准备度", summary["avg_modeling_readiness"])

    base_cols = st.columns(3)
    base_cols[0].info(f"驱动形式：{label_of('drivetrain', car.get('drivetrain'))}")
    base_cols[1].info(f"PI：{car.get('performance_index') or '未设置'}")
    base_cols[2].info(f"等级：{car.get('car_class') or 'unknown'}")
    with advanced_expander("高级信息：车辆 ID / 序号 / 备注"):
        st.write(f"车辆 ID：{car.get('car_id')}")
        st.write(f"车辆序号：{car.get('car_ordinal') or '未设置'}")
        if car.get("notes"):
            st.write(str(car.get("notes")))

    tab_overview, tab_tunes, tab_groups, tab_runs, tab_scores = st.tabs(["概览", "调校版本", "场景数据集组", "Runs / Laps", "行为与评分"])

    with tab_overview:
        section_header("测试覆盖", "缺失项代表还没有对应场景数据，不代表车辆表现差。")
        scenario_keys = [group.get("scenario_key") for group in car.get("dataset_groups", []) if group.get("scenario_key")]
        active_scenarios = [item for item in option_values("test_scenario") if item != "unknown"]
        coverage_rows = [{"测试场景": label_of("test_scenario", scenario), "是否覆盖": "已覆盖" if scenario in scenario_keys else "缺失"} for scenario in active_scenarios]
        st.dataframe(pd.DataFrame(coverage_rows), use_container_width=True, hide_index=True)

        section_header("下一步建议")
        suggestions: list[str] = []
        if summary["run_count"] == 0:
            suggestions.append("先录制一次 baseline 自由驾驶，建立车辆基础样本。")
        if not behavior_counts and summary["run_count"] > 0:
            suggestions.append("已有 run 但缺少人工行为标签，建议进入记录回顾补充。")
        missing = [scenario for scenario in active_scenarios if scenario not in scenario_keys]
        if missing:
            suggestions.append(f"优先补充场景：{label_of('test_scenario', missing[0])}。")
        if summary["avg_modeling_readiness"] < 75 and summary["run_count"] > 0:
            suggestions.append("建模准备度偏低，检查车辆/调校/场景/路线/目的标签是否完整。")
        if not suggestions:
            suggestions.append("覆盖和标签已经具备基础结构，可以继续积累同场景对比 runs。")
        for item in suggestions:
            st.write(f"- {item}")

    with tab_tunes:
        render_tune_manager(platform, car)

    with tab_groups:
        render_dataset_group_manager(platform, car)

    with tab_runs:
        records = car_runs(car, all_runs)
        runs_table(records)
        if records:
            selected_id = st.selectbox("查看 Run 结构", [record["session_id"] for record in records])
            record = all_runs[selected_id]
            col1, col2, col3 = st.columns(3)
            col1.metric("检测圈数", record.get("detected_lap_count", 0))
            col2.metric("Lap reset", record.get("detected_lap_reset_count", 0))
            col3.metric("Segments", len(record.get("segments", [])))
            laps = record.get("laps", [])
            if laps:
                st.dataframe(pd.DataFrame(laps), use_container_width=True, hide_index=True)
            else:
                st.info("当前 run 还没有 lap 摘要。重建索引后会从 CSV 重新检测。")
            if st.button("进入该 Run 的记录回顾", key=f"review_{selected_id}"):
                set_page(PAGE_REVIEW, session_id=selected_id)

    with tab_scores:
        section_header("常见行为标签统计")
        if behavior_counts:
            st.dataframe(pd.DataFrame([{"行为标签": label_of("behavior_tag", tag), "次数": count} for tag, count in behavior_counts.items()]), use_container_width=True, hide_index=True)
        else:
            st.info("还没有行为标签。")

        section_header("操控性人工评分概览")
        if handling_avg:
            st.dataframe(pd.DataFrame([{"维度": label_of("handling_dimension", key), "平均分": value} for key, value in handling_avg.items()]), use_container_width=True, hide_index=True)
        else:
            st.info("还没有操控性评分。")
        if subjective_avg:
            st.subheader("主观评价概览")
            st.dataframe(pd.DataFrame([{"评分项": label_of("subjective_score", key), "平均分": value} for key, value in subjective_avg.items()]), use_container_width=True, hide_index=True)


def page_dataset_groups() -> None:
    render_platform_header("数据集组 Dataset Groups", "数据集组的主分类是测试场景；实验目的通过 purpose 和 tags 补充。")
    platform = read_platform()
    all_runs = runs_by_id()
    cars = platform.get("cars", [])
    if not cars:
        st.warning("请先创建车辆。")
        return
    car_labels = {f"{car.get('display_name')} · {car.get('car_id')}": car for car in cars}
    selected = st.selectbox("选择车辆", list(car_labels.keys()))
    car = car_labels[selected]
    st.session_state.selected_car_id = car["car_id"]
    render_dataset_group_manager(platform, car)

    st.subheader("所有组的 Run 覆盖")
    rows = []
    for group in car.get("dataset_groups", []):
        group_runs = [all_runs[run_id] for run_id in clean_list(group.get("run_ids")) if run_id in all_runs]
        rows.append({
            "组名": group.get("name"),
            "主场景": label_of("test_scenario", group.get("scenario_key")),
            "目的": label_of("dataset_purpose", group.get("purpose")),
            "Runs": len(group_runs),
            "平均质量分": round(sum(float(run.get("run_quality_score", 0) or 0) for run in group_runs) / len(group_runs), 1) if group_runs else 0,
            "路线": group.get("route_name"),
            "路面": label_of("surface_type", group.get("surface_type")),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("当前车辆还没有数据集组。")


def page_routes() -> None:
    render_platform_header("路线库 Routes", "路线是未来 Route Profile / 车辆-赛道世界模型的独立对象。")
    route_items = list_routes(include_inactive=True)
    all_runs = list(runs_by_id().values())
    profiles = read_route_profiles()
    rows = []
    for item in route_items:
        route_name = str(item.get("key"))
        if route_name == "unknown":
            continue
        route_runs = [run for run in all_runs if str(run.get("route_name")) == route_name]
        survey_runs = [run for run in route_runs if run.get("run_type") == "track_boundary_survey"]
        readiness = route_survey_readiness(route_name, survey_runs, profiles)
        rows.append({
            "路线": item.get("label_zh") or route_name,
            "route_key": route_name,
            "Runs": len(route_runs),
            "Survey Runs": len(survey_runs),
            "左边界": readiness["survey_counts"].get("left_boundary", 0),
            "右边界": readiness["survey_counts"].get("right_boundary", 0),
            "参考线": readiness["survey_counts"].get("reference_line", 0),
            "Profiles": len([profile for profile in profiles if profile.get("route_name") == route_name]),
            "准备度": readiness["status_label"],
            "启用": bool(item.get("is_active", True)),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("还没有路线。可以在设置或数据字典管理中新增路线。")

    if route_items:
        selectable = [item for item in route_items if item.get("key") != "unknown"]
        if selectable:
            selected = st.selectbox("选择路线", selectable, format_func=lambda item: str(item.get("label_zh") or item.get("key")))
            st.session_state.selected_route_name = selected.get("key")
            if st.button("进入路线详情", type="primary"):
                set_page(PAGE_ROUTE_DETAIL)


def page_route_detail() -> None:
    render_platform_header("路线详情 / Track Profile", "展示普通 runs、赛道边界测量 runs 和 Route Profile 准备度。")
    route_items = list_routes(include_inactive=True)
    if not route_items:
        empty_state("还没有路线。")
        return
    route_keys = [str(item["key"]) for item in route_items]
    selected_route = str(st.session_state.get("selected_route_name") or route_keys[0])
    if selected_route not in route_keys:
        selected_route = route_keys[0]
    selected_route = st.selectbox("当前路线", route_keys, index=route_keys.index(selected_route), format_func=lambda key: label_of("route", key))
    st.session_state.selected_route_name = selected_route

    all_runs = list(runs_by_id().values())
    route_runs = [run for run in all_runs if str(run.get("route_name")) == selected_route]
    survey_runs = [run for run in route_runs if run.get("run_type") == "track_boundary_survey"]
    normal_runs = [run for run in route_runs if run.get("run_type") != "track_boundary_survey"]
    status = route_profile_status(selected_route)
    profiles = status.get("profiles", [])
    readiness = route_survey_readiness(selected_route, survey_runs, profiles)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_card("普通 Runs", len(normal_runs))
    with col2:
        metric_card("Survey Runs", len(survey_runs))
    with col3:
        metric_card("左边界", readiness["survey_counts"].get("left_boundary", 0))
    with col4:
        metric_card("右边界", readiness["survey_counts"].get("right_boundary", 0))
    with col5:
        metric_card("参考线", readiness["survey_counts"].get("reference_line", 0))

    section_header("Route Profile 准备度", "这里描述用户测得的安全行驶走廊草稿，不代表 FH6 官方赛道边界或 checkpoint 校验。")
    tone = "success" if readiness["can_generate_draft"] else ("warning" if survey_runs else "info")
    status_badge(f"{readiness['status_label']}；Route Profile 数量：{status['profile_count']}", tone)
    if readiness["missing_measurements"]:
        missing = [
            f"{item['label']} 还缺 {item['missing']} 次"
            for item in readiness["missing_measurements"]
            if item.get("missing", 0) > 0
        ]
        st.warning("当前路线测量不足：" + "、".join(missing) + "。建议在开始记录中选择“赛道边界测量”。")

    section_header("Survey Runs", "测量数据只用于路线/走廊资料，不作为默认圈速或调校质量评价。")
    if survey_runs:
        filter_options = ["all"] + option_values("survey_type")
        selected_filter = st.selectbox(
            "测量类型过滤",
            filter_options,
            format_func=lambda key: "全部" if key == "all" else label_of("survey_type", key),
        )
        visible_runs = survey_runs if selected_filter == "all" else [run for run in survey_runs if run.get("survey_type") == selected_filter]
        table = pd.DataFrame(visible_runs)
        visible = [column for column in ["session_id", "survey_type", "created_at", "duration_seconds", "packet_count", "quality_status", "notes"] if column in table]
        display = table[visible].copy()
        if "survey_type" in display:
            display["survey_type"] = display["survey_type"].map(lambda value: label_of("survey_type", value))
        if "quality_status" in display:
            display["quality_status"] = display["quality_status"].map(lambda value: label_of("quality_status", value))
        st.dataframe(
            display.rename(
                columns={
                    "session_id": "run_id",
                    "survey_type": "测量类型",
                    "created_at": "创建时间",
                    "duration_seconds": "时长",
                    "packet_count": "数据包",
                    "quality_status": "质量状态",
                    "notes": "备注",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        with advanced_expander("生成 Route Profile 草稿", expanded=False):
            if not readiness["can_generate_draft"]:
                st.warning("建议补足左右边界和参考线测量后再生成可行驶走廊草稿。")
            selected_run = st.selectbox("从 Survey Run 生成/更新 Route Profile", [run["session_id"] for run in survey_runs])
            selected_record = next(run for run in survey_runs if run["session_id"] == selected_run)
            raw_path_value = selected_record.get("raw_csv_path")
            if st.button("生成 Route Profile", type="primary", disabled=not bool(raw_path_value)):
                raw_path = ROOT / raw_path_value
                profile = build_route_profile_from_csv(
                    raw_path,
                    session_id=selected_run,
                    route_name=selected_route,
                    run_type=str(selected_record.get("run_type") or "track_boundary_survey"),
                    survey_type=selected_record.get("survey_type"),
                    car_id=selected_record.get("car_id"),
                    tune_id=selected_record.get("tune_id"),
                    dataset_group_id=selected_record.get("dataset_group_id"),
                )
                st.success(f"已生成 Route Profile：{profile['profile_id']}；boundary_quality={profile.get('boundary_quality')}")
                st.json(profile.get("source_survey_runs", {}))
                st.rerun()
            if not raw_path_value:
                st.error("该 run 没有 raw CSV 路径。")
    else:
        empty_state("当前路线还没有赛道边界测量 run。")

    section_header("普通 Runs")
    runs_table(normal_runs)

    section_header("Route Profiles")
    if profiles:
        profile_table = pd.DataFrame(profiles)
        visible = [column for column in ["profile_id", "survey_type", "boundary_quality", "source_session_id", "source_survey_runs", "profile_path"] if column in profile_table]
        st.dataframe(profile_table[visible], use_container_width=True, hide_index=True)
    else:
        empty_state("当前路线还没有 Route Profile。")


def render_recording_form() -> None:
    cfg = get_run_config()
    with st.form("record_config_form"):
        section_header("1. 选择车辆")
        col1, col2, col3 = st.columns(3)
        cfg["car_name"] = col1.text_input("车辆名称", value=str(cfg.get("car_name", "")))
        cfg["performance_index"] = col2.number_input("性能分 PI", min_value=0, max_value=999, value=int(cfg.get("performance_index") or 0)) or None
        cfg["drivetrain"] = select_dictionary("drivetrain", "驱动形式", cfg.get("drivetrain", "RWD"), key="record_drivetrain")
        col1, col2, col3 = st.columns(3)
        cfg["car_class"] = col1.text_input("车辆等级", value=str(cfg.get("car_class", "unknown")))
        cfg["car_ordinal"] = col2.number_input("车辆序号 CarOrdinal（可选）", min_value=0, value=int(cfg.get("car_ordinal") or 0)) or None
        cfg["car_group"] = col3.text_input("车辆分组（可选）", value=str(cfg.get("car_group") or ""))

        section_header("2. 选择调校")
        col1, col2 = st.columns(2)
        cfg["tune_name"] = col1.text_input("调校名称", value=str(cfg.get("tune_name", "stock_default")))
        cfg["tune_version"] = col2.text_input("调校版本", value=str(cfg.get("tune_version", "v01")))

        with advanced_expander("详细调校参数（可选）", expanded=False):
            tune = dict(cfg.get("tune", {}))
            keys = list(TUNE_FIELD_LABELS.keys())
            for start in range(0, len(keys), 3):
                cols = st.columns(3)
                for col, field in zip(cols, keys[start : start + 3]):
                    current = "" if tune.get(field) is None else str(tune.get(field))
                    value = col.text_input(TUNE_FIELD_LABELS[field], value=current, key=f"tune_field_{field}")
                    try:
                        tune[field] = float(value) if value.strip() else None
                    except ValueError:
                        tune[field] = None
            cfg["tune"] = tune

        section_header("3. 选择路线与场景")
        col1, col2, col3 = st.columns(3)
        cfg["run_type"] = select_dictionary("run_type", "记录类型", cfg.get("run_type", "normal_recording"), key="record_run_type")
        cfg["test_scenario"] = select_dictionary("test_scenario", "主测试场景", cfg.get("test_scenario", "free_drive"), key="record_scenario")
        cfg["route_name"] = select_dictionary("route", "路线", cfg.get("route_name", "horizon_highway_loop"), key="record_route")
        cfg["surface_type"] = select_dictionary("surface_type", "路面类型", cfg.get("surface_type", "asphalt"), key="record_surface")
        if cfg.get("run_type") == "track_boundary_survey":
            cfg["test_scenario"] = "track_boundary_survey"
            cfg["purpose"] = "model_training"
            cfg["survey_type"] = select_dictionary("survey_type", "测量类型", cfg.get("survey_type", "reference_line"), key="record_survey_type")
            cfg["survey_speed_note"] = st.text_input("测量速度备注", value=str(cfg.get("survey_speed_note", "slow_and_steady")))
            st.info("请低速沿赛道边缘稳定行驶。这次记录用于建立赛道可行驶边界，不用于圈速评价。可以重复测量多次，以提高边界可靠性。")
        col1, col2 = st.columns(2)
        cfg["purpose"] = select_dictionary("dataset_purpose", "实验目的 purpose", cfg.get("purpose", "baseline"), key="record_purpose")
        cfg["purpose_tags"] = multiselect_dictionary("dataset_purpose", "目的标签", cfg.get("purpose_tags", [cfg.get("purpose", "baseline")]), key="record_purpose_tags")
        cfg["use_case"] = select_dictionary("use_case", "用途类型（兼容旧字段）", cfg.get("use_case", "road_grip"), key="record_use_case")

        section_header("4. 检查 Data Out 与辅助设置")
        st.info("FH6 Data Out 建议：On；IP Address = 127.0.0.1；Port = 9999。")
        with advanced_expander("高级设置：UDP 监听"):
            col1, col2, col3 = st.columns(3)
            cfg["host"] = col1.text_input("监听地址", value=str(cfg.get("host", "127.0.0.1")))
            cfg["port"] = col2.number_input("监听端口", min_value=1, max_value=65535, value=int(cfg.get("port", 9999)))
            with col3:
                metric_card("数据包大小", "324 bytes")
            st.caption("同一台电脑通常监听 127.0.0.1:9999。避免 5200-5300。")

        col1, col2, col3, col4 = st.columns(4)
        cfg["assists_abs"] = col1.checkbox("ABS", value=bool(cfg.get("assists_abs", True)))
        cfg["assists_traction_control"] = col2.checkbox("TCS", value=bool(cfg.get("assists_traction_control", False)))
        cfg["assists_stability_control"] = col3.checkbox("STM", value=bool(cfg.get("assists_stability_control", False)))
        cfg["assists_shifting"] = select_dictionary("assists_shifting", "换挡模式", cfg.get("assists_shifting", "manual"), key="record_shifting")

        cfg["tags"] = multiselect_dictionary("general_tag", "通用标签", cfg.get("tags", []), key="record_general_tags")
        cfg["notes"] = st.text_area("备注", value=str(cfg.get("notes", "")))
        cfg["auto_process"] = st.checkbox("停止后自动处理并更新索引", value=bool(cfg.get("auto_process", True)))
        submitted = st.form_submit_button("保存记录设置", type="primary")
    if submitted:
        st.session_state.run_config = cfg
        write_json(TUNE_CONFIG, build_recording_config()["tune_config"])
        st.success("记录设置已保存。")

    config = build_recording_config()
    st.caption("本次将生成的 session_id：")
    st.code(config["session_id"], language="text")


def page_record_run() -> None:
    render_platform_header("开始记录 Record Run", "录制前先明确车辆、调校版本、测试场景和实验目的。")
    render_recording_form()

    st.divider()
    st.subheader("实时记录")
    controller = get_controller()
    state = controller.snapshot()
    active_config = st.session_state.get("active_recording_config") or build_recording_config()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("状态", state.status)
    col2.metric("数据包", state.packet_count)
    col3.metric("丢弃", state.dropped_count)
    col4.metric("采样率", f"{state.sample_rate:.1f}/s")

    col1, col2, col3 = st.columns(3)
    if col1.button("开始记录", disabled=controller.is_running(), type="primary"):
        config = build_recording_config()
        st.session_state.active_recording_config = config
        controller.start(config)
        st.rerun()
    if col2.button("停止记录", disabled=not controller.is_running()):
        controller.stop()
        stopped = controller.snapshot()
        session_id = stopped.session_id
        if session_id and bool(active_config.get("auto_process", True)):
            with st.spinner("正在后处理并更新索引..."):
                process_session(session_id)
                metadata = active_config.get("metadata", {})
                if metadata.get("run_type") == "track_boundary_survey":
                    raw_path = RAW_DIR / f"{session_id}.csv"
                    record = index_session(session_id)
                    build_route_profile_from_csv(
                        raw_path,
                        session_id=session_id,
                        route_name=str(metadata.get("route_name") or "unknown"),
                        run_type="track_boundary_survey",
                        survey_type=metadata.get("survey_type"),
                        car_id=record.get("car_id"),
                        tune_id=record.get("tune_id"),
                        dataset_group_id=record.get("dataset_group_id"),
                    )
                sync_platform_with_runs(read_index())
        if session_id:
            st.session_state.selected_review_session_id = session_id
            st.session_state.last_stopped_session_id = session_id
        st.session_state.pop("active_recording_config", None)
        st.rerun()
    if col3.button("刷新"):
        st.rerun()

    if state.error:
        st.error(state.error)
    if state.csv_path:
        st.code(state.csv_path, language="text")
    if state.latest:
        latest = state.latest
        st.subheader("最新遥测预览")
        cols = st.columns(6)
        cols[0].metric("速度", f"{float(latest.get('speed', 0.0)) * 3.6:.1f} km/h")
        cols[1].metric("RPM", f"{float(latest.get('current_engine_rpm', 0.0)):.0f}")
        cols[2].metric("挡位", latest.get("gear", ""))
        cols[3].metric("油门", f"{int(latest.get('accel', 0)) / 255:.2f}")
        cols[4].metric("刹车", f"{int(latest.get('brake', 0)) / 255:.2f}")
        cols[5].metric("转向", f"{int(latest.get('steer', 0)) / 127:.2f}")
    else:
        st.info("还没有收到数据包。确认 FH6 Data Out = On，IP = 127.0.0.1，端口 = 9999。")

    last_session = st.session_state.get("last_stopped_session_id")
    if last_session:
        st.success(f"最近停止的 run：{last_session}")
        if st.button("进入记录回顾", type="primary"):
            set_page(PAGE_REVIEW, session_id=last_session)


def page_run_review() -> None:
    render_platform_header("记录回顾 Run Review", "人工标签表示驾驶者主观反馈和实验意图，不等于 telemetry 真值。")
    runs = read_index()
    if not runs:
        st.warning("还没有 run。")
        return
    session_ids = [str(run["session_id"]) for run in runs if run.get("session_id")]
    default_id = st.session_state.get("selected_review_session_id") or session_ids[0]
    if default_id not in session_ids:
        default_id = session_ids[0]
    session_id = st.selectbox("选择 Run", session_ids, index=session_ids.index(default_id))
    st.session_state.selected_review_session_id = session_id
    record = next(run for run in runs if run.get("session_id") == session_id)
    review = get_run_review(session_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("车辆", record.get("car_name", "unknown"))
    with col2:
        metric_card("场景", label_of("test_scenario", record.get("test_scenario")))
    with col3:
        metric_card("质量分", record.get("run_quality_score", 0))
    with col4:
        metric_card("检测圈数", record.get("detected_lap_count", 0))

    st.info("推头、甩尾、打滑、失控等行为不会降低数据质量；请在行为标签中标注。质量问题主要是上下文缺失、采样异常、时间 gap、lap 分段不清等。")

    with st.form("run_review_form"):
        intent_tags = multiselect_dictionary("intent_tag", "本次是否故意制造某种状态？", review.get("intent_tags"), key="review_intent_tags")
        behavior_tags = multiselect_dictionary("behavior_tag", "车辆行为标签", review.get("behavior_tags"), key="review_behavior_tags")
        data_status_tags = multiselect_dictionary("data_status", "数据状态", review.get("data_status_tags"), key="review_data_status_tags")
        quality_state_tags = multiselect_dictionary("run_state_tag", "记录状态标签", review.get("quality_state_tags"), key="review_quality_state_tags")
        purpose_tags = multiselect_dictionary("dataset_purpose", "实验目的标签", review.get("purpose_tags"), key="review_purpose_tags")

        st.subheader("操控性 Handling Evaluation")
        st.caption("操控性不是单一指标。先作为人工评分字段保留，后续再接评估系统。")
        handling_scores: dict[str, int | None] = {}
        for start in range(0, len(HANDLING_SCORE_KEYS), 3):
            cols = st.columns(3)
            for col, key in zip(cols, HANDLING_SCORE_KEYS[start : start + 3]):
                item = next((row for row in read_dictionary_items("handling_dimension") if row["key"] == key), {})
                with col:
                    handling_scores[key] = score_select(label_of("handling_dimension", key), review.get("handling_scores", {}).get(key), key=f"handling_score_{key}", help_text=item.get("description_zh") or None)

        st.subheader("主观评价")
        subjective_scores: dict[str, int | None] = {}
        for start in range(0, len(SUBJECTIVE_SCORE_KEYS), 3):
            cols = st.columns(3)
            for col, key in zip(cols, SUBJECTIVE_SCORE_KEYS[start : start + 3]):
                with col:
                    subjective_scores[key] = score_select(label_of("subjective_score", key), review.get("subjective_scores", {}).get(key), key=f"subjective_score_{key}")
        notes = st.text_area("备注", value=str(review.get("notes", "")))
        submitted = st.form_submit_button("保存记录回顾", type="primary")

    if submitted:
        saved = save_run_review(session_id, {
            "intent_tags": intent_tags,
            "behavior_tags": behavior_tags,
            "data_status_tags": data_status_tags,
            "quality_state_tags": quality_state_tags,
            "purpose_tags": purpose_tags,
            "handling_scores": handling_scores,
            "subjective_scores": subjective_scores,
            "notes": notes,
        })
        index_session(session_id)
        sync_platform_with_runs(read_index())
        st.success("记录回顾已保存。")
        with advanced_expander("已保存内容"):
            st.json(saved)

    with advanced_expander("高级信息：质量详情 / Laps / 状态计数"):
        col1, col2 = st.columns(2)
        with col1:
            st.json(record.get("quality", {}))
        with col2:
            if record.get("laps"):
                st.dataframe(pd.DataFrame(record.get("laps", [])), use_container_width=True, hide_index=True)
            if record.get("state_tag_counts"):
                st.dataframe(pd.DataFrame([{"状态": label_of("run_state_tag", key), "样本数": value} for key, value in record.get("state_tag_counts", {}).items()]), use_container_width=True, hide_index=True)


def dictionary_editor(group: str, *, key_prefix: str) -> None:
    items = read_dictionary_items(group, include_inactive=True)
    columns = ["key", "label_zh", "label_en", "description_zh", "description_en", "is_active", "sort_order"]
    frame = pd.DataFrame(items).reindex(columns=columns)
    edited = st.data_editor(
        frame,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=f"{key_prefix}_{group}_editor",
        column_config={
            "key": st.column_config.TextColumn("Key（内部稳定值）", required=True),
            "label_zh": st.column_config.TextColumn("中文显示名"),
            "label_en": st.column_config.TextColumn("英文名（内部/兼容）"),
            "description_zh": st.column_config.TextColumn("中文说明"),
            "description_en": st.column_config.TextColumn("英文说明"),
            "is_active": st.column_config.CheckboxColumn("启用", default=True),
            "sort_order": st.column_config.NumberColumn("排序", step=1, min_value=0),
        },
    )
    col1, col2 = st.columns(2)
    if col1.button("保存", type="primary", key=f"{key_prefix}_{group}_save"):
        cleaned: list[dict[str, Any]] = []
        seen: set[str] = set()
        duplicate_count = 0
        for idx, row in enumerate(edited.to_dict("records")):
            item = normalize_dictionary_item(row, fallback_sort=(idx + 1) * 10)
            if not item:
                continue
            if item["key"] in seen:
                duplicate_count += 1
                continue
            seen.add(item["key"])
            cleaned.append(item)
        if not cleaned:
            st.error("至少保留一条有效选项。")
        else:
            cleaned.sort(key=lambda item: (item.get("sort_order", 0), item.get("key", "")))
            save_dictionary_items(group, cleaned)
            if duplicate_count:
                st.warning(f"已忽略 {duplicate_count} 条重复 key。")
            st.success("已保存。")
            st.rerun()
    if col2.button("恢复默认", key=f"{key_prefix}_{group}_reset"):
        save_dictionary_items(group, default_dictionary_items(group))
        st.success("已恢复默认。")
        st.rerun()


def page_tag_manager() -> None:
    render_platform_header("标签管理 Tag Manager", "标签用于解释 run 的实验意图、车辆行为和记录状态；内部保存稳定英文 key。")
    groups = ["general_tag", "intent_tag", "behavior_tag", "run_state_tag", "dataset_purpose", "handling_dimension", "subjective_score"]
    group = st.selectbox("标签类别", groups, format_func=dictionary_group_label)
    dictionary_editor(group, key_prefix="tag_manager")


def page_dictionary_manager() -> None:
    render_platform_header("数据字典管理 Dictionary Manager", "维护场景、目的、路面、路线、标签、质量状态等平台字典。")
    group = st.selectbox("字典类别", list(DICTIONARY_SPECS.keys()), format_func=dictionary_group_label)
    dictionary_editor(group, key_prefix="dictionary_manager")


def page_settings() -> None:
    render_platform_header("设置 Settings", "索引维护、质量定义、路线管理和兼容旧流程的工具。")
    st.subheader("索引维护")
    col1, col2, col3 = st.columns(3)
    if col1.button("重建 Run 索引", type="primary"):
        with st.spinner("正在从 data/sessions 和 CSV 重建索引..."):
            records = rebuild_index()
            sync_platform_with_runs(records)
        st.success(f"已重建 {len(records)} 条 run。")
    if col2.button("同步平台索引"):
        sync_platform_with_runs(read_index())
        st.success("平台索引已同步。")
    if col3.button("刷新默认字典"):
        ensure_all_dictionaries()
        st.success("默认字典已检查并合并。")

    section_header("数据完整性检查", "只生成警告和报告，不阻止 UI 启动。")
    if st.button("生成数据完整性报告"):
        result = check_data_integrity()
        report_path = write_data_integrity_report(result)
        count = result.get("summary", {}).get("issue_count", 0)
        if count:
            st.warning(f"发现 {count} 条完整性警告，报告已写入：{report_path}")
        else:
            st.success(f"未发现完整性警告，报告已写入：{report_path}")

    st.subheader("数据质量定义")
    st.markdown(
        """
- 质量表示数据是否有清楚上下文、能否被正确解释、能否比较、能否用于后续建模。
- Run Quality Score 关注 metadata 完整度、车辆/调校/场景明确性、记录时长、packet count、sample rate、timestamp gap、lap 切分、暂停/静止状态是否标记、route / purpose / tags 是否完整。
- 推头、甩尾、出弯打滑、失控、压路肩、悬挂到底不是低质量数据；它们应进入行为标签或状态标签。
"""
    )

    st.subheader("Route Manager / 路线管理")
    dictionary_editor("route", key_prefix="route_manager")

    st.subheader("单文件质量检查")
    raw_files = sorted(RAW_DIR.glob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    if raw_files:
        selected = st.selectbox("原始 CSV", raw_files, format_func=lambda path: path.name)
        if st.button("计算质量"):
            st.json(compute_data_quality_for_csv(selected))
    else:
        st.info("没有原始 CSV。")

    st.subheader("路径")
    st.code(f"平台索引：{PLATFORM_INDEX_PATH}\nRun 索引：{ROOT / 'data' / 'index' / 'runs_index.json'}", language="text")


def main() -> None:
    st.set_page_config(page_title="FH6 车辆数据平台", layout="wide")
    apply_theme()
    ensure_dirs()
    pages = {
        PAGE_DASHBOARD: page_dashboard,
        PAGE_CARS: page_cars,
        PAGE_CAR_DETAIL: page_car_detail,
        PAGE_GROUPS: page_dataset_groups,
        PAGE_ROUTES: page_routes,
        PAGE_ROUTE_DETAIL: page_route_detail,
        PAGE_RECORD: page_record_run,
        PAGE_REVIEW: page_run_review,
        PAGE_TAGS: page_tag_manager,
        PAGE_DICTIONARY: page_dictionary_manager,
        PAGE_SETTINGS: page_settings,
    }
    pending_page = st.session_state.pop("_pending_page", None)
    if pending_page in pages:
        st.session_state.nav_widget = pending_page
    if "nav_widget" not in st.session_state or st.session_state.nav_widget not in pages:
        st.session_state.nav_widget = PAGE_DASHBOARD
    st.sidebar.markdown("## FH6 平台")
    selected_page = st.sidebar.radio("主导航", list(pages.keys()), key="nav_widget")
    pages[selected_page]()


if __name__ == "__main__":
    main()
