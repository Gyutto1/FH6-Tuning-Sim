# PySide6 Desktop MVP Brief

更新时间：2026-05-30

## PySide6 MVP 目标

本 MVP 的目标是验证 FH6 Tuning Sim 可以作为本地桌面车辆数据平台运行，而不是继续把 Streamlit 作为最终产品 UI。

本轮只做小范围桌面 proof of concept：

- 新增 PySide6 桌面入口。
- 复用现有数据文件和 store。
- 以车辆为中心展示数据。
- 保持现有 CLI、Streamlit、packet parser、UDP listener、raw telemetry schema 不变。

目标启动命令：

```powershell
python -m fh6_tuning_sim.ui_desktop.app
```

第一目标车辆：

```text
Mercedes-AMG GT S1 PI900
```

当前数据中的对应记录：

```text
car_id: car_ordinal_4265
display_name: Mercedes-AMG GT
performance_index: 900
drivetrain: RWD
```

## 主流程

第一版桌面 MVP 的主流程固定为：

```text
首页
  -> 车辆库
  -> 车辆卡片
  -> 车辆详情
  -> 开始记录
```

页面职责：

- 首页：显示车辆数、run 数、未绑定/未归档 run 数、最近记录、车辆预览。
- 车辆库：用车辆卡片展示已有车辆，不用表格作为主视图。
- 车辆卡片：显示车辆名、等级/PI、驱动形式、run 数、dataset group 数、最近记录、建模准备度。
- 车辆详情：显示选中车辆的信息、调校版本、dataset groups、runs、测试覆盖 placeholder。
- 开始记录：必须从选中车辆上下文进入，清晰显示当前车辆；Start/Stop 可先占位，除非接入现有 `RecordingController` 很小且不扩大范围。

## 需要新增的目录结构

建议新增：

```text
fh6_tuning_sim/ui_desktop/
  __init__.py
  app.py
  main_window.py
  pages/
    dashboard_page.py
    cars_page.py
    car_detail_page.py
    record_run_page.py
    tag_library_page.py
    settings_page.py
  widgets/
    car_card.py
    metric_card.py
    tag_chip.py
    section_header.py
  services/
    desktop_data_service.py
```

桌面 data service 应提供：

```text
list_cars()
get_car(car_id)
list_runs_for_car(car_id)
list_dataset_groups_for_car(car_id)
list_routes()
list_tags_by_category()
list_unassigned_runs()
```

## 需要复用的现有数据 / Store

优先复用：

```text
data/index/runs_index.json
data/platform/platform_index.json
configs/dictionaries/*.json
data/sessions/*_meta.json
data/sessions/*_tune.json
data/raw/*.csv
data/processed/*_processed.csv
reports/*
```

优先复用 helper：

```text
fh6_tuning_sim/data_management/json_store.py
fh6_tuning_sim/data_management/run_index.py
fh6_tuning_sim/data_management/platform_store.py
fh6_tuning_sim/data_management/dictionaries.py
fh6_tuning_sim/data_management/annotation_store.py
fh6_tuning_sim/data_management/route_store.py
fh6_tuning_sim/data_management/route_profile.py
```

读取规则：

- 使用 safe JSON / store helper。
- 缺失 optional index 时显示 empty state，不崩溃。
- UI 不直接暴露 raw JSON。
- 内部保存稳定英文 key，默认 UI 显示中文 label。
- 标签、评分、备注、派生分析必须留在 annotation/review 层，不写入 raw CSV。

## 不允许做的事情

- 不实现 AI training。
- 不实现 reinforcement learning。
- 不实现 automatic tune optimizer。
- 不实现 world-model training。
- 不实现完整 Route Profile algorithm。
- 不实现 full lap simulation。
- 不做复杂 3D visualization。
- 不迁移 SQLite。
- 不打包 EXE。
- 不修改 packet parser。
- 不修改 UDP listener。
- 不修改 raw telemetry schema。
- 不删除 Streamlit。
- 不重写整个后端。
- 不把 Streamlit 全量功能迁移到桌面 MVP。
- 不 hard-delete 现有 data/config 文件。
- 不在 UI 页面硬编码用户可见字典分类。

## 成功标准

MVP 完成后应满足：

- 可以用 `python -m fh6_tuning_sim.ui_desktop.app` 启动桌面窗口。
- 首页显示平台概览。
- 车辆库显示已有车辆卡片，包括 Mercedes-AMG GT。
- 可以从车辆卡片进入车辆详情。
- 车辆详情显示该车辆相关 runs / dataset groups。
- 可以从车辆详情进入开始记录页面。
- 标签库以视觉化 chips/cards 展示标签，而不是后端表格。
- Streamlit 文件仍然存在且未被删除。
- 现有 CLI 行为未破坏。
- 现有测试通过。

## 验证命令

优先使用虚拟环境解释器：

```powershell
.\.venv\Scripts\python.exe -m compileall fh6_tuning_sim
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m fh6_tuning_sim.ui_desktop.app
```

如果 GUI 不能自动验证，至少记录：

```powershell
.\.venv\Scripts\python.exe -c "import PySide6; print('PySide6 import ok')"
.\.venv\Scripts\python.exe -c "import fh6_tuning_sim.ui_desktop.app; print('desktop app import ok')"
```

并在 `reports/pyside6_mvp_report.md` 中写清楚 GUI 自动验证是否跳过、跳过原因和人工验证步骤。
