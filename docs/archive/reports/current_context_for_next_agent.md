# 给下一位 Agent 的当前上下文

更新时间：2026-05-30

## 简短总结

FH6 Tuning Sim 当前处于 v0.3.1 稳定化阶段。下一项任务是小范围 PySide6 desktop MVP，不是后端重写。

项目已有遥测管线、Streamlit 原型、安全 JSON helper、run index、vehicle-centered platform index。下一位 agent 应新增 `fh6_tuning_sim/ui_desktop/`，并保持实现范围小。

## 当前目标

项目目标是构建一个本地桌面的 FH6 车辆数据平台。

产品应保持车辆中心：

- Dashboard。
- My Cars。
- Car Detail。
- Routes / Route Detail。
- Record Run。
- Run Review。
- Dataset Groups。
- Tag Manager。
- Dictionary Manager。
- Settings。

下一项 MVP 任务只实现其中一部分。

## 当前版本状态

当前优先级：

```text
v0.3.1 stabilization
```

当前代码库已有：

- UDP receiver/listener。
- Packet parser。
- Raw telemetry CSV logger。
- Feature engineering。
- Plot generation。
- Markdown report generation。
- Run comparison。
- Dataset builder。
- Streamlit UI prototype。
- Safe JSON store helpers。
- Vehicle-centered platform index。
- Data integrity warnings/reporting。

当前代码库还没有：

- `fh6_tuning_sim/ui_desktop/`
- PySide6 dependency declaration。
- PySide6 app entry point。
- Desktop MVP report。

## Streamlit 状态

Streamlit 保留在项目中。

不要删除或重写：

```text
fh6_tuning_sim/ui/app.py
fh6_tuning_sim/ui/theme.py
start_ui.bat
```

Streamlit 角色：

- 开发后台。
- 原型参考。
- 数据调试工具。

Desktop 是新的产品 UI 方向，但 Streamlit 仍然有用。

## Desktop MVP 决策

下一项精确任务：

```text
PySide6 Desktop MVP
```

要求命令：

```powershell
python -m fh6_tuning_sim.ui_desktop.app
```

第一目标车辆：

```text
Mercedes-AMG GT S1 PI900
```

当前数据映射：

```text
car_id: car_ordinal_4265
display_name: Mercedes-AMG GT
performance_index: 900
drivetrain: RWD
```

## 当前数据和 Store 结构

重要数据文件：

```text
data/index/runs_index.json
data/platform/platform_index.json
configs/dictionaries/*.json
data/raw/*.csv
data/processed/*_processed.csv
data/sessions/*_meta.json
data/sessions/*_tune.json
reports/*
```

当前观察到的状态：

- `data/index/runs_index.json`：存在，4 条 runs。
- `data/platform/platform_index.json`：存在，2 辆 cars。
- 主要真实/演示车辆：
  - `Mercedes-AMG GT`
  - `demo car`
- 可选文件可能缺失，不能阻塞启动：
  - `data/index/annotations.json`
  - `data/platform/route_profiles.json`

重要 helper 模块：

```text
fh6_tuning_sim/data_management/json_store.py
fh6_tuning_sim/data_management/run_index.py
fh6_tuning_sim/data_management/platform_store.py
fh6_tuning_sim/data_management/dictionaries.py
fh6_tuning_sim/data_management/annotation_store.py
fh6_tuning_sim/data_management/route_store.py
fh6_tuning_sim/data_management/route_profile.py
```

应复用这些 helper。不要把 raw JSON 结构直接暴露给 desktop page widgets。

## 现有 CLI 命令

启动 launcher：

```powershell
.\start_fh6_tool.bat
```

启动 Streamlit：

```powershell
.\start_ui.bat
.\.venv\Scripts\python.exe -m streamlit run fh6_tuning_sim/ui/app.py
```

记录：

```powershell
python -m fh6_tuning_sim.receiver.udp_listener --host 127.0.0.1 --port 9999 --tune-config configs/tune_config.json --notes "baseline road grip run"
```

处理：

```powershell
python -m fh6_tuning_sim.analysis.feature_engineering data/raw/<session_id>.csv --output data/processed/<session_id>_processed.csv
```

画图：

```powershell
python -m fh6_tuning_sim.visualization.plot_timeseries data/processed/<session_id>_processed.csv --output reports/<session_id>_timeseries.png
```

报告：

```powershell
python -m fh6_tuning_sim.analysis.report_generator data/processed/<session_id>_processed.csv --metadata data/sessions/<session_id>_meta.json --tune-config data/sessions/<session_id>_tune.json --output reports/<session_id>_report.md
```

对比：

```powershell
python -m fh6_tuning_sim.analysis.tune_compare data/processed/run_a.csv data/processed/run_b.csv --left-name baseline --right-name revised --output reports/baseline_vs_revised.md
```

Dataset builder：

```powershell
python -m fh6_tuning_sim.models.dataset data/processed/<session_id>_processed.csv --output data/processed/<session_id>_dataset.npz --past-samples 60 --future-samples 12
```

## 现有测试

运行：

```powershell
.\.venv\Scripts\python.exe -m compileall fh6_tuning_sim
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

现有测试覆盖：

- Packet parser。
- Analysis pipeline。
- Stabilization helpers。
- Safe JSON。
- Route survey readiness。
- Integrity warnings/report generation。

## 已知问题

- PySide6 缺失，依赖和本地环境都还没准备。
- 当前工作区里 `python` 不在 PATH，应使用 `.\.venv\Scripts\python.exe`。
- Desktop package 尚不存在。
- Streamlit UI 可用，但最终产品 UX 方向需要更轻量的桌面 UI。
- 可选 index 文件可能不存在。
- 部分历史生成文本可能有编码遗留；除非明确要求，不要把全局清理纳入 desktop MVP。

## 下一项精确任务

实现 PySide6 Desktop MVP。

要求文件/目录：

```text
fh6_tuning_sim/ui_desktop/app.py
fh6_tuning_sim/ui_desktop/main_window.py
fh6_tuning_sim/ui_desktop/services/desktop_data_service.py
fh6_tuning_sim/ui_desktop/pages/dashboard_page.py
fh6_tuning_sim/ui_desktop/pages/cars_page.py
fh6_tuning_sim/ui_desktop/pages/car_detail_page.py
fh6_tuning_sim/ui_desktop/pages/record_run_page.py
fh6_tuning_sim/ui_desktop/pages/tag_library_page.py
fh6_tuning_sim/ui_desktop/pages/settings_page.py
fh6_tuning_sim/ui_desktop/widgets/car_card.py
fh6_tuning_sim/ui_desktop/widgets/metric_card.py
fh6_tuning_sim/ui_desktop/widgets/tag_chip.py
fh6_tuning_sim/ui_desktop/widgets/section_header.py
```

要求 service API：

```text
list_cars()
get_car(car_id)
list_runs_for_car(car_id)
list_dataset_groups_for_car(car_id)
list_routes()
list_tags_by_category()
list_unassigned_runs()
```

要求 MVP 行为：

- Dashboard 显示车辆数、run 数、未归档/未绑定 run、最近记录、车辆预览。
- Cars page 使用卡片，不使用后端表格作为主视图。
- Car Detail 显示选中车辆、dataset groups、runs。
- Record Run 从选中车辆上下文进入。
- Tag Library 使用可视化 grouped chips/cards。
- Settings 可以是最小 placeholder。

## Do-Not-Do List

- 不做 AI training。
- 不做 reinforcement learning。
- 不做 automatic tune optimizer。
- 不做 world model training。
- 不修改 packet parser。
- 不修改 raw telemetry schema。
- 不重写 UDP listener。
- 不迁移 SQLite。
- 不打包 EXE。
- 不做完整 Route Profile algorithm。
- 不删除 Streamlit。
- 不 hard-delete 数据或配置文件。

## 报告要求

PySide6 MVP 实现后，写：

```text
reports/pyside6_mvp_report.md
```

报告语言：中文。

包括：

- 已实现页面。
- 数据读取方式。
- 复用的 store/service。
- 未实现功能。
- 测试结果。
- 是否建议继续 PySide6 UI 路线。
