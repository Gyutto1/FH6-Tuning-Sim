# FH6 Tuning Sim v0.99.1 架构、菜单结构与参数填充指南

日期: 2026-05-31

本文档详细解释当前 FH6 Tuning Sim Desktop v0.99.1 的程序架构、SQLite 数据层级、菜单目录结构，以及后续真实游戏数据（改装件、调校参数、性能总览）应填入哪些表和字段。

**本文档不包含任何代码实现建议。**

---

## 1. 当前总体架构

项目分为以下各层，数据从底层到 UI 逐层传递：

```
+--------------------------------------------------+
|              PySide6 Desktop UI (v0.99.1)        |
|  main_window.py -> pages/ dialogs/ widgets/       |
+--------------------------------------------------+
|          DesktopDataService (SQLite Facade)       |
|  services/desktop_data_service.py                 |
|  services/recording_context_service.py            |
+--------------------------------------------------+
|         Repository Layer (事务读写)               |
|  db/repositories/ (9个 Repository 类)             |
+--------------------------------------------------+
|         SQLite Database (主存储)                   |
|  data/fh6_tuning_sim.db                          |
|  data/demo/fh6_demo.db                           |
+--------------------------------------------------+
|  UDP Listener / Packet Parser / Raw CSV           |
|  (保护模块，v0.99 不修改)                          |
+--------------------------------------------------+
|  Legacy: JSON index files | Streamlit debug UI   |
|  (保留不删)                                       |
+--------------------------------------------------+
```

### 各层作用

| 层 | 作用 | 关键文件 |
| --- | --- | --- |
| **SQLite Database** | 主存储。所有实体和数据关系通过外键约束保证完整性。激活 PRAGMA foreign_keys = ON。 | db/schema.sql |
| **Connection Layer** | 提供 connect()、transaction()（事务包装）、row_to_dict() 等工具函数。 | db/connection.py |
| **Migration** | init_schema() 幂等执行 schema.sql，通过 schema_version 表记录版本。legacy_migration.py 负责 JSON -> SQLite 迁移。 | db/migrations.py, db/legacy_migration.py |
| **Repository Layer** | 每个 Repository 封装对单类实体（Car/Build/Tune 等）的 CRUD 操作，所有写操作通过 transaction() 提交。 | db/repositories/ |
| **DesktopDataService** | PySide6 UI 的唯一数据入口。聚合多个 Repository 调用，提供 UI 友好格式的字典。页面不直接写 SQL。 | ui_desktop/services/desktop_data_service.py |
| **RecordingContextService** | 在 Recording 启动前验证 Car/Build/Tune/Setup Snapshot/Route/Intent Tags 上下文完整性。 | db/services/recording_context_service.py |
| **RecordingWorker** | QThread 中运行 UDP 接收循环，非阻塞。复用现有 packet_parser 和 TelemetryCsvLogger。 | ui_desktop/services/recording_worker.py |
| **PySide6 Pages** | 用户可见界面，通过 MainWindow 的 QStackedWidget 导航。 | ui_desktop/pages/ |
| **Widgets** | 可复用 UI 组件：CarCard、MetricCard、SectionHeader、TagChip。 | ui_desktop/widgets/ |
| **Dictionaries** | 中文标签映射（drivetrain、surface_type、use_case 等）。UI 显示中文 label 但内部存储英文 key。 | data_management/dictionaries.py |
| **Tests** | 7 个测试文件，46 个测试用例，覆盖 repository、schema、recording context、run library filter 等。 | tests/ |

### 数据流向（SQLite -> UI）

```
SQLite Row (sqlite3.Row)
  -> Repository 返回 dict
  -> DesktopDataService 组装 UI-friendly dict（含 Chinese labels、tag items 等）
  -> PySide6 Page/Widget 渲染为 QLabel/QPushButton/QFrame
```

UI 从不直接写 SQL。所有写操作通过 DesktopDataService.method() -> Repository.method() -> transaction() 完成。

---

## 2. 核心数据层级

```
Car ----+ Build ----+ Tune ----+ Setup Snapshot ----+ Run
  |          |           |              |                  |
  |          |           |              |                  +-- Route
  |          |           |              |                  +-- Tags (run_tags)
  |          |           |              |                  +-- Annotations
  |          |           |              |                  +-- Recording Session
  |          |           |              |
  |          |           +-- tune_parameter_definitions
  |          |           +-- tune_parameter_values
  |          |
  |          +-- build_snapshots
  |          +-- upgrade_categories / upgrade_options
  |          +-- build_upgrade_selections
  |          +-- upgrade_compatibility_rules
  |
  +-- (车辆本体，无 parent)
```

### 2.1 Car（车辆）

表示车辆本体。在 FH6 中每辆车有唯一 car_ordinal。

**核心字段：**

| 字段 | 说明 |
| --- | --- |
| car_id | 主键，格式如 car_amg_gt |
| display_name | 显示名称，如 "Mercedes-AMG GT" |
| car_ordinal | FH6 游戏中车辆序号 |
| car_group | FH6 车辆分组 |
| default_car_class | 默认等级，如 "S1" |
| default_pi | 默认 PI（性能指数） |
| default_drivetrain | 默认驱动形式，如 "RWD" |
| status / is_active | active / archived（不硬删除） |
| notes | 用户备注 |
| source | manual / demo_seed / system_default |

**对应 UI：** Car Detail Page --- 显示 PI、Class、Drivetrain、Build Cards 列表、Recent Runs

### 2.2 Build（改装版本）

表示硬件/改装组合。Build != Tune：Build 回答「车上装了什么」，Tune 回答「这些零件怎么调的」。

**核心字段：**

| 字段 | 说明 |
| --- | --- |
| build_id | 主键，格式如 car_amg_gt__build__stage_2_awd |
| car_id | 外键 -> cars |
| display_name | 如 "Stage 2 AWD" |
| build_key | 内部 key，如 "stage_2_awd" |
| status / is_active | 归档控制 |

**Build 关联的子数据：**
- build_snapshots --- 本次 Build 的性能快照（PI/Class/Power/Weight 等）
- build_upgrade_selections --- 具体选择哪个改装件（通过 upgrade_categories/options）
- Tunes --- 属于此 Build 的所有 Tune

**对应 UI：** Build Detail Page --- 显示 Build Snapshot、Upgrade Selections、Tunes 列表、Runs

### 2.3 Tune（调校版本）

表示某个 Build 下的调校参数组合。一个 Build 可以有多个 Tune。

**核心字段：**

| 字段 | 说明 |
| --- | --- |
| tune_id | 主键，格式如 build_amg_stage2__tune__high_speed_stability__v01 |
| build_id | 外键 -> builds |
| display_name | 如 "high_speed_stability" |
| tune_key | 内部 key |
| version | 版本号如 "v00", "v01" |

**Tune 关联的子数据：**
- tune_parameter_values --- 本次 Tune 的具体参数值（胎压、齿比、弹簧刚度等）
- Setup Snapshots --- 本次 Tune 确认后的快照

**对应 UI：** Tune Detail Page --- 显示 Tune Parameter Editor、Setup Snapshots、Runs

### 2.4 Setup Snapshot（记录前快照）

表示 Build + Tune 确认后、开始 Recording 前的车辆最终状态。**这是 recording 前必须绑定的上下文。**

**核心字段：**

| 字段 | 说明 |
| --- | --- |
| setup_snapshot_id | 主键 |
| car_id | 外键 -> cars |
| build_id | 外键 -> builds |
| tune_id | 外键 -> tunes |
| snapshot_name | 如 "AMG Stage 2 Baseline" |
| pi | 当前 PI |
| car_class | 当前等级 |
| drivetrain | 当前驱动形式 |
| power / torque | 马力 / 扭矩 |
| weight / front_weight_percent | 重量 / 前轴重量比 |
| tire_compound | 轮胎配方 |
| performance_ratings | JSON 字段：speed/handling/acceleration/launch/braking/offroad |
| source / notes | 来源和备注 |

**重要：** Setup Snapshot 不是 Tag。PI、Class、Power、Tire Compound 等是车辆的结构化状态字段，不应标记为 tag。它们在 recording 前必须明确记录在 Setup Snapshot 中。

**对应 UI：** Setup Snapshot Edit Dialog（可从 Tune Detail Page 打开编辑）

### 2.5 Run（遥测记录）

表示一次遥测记录。**每个 Run 必须绑定完整上下文。**

**核心字段：**

| 字段 | 说明 |
| --- | --- |
| run_id | 主键 |
| session_id | UDP 会话 ID，也是 raw CSV 的文件名（不含扩展名） |
| car_id / build_id / tune_id / setup_snapshot_id | 四层上下文外键 |
| route_id / route_mode | 路线 / 路线模式（timed_route / free_drive / unset） |
| record_type | 记录类型（lap_recording / free_drive / drag_strip / hard_braking 等） |
| raw_csv_path / processed_csv_path | CSV 文件路径 |
| plot_path / report_path / dataset_path | 派生文件路径 |
| duration_seconds / packet_count | 运行时统计 |
| quality_status | draft / good / warning |
| status / is_active | active / archived |
| notes | 用户备注 |

**Run 关联的子数据：**
- run_tags --- 通过 tag_id 关联 tags 表，带 tag_role（如 "intent"）
- annotations --- 时间区段标注
- recording_sessions --- 记录会话详情

**对应 UI：** Run Library Page --- 左侧筛选栏 + 右侧结果列表

---
## 3. 当前 SQLite 表结构逐表说明

以下按 schema.sql 顺序逐表说明。

### 3.1 schema_version
- **用途：** 追踪 schema 变更（迁移系统）
- **核心字段：** version, name, applied_at_utc
- **当前状态：** version=1，"desktop_0_99_beta_initial_schema"

### 3.2 cars
- **用途：** 车辆本体信息
- **核心字段：** car_id(PK), display_name, manufacturer, model, year, car_ordinal, car_group, default_car_class, default_pi, default_drivetrain, status, is_active, notes, source
- **外键关系：** 无（根实体）
- **对应 UI：** Car Detail Page, Cars Page
- **后续填充：** 用户录入车辆时填写 display_name/manufacturer/model/car_ordinal 等

### 3.3 builds
- **用途：** 改装版本/硬件组合
- **核心字段：** build_id(PK), car_id(FK->cars), display_name, build_key, status, is_active, notes, source
- **外键关系：** car_id -> cars
- **唯一约束：** (car_id, build_key)
- **对应 UI：** Build Detail Page
- **后续填充：** 用户创建新 Build 时填写 display_name/build_key

### 3.4 build_snapshots
- **用途：** Build 的性能快照（记录某次 Build 的 PI/Class/Power 等）
- **核心字段：** build_snapshot_id(PK), build_id(FK->builds), pi, car_class, drivetrain, power, torque, weight, tire_compound, upgrade_summary, notes
- **外键关系：** build_id -> builds
- **对应 UI：** Build Detail Page 的 "Build Snapshot" 区域
- **后续填充：** 用户确认 Build 状态时录入

### 3.5 upgrade_categories
- **用途：** 改装类别定义（发动机、进气、排气、涡轮、轮胎等）
- **核心字段：** upgrade_category_id(PK), category_key(UNIQUE), label_zh, label_en, display_order, description, is_active
- **外键关系：** 无（字典表）
- **对应 UI：** 暂无专用 UI；Build Detail Page 的 "Upgrade Selections" 区域展示关联数据
- **后续填充：** *** 重要 --- 改装类别应填入此表（见第 9 章）

### 3.6 upgrade_options
- **用途：** 每个改装类别下的具体选项
- **核心字段：** upgrade_option_id(PK), upgrade_category_id(FK->upgrade_categories), option_key, label_zh, label_en, is_stock, pi_impact, weight_impact, cost_credits, notes, is_active
- **外键关系：** upgrade_category_id -> upgrade_categories
- **唯一约束：** (upgrade_category_id, option_key)
- **后续填充：** *** 重要 --- 每个改装选项应填入此表

### 3.7 build_upgrade_selections
- **用途：** 一个 Build 在各改装类别中选择了哪个选项（多对多关联）
- **核心字段：** (build_id, upgrade_category_id) 复合主键, upgrade_option_id(FK->upgrade_options), notes
- **外键关系：** build_id -> builds, upgrade_category_id -> upgrade_categories, upgrade_option_id -> upgrade_options
- **对应 UI：** Build Detail Page 的 "Upgrade Selections" 区域
- **后续填充：** 用户为 Build 选择改装件时写入

### 3.8 upgrade_compatibility_rules
- **用途：** 改装兼容性规则（如某些选项互斥、需要前置升级等）
- **核心字段：** upgrade_rule_id(PK), rule_type, source_option_id, target_option_id, payload_json, notes, is_active
- **外键关系：** 逻辑关联 upgrade_options（无强制外键）
- **后续填充：** 可在填充改装选项后逐步添加规则

### 3.9 tunes
- **用途：** 调校版本
- **核心字段：** tune_id(PK), build_id(FK->builds), display_name, tune_key, version, status, is_active, notes, source
- **外键关系：** build_id -> builds
- **唯一约束：** (build_id, tune_key, version)
- **对应 UI：** Tune Detail Page
- **后续填充：** 用户创建新 Tune 时填写

### 3.10 tune_parameter_definitions
- **用途：** 调校参数定义（每个参数叫什么、范围是多少）
- **核心字段：** tune_parameter_id(PK), parameter_key(UNIQUE), category, label_zh, label_en, unit, min_value, max_value, step, value_type, description, is_enabled, display_order
- **外键关系：** 无（字典表）
- **对应 UI：** Tune Parameter Editor（在 Tune Detail Page 中）
- **后续填充：** *** 重要 --- 所有 FH6 调校参数应填入此表（见第 9 章）

### 3.11 tune_parameter_values
- **用途：** 某个 Tune 的具体参数值
- **核心字段：** (tune_id, tune_parameter_id) 复合主键, value_text, value_real, notes
- **外键关系：** tune_id -> tunes, tune_parameter_id -> tune_parameter_definitions
- **对应 UI：** Tune Parameter Editor 的每个滑动条/输入框
- **后续填充：** 用户为 Tune 设置参数值时写入（通过 Tune Parameter Editor）

### 3.12 setup_snapshots
- **用途：** Recording 前的车辆最终状态快照
- **核心字段：** setup_snapshot_id(PK), car_id(FK), build_id(FK), tune_id(FK), snapshot_name, pi, car_class, drivetrain, power, torque, weight, front_weight_percent, tire_compound, performance_ratings(JSON), source, notes, is_active
- **外键关系：** car_id -> cars, build_id -> builds, tune_id -> tunes
- **索引：** (car_id, build_id, tune_id) 复合索引
- **对应 UI：** Setup Snapshot Edit Dialog
- **后续填充：** *** 重要 --- Recording 前用户确认的车辆性能状态填入此表

### 3.13 routes
- **用途：** 路线定义
- **核心字段：** route_id(PK), route_key, display_name, route_mode, surface_type, route_type, source, notes, is_active
- **对应 UI：** Run Library 筛选 "路线模式"
- **后续填充：** 用户定义路线时填写

### 3.14 runs
- **用途：** 遥测记录（核心实体）
- **核心字段：** run_id(PK), session_id, car_id(FK), build_id(FK), tune_id(FK), setup_snapshot_id(FK), route_id(FK), route_mode, record_type, use_case, raw_csv_path, 各种派生路径, duration_seconds, packet_count, quality_status, quality_warnings, metrics_json, notes, status, is_active
- **外键关系：** 4 个上下文外键 + route_id -> routes
- **索引：** (car_id, build_id, tune_id, setup_snapshot_id), (route_id, route_mode), (status, is_active)
- **对应 UI：** Run Library Page, Run Card
- **约束：** 创建 Run 时需要 car_id, build_id, tune_id, setup_snapshot_id, route_mode, record_type, 且至少一个 intent tag

### 3.15 tags
- **用途：** 标签字典（所有 tag 的统一定义）
- **核心字段：** tag_id(PK), tag_key, category, label_zh, label_en, description, is_system, is_active, display_order
- **tag_id 格式：** {category}__{tag_key}，如 intent_tag__baseline
- **内置 categories：** intent_tag, behavior_tag, dataset_purpose, general_tag, run_state_tag, quality_status, data_status
- **对应 UI：** Tag Library Page

### 3.16 run_tags
- **用途：** Run 和 Tag 的多对多关联
- **核心字段：** (run_id, tag_id) 复合主键, tag_role（如 "intent"）, created_at_utc
- **外键关系：** run_id -> runs, tag_id -> tags
- **索引：** idx_run_tags_tag_id
- **对应 UI：** Run Library 中 Run Card 显示 tag chips

### 3.17 annotations
- **用途：** 遥测时间区段标注
- **核心字段：** annotation_id(PK), target_type, target_id, run_id(FK), start_time, end_time, source, confidence, note, payload_json, is_active
- **对应用途：** 标记某段时间发生了推头、甩尾、暂停等

### 3.18 annotation_tags
- **用途：** Annotation 和 Tag 的多对多关联
- **核心字段：** (annotation_id, tag_id) 复合主键

### 3.19 dataset_groups / dataset_group_runs
- **用途：** 将多个 Run 组织为数据集组
- **dataset_groups 核心字段：** dataset_group_id(PK), car_id(FK), display_name, purpose, route_id(FK)
- **dataset_group_runs 核心字段：** (dataset_group_id, run_id) 复合主键
- **后续用途：** 将相关 Run 归为一组用于分析或训练

### 3.20 experiment_matrices / experiment_variables / experiment_tasks
- **用途：** 实验矩阵（占位，见第 9.5 章）
- **experiment_matrices 核心字段：** experiment_matrix_id(PK), car_id(FK), display_name, purpose, status(draft/active/completed), payload_json
- **experiment_variables 核心字段：** experiment_variable_id(PK), experiment_matrix_id(FK), variable_type, variable_key, payload_json
- **experiment_tasks 核心字段：** experiment_task_id(PK), experiment_matrix_id(FK), build_id(FK), tune_id(FK), setup_snapshot_id(FK), route_id(FK), record_type, required_run_count, completed_run_count, status

### 3.21 recording_sessions
- **用途：** 记录会话详情
- **核心字段：** recording_session_id(PK), run_id(FK), car_id(FK), build_id(FK), tune_id(FK), setup_snapshot_id(FK), route_id(FK), route_mode, record_type, status, started_at_utc, stopped_at_utc, packet_count, metadata_json, error_message
- **重要约束：** (setup_snapshot_id, car_id, build_id, tune_id) 四列外键引用 setup_snapshots 的对应四列

---

## 4. Repository Layer 说明

当前共有 9 个 Repository 类，全部通过 db/repositories/__init__.py 导出：

| Repository | 文件 | 主要方法 |
| --- | --- | --- |
| **CarRepository** | car_repository.py | list_cars(), get_car(), create_car(), update_car(), archive_car() |
| **BuildRepository** | build_repository.py | list_by_car(), get_build(), latest_build_snapshot(), list_upgrade_selections(), create_build(), ensure_default_stock_build(), update_build(), archive_build() |
| **TuneRepository** | tune_repository.py | list_by_build(), get_tune(), create_tune(), ensure_baseline_tune(), update_tune(), archive_tune() |
| **TuneParameterRepository** | tune_parameter_repository.py | list_definitions(), list_values(), save_values() |
| **SetupSnapshotRepository** | setup_snapshot_repository.py | get_snapshot(), list_by_tune(), validate_context(), create_snapshot(), update_snapshot(), ensure_default_setup_snapshot() |
| **RunRepository** | run_repository.py | get_run(), create_run(), update_run_notes(), archive_run(), add_tag_to_run(), remove_tag_from_run(), query_run_records() |
| **TagRepository** | tag_repository.py | list_by_category(), get_tag(), tag_id_for_key(), create_tag(), update_tag(), archive_tag() |
| **RouteRepository** | route_repository.py | list_routes(), get_route(), create_route() |
| **ExperimentRepository** | experiment_repository.py | list_matrices(), create_placeholder_matrix() |

### 关键设计模式

- **所有写操作通过 transaction() 包装** --- 自动 COMMIT 或 ROLLBACK
- **ensure_default_*() 方法** --- Build/Tune/Setup Snapshot 各有一个 "默认" 创建方法，确保初次使用时上下文不为空
- **validate_context()** --- SetupSnapshotRepository 通过 JOIN 验证四层上下文的一致性
- **query_run_records()** --- RunRepository 的核心查询方法，支持多字段筛选 + tag_id 筛选 + keyword 搜索，一次查询返回含 tag 信息的完整 record dict
- **utils.py 工具函数** --- utc_now(), clean_key()（sanitize）, require_text(), active_flag()

---

## 5. UI 页面/模块说明

### 5.1 MainWindow 导航结构

```
+--------------+-------------------------------------------+
|  Sidebar     |  Content Area (QStackedWidget)             |
|              |                                           |
|  首页        |  0: DashboardPage                         |
|  车辆库      |  1: CarsPage                              |
|  数据总库    |  2: CarDetailPage                          |
|  标签库      |  3: BuildDetailPage                        |
|  设置        |  4: TuneDetailPage                         |
|              |  5: RecordRunPage                          |
|  v0.99.1     |  6: RunLibraryPage                         |
|              |  7: TagLibraryPage                         |
|              |  8: SettingsPage                           |
+--------------+-------------------------------------------+
```

**导航规则：** 点击 Sidebar 按钮切换顶层页面。Car Detail / Build Detail / Tune Detail / Record Run 是上下文相关页面，进入时显示顶部返回栏。

### 5.2 各页面说明

| 页面 | 组件 | 数据来源 | 主要功能 |
| --- | --- | --- | --- |
| **DashboardPage** | MetricCard, CarCard 预览, Run 列表 | dashboard_stats() | 首页概览：车辆数、记录数、最近 Run |
| **CarsPage** | CarCard 列表 | list_cars() | 显示所有车辆卡片，点击进入 Car Detail |
| **CarDetailPage** | MetricCard, BuildCard 列表, Run 列表 | get_car() | 车辆详情：PI/Class/Drivetrain/Builds/Runs |
| **BuildDetailPage** | Build Snapshot, Upgrade Selections 占位, Tune 列表, Run 列表 | get_build_detail() | Build 详情：快照、改装件、Tunes、Runs |
| **TuneDetailPage** | TuneParameterEditor, Setup Snapshot 列表, Run 列表 | get_tune_detail() | Tune 详情：参数编辑、快照、Runs |
| **RecordRunPage** | 5 步 Wizard | 用户选择 + RecordingContextService.validate() | Recording 前上下文准备 |
| **RunLibraryPage** | 左侧筛选面板 + 右侧结果列表 | list_run_records() | Run 的搜索/筛选/编辑/标签管理 |
| **TagLibraryPage** | TagChip 按类别分组 | list_tags_by_category() | 标签可视化管理/创建 |
| **SettingsPage** | 静态信息 | - | 版本/环境信息 |

### 5.3 Dialogs

| Dialog | 用途 |
| --- | --- |
| **CarEditDialog** | 编辑车辆属性（display_name、manufacturer 等） |
| **SetupSnapshotEditDialog** | 编辑/确认 Setup Snapshot 所有字段 |
| **TuneParameterEditor** | (嵌入 TuneDetailPage) 编辑 Tune 参数 |
| **TagEditDialog** | 创建/编辑标签 |

### 5.4 Widgets

| Widget | 用途 |
| --- | --- |
| **CarCard** | 车辆卡片（显示名称、PI、统计、操作按钮） |
| **MetricCard** | 统计数字卡片 |
| **SectionHeader** | 段落标题 + 副标题 |
| **TagChip** | 标签芯片（显示 label_zh / category color） |

---

## 6. Record Run Wizard 当前逻辑

5 步 Wizard，每步使用 QStackedWidget 内部切换：

### Step 1: Select Build
- **需要数据：** 当前 Car 下的所有 Build 列表（含 "默认原厂" build）
- **校验：** 至少选择一个 Build -> 设置 build_id
- **UI 元素：** QComboBox 列出 Build

### Step 2: Select/Edit Tune
- **需要数据：** 所选 Build 下的所有 Tune 列表（含 baseline_tune）
- **校验：** 至少选择一个 Tune -> 设置 tune_id
- **UI 元素：** QComboBox 列出 Tune

### Step 3: Confirm/Edit Setup Snapshot
- **需要数据：** 所选 Tune 下的 Setup Snapshot 列表
- **校验：** 至少选择一个 Setup Snapshot（或确认默认快照）
- **UI 元素：** QComboBox 列出快照 + "编辑快照"按钮打开 SetupSnapshotEditDialog

### Step 4: Route / Record Type / Intent Tags
- **需要数据：**
  - Route Mode: timed_route / free_drive / unset
  - Record Type: lap_recording / free_drive / drag_strip / hard_braking 等
  - Intent Tags: 用户从已有 intent_tag 中选择至少一个（chip 多选 UI）
- **校验：** route_mode 非空、record_type 非空、至少一个 intent tag
- **UI 元素：** QComboBox + chip 多选按钮

### Step 5: Ready / Start Recording
- **触发 Start 条件：** RecordingContextService.validate() 返回 is_valid=true
- **校验内容：**
  - car_id, build_id, tune_id, setup_snapshot_id 都存在
  - route_mode, record_type 非空
  - 至少一个 intent tag 存在
  - 四层上下文通过 validate_context() 一致性检查
- **Start Recording 做什么：** 创建 QThread + RecordingWorker -> UDP 监听 -> 接收 packet -> 写入 raw CSV -> Stop 后通过 create_run_from_recording() 保存 SQLite run
- **最终 Run 绑定：** car_id, build_id, tune_id, setup_snapshot_id 全部写入 runs 表

### 缺少上下文时的提示
- 如果未选择 Car 就进入 RecordRunPage：显示 "请从车辆库进入记录页面。"
- 如果某步没有可选项：系统提供 ensure_default_*() 自动创建默认上下文
- 如果 Start 时上下文不完整：_update_step_state() 会禁用 Start 按钮

---
## 7. Run Library 当前逻辑

### 筛选字段

| 筛选项 | 筛选字段 | 数据来源 |
| --- | --- | --- |
| 车辆 (Car) | r.car_id | cars 表 |
| Build | r.build_id | builds 表 |
| Tune | r.tune_id | tunes 表 |
| Snapshot | r.setup_snapshot_id | setup_snapshots 表 |
| 路线模式 | r.route_mode | timed_route / free_drive / unset |
| 记录类型 | r.record_type | lap_recording / free_drive 等 |
| 质量 | r.quality_status | good / warning / draft / unknown |
| 标签 | rt.tag_id（EXISTS 子查询） | run_tags 表 |
| 关键词 | search_text（内存过滤） | display_title、session_id、car_name、build_name、tag_keys、tag_labels、notes |
| 归档 | r.is_active | 是否包含 archived |

### 级联筛选
- Car -> Build -> Tune：选择 Car 后动态加载该 Car 的 Build 列表；选择 Build 后动态加载该 Build 的 Tune 列表
- 其他筛选项独立更新结果

### Tag 筛选
- **使用 tag_id** 而非 tag_key：通过 EXISTS (SELECT 1 FROM run_tags rt WHERE rt.run_id = r.run_id AND rt.tag_id = ?)
- Tag 下拉列表显示 label_zh (tag_id) 格式

### Run Card 显示信息
- **display_title**：{car_name} - {route_name} - {record_type_label}
- **subtitle**：session: {session_id} | {duration}s | {quality_status}
- **标签 chips**：显示 label_zh（中文标签），颜色按 category 区分
- **操作按钮**：编辑备注、添加标签、移除标签、归档

### 关键词搜索
- 构建 search_text 包含：display_title、session_id、car_name、build_name、tune_name、setup_snapshot_name、route_name、tag_keys、tag_labels、notes
- 大小写不敏感匹配
- 在 SQL 筛选结果上再进行内存过滤（因为 search_text 是组装字段）

---

## 8. Tag Library 当前逻辑

### Tag 系统架构

```
tags 表（字典）
  +-- tag_id = {category}__{tag_key}
  +-- tag_key（内部英文 key）
  +-- label_zh（用户可见中文标签）
  +-- category（分组）
  +-- is_system（系统内置 vs 用户创建）
  +-- is_active（可禁用不删除）

run_tags 表（关联）
  +-- run_id -> runs
  +-- tag_id -> tags
  +-- tag_role（如 "intent"）
```

### Tag 类别（category）

| Category | 用途 | 示例 |
| --- | --- | --- |
| intent_tag | Recording 时必须选择至少一个 | baseline（基准）、repeat_test（重刻测试）、intentional_understeer（故意推头） |
| behavior_tag | 车辆行为描述 | 推头、甩尾、打滑、暂停 |
| general_tag | 通用标签 | needs_review、favorite |
| run_state_tag | Run 状态 | has_pause、crashed、invalid |
| quality_status | 数据质量 | good、warning、partial |
| data_status | 数据处理状态 | raw_only、processed、published |
| dataset_purpose | 数据集用途 | baseline、model_training、handling_evaluation |

### 用户创建 Tag
- **写入 tags 表**（不写 run_tags）
- tag_id 自动生成为 {category}__{tag_key}
- 创建后出现在 Tag Library 对应分类下

### Run 添加 Tag
- **写入 run_tags 表**：INSERT INTO run_tags (run_id, tag_id, tag_role, ...)
- 不影响 tags 表

### UI 显示
- Tag Library：按 category 分组，每行最多 8 个 TagChip
- Run Card：显示 label_zh（中文标签），使用 tag 的 category 对应颜色
- 筛选下拉：显示 label_zh (tag_id)

---

## 9. 后续真实参数填充指南

当你后续从游戏界面截屏/文字给我时，以下是归类方法。

### 9.1 改装件菜单 -> 应进入 upgrade_categories + upgrade_options + build_upgrade_selections

游戏中的改装件如发动机、进气、排气、涡轮/机械增压、轮胎、轮毂、变速箱、差速器、悬挂、防倾杆、刹车、空力、车重、转换等：

#### upgrade_categories 填法

| category_key | label_zh | display_order |
| --- | --- | --- |
| engine | 发动机 | 10 |
| intake | 进气 | 20 |
| exhaust | 排气 | 30 |
| forced_induction | 涡轮/机械增压 | 40 |
| tires | 轮胎 | 50 |
| wheels | 轮毂 | 60 |
| transmission | 变速箱 | 70 |
| differential | 差速器 | 80 |
| suspension | 悬挂 | 90 |
| antiroll_bars | 防倾杆 | 100 |
| brakes | 刹车 | 110 |
| aero | 空力 | 120 |
| weight_reduction | 车重 | 130 |
| conversion | 转换（引擎置换/驱动转换） | 140 |

**字段设计：**
- category_key：内部英文 key，稳定不变
- label_zh：中文标签，如 "涡轮/机械增压"
- label_en：英文标签
- display_order：控制显示顺序

#### upgrade_options 填法

每个改装类别下的具体选项，如轮胎类别有：

| upgrade_category_id | option_key | label_zh | is_stock | pi_impact | weight_impact |
| --- | --- | --- | --- | --- | --- |
| (tires_id) | stock_tires | 原厂轮胎 | 1 | 0 | 0 |
| (tires_id) | street_tires | 街胎 | 0 | +5 | -2 |
| (tires_id) | sport_tires | 运动胎 | 0 | +10 | -3 |
| (tires_id) | semi_slick | 半热熔 | 0 | +15 | -4 |
| (tires_id) | slick | 全热熔 | 0 | +20 | -5 |

**字段设计：**
- option_key：内部英文 key
- label_zh：中文标签
- is_stock：是否原厂（1=是）
- pi_impact：对 PI 的影响值
- weight_impact：对车重的影响值
- cost_credits：CR 花费

#### build_upgrade_selections 填法

当用户为 Build "Stage 2 AWD" 选择悬挂为 "拉力悬挂" 时：

```
build_id = "build_amg_stage2"
upgrade_category_id = (suspension 的 ID)
upgrade_option_id = (rally_suspension 的 ID)
```

#### upgrade_compatibility_rules（可选）

如 "选择 AWD 转换后不能再选 RWD 差速器" 等互斥规则，用 payload_json 存储规则详情。

---

### 9.2 调校参数菜单 -> 应进入 tune_parameter_definitions + tune_parameter_values

游戏中的调校参数如胎压、齿比、定位、防倾杆、弹簧、车高、阻尼、空力、刹车、差速器等：

#### tune_parameter_definitions 填法

| parameter_key | category | label_zh | unit | min_value | max_value | step | value_type |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tire_pressure_front | tires | 前轮胎压 | PSI | 15.0 | 55.0 | 0.1 | float |
| tire_pressure_rear | tires | 后轮胎压 | PSI | 15.0 | 55.0 | 0.1 | float |
| final_drive_ratio | gearing | 终传比 | - | 2.0 | 6.0 | 0.01 | float |
| front_camber | alignment | 前轮外倾角 | deg | -5.0 | 1.0 | 0.1 | float |
| rear_camber | alignment | 后轮外倾角 | deg | -5.0 | 1.0 | 0.1 | float |
| front_toe | alignment | 前束角 | deg | -2.0 | 2.0 | 0.1 | float |
| rear_toe | alignment | 后束角 | deg | -2.0 | 2.0 | 0.1 | float |
| front_antiroll_bar | suspension | 前防倾杆 | N/mm | 1.0 | 65.0 | 0.1 | float |
| rear_antiroll_bar | suspension | 后防倾杆 | N/mm | 1.0 | 65.0 | 0.1 | float |
| front_spring_rate | suspension | 前弹簧刚度 | kgf/mm | 1.0 | 200.0 | 0.1 | float |
| rear_spring_rate | suspension | 后弹簧刚度 | kgf/mm | 1.0 | 200.0 | 0.1 | float |
| ride_height_front | suspension | 前车高 | cm | 5.0 | 30.0 | 0.1 | float |
| ride_height_rear | suspension | 后车高 | cm | 5.0 | 30.0 | 0.1 | float |
| front_rebound | damping | 前回弹阻尼 | N-s/m | 1.0 | 20.0 | 0.1 | float |
| rear_rebound | damping | 后回弹阻尼 | N-s/m | 1.0 | 20.0 | 0.1 | float |
| front_bump | damping | 前压缩阻尼 | N-s/m | 1.0 | 20.0 | 0.1 | float |
| rear_bump | damping | 后压缩阻尼 | N-s/m | 1.0 | 20.0 | 0.1 | float |
| front_downforce | aero | 前下压力 | kgf | 10.0 | 200.0 | 0.1 | float |
| rear_downforce | aero | 后下压力 | kgf | 10.0 | 200.0 | 0.1 | float |
| brake_pressure | brakes | 刹车压力 | % | 50.0 | 150.0 | 1.0 | float |
| brake_bias | brakes | 前后刹车比 | % front | 30.0 | 70.0 | 1.0 | float |
| diff_accel | differential | 差速器加速锁止率 | % | 0.0 | 100.0 | 1.0 | float |
| diff_decel | differential | 差速器减速锁止率 | % | 0.0 | 100.0 | 1.0 | float |

**每个参数需要记录：**

- parameter_key：内部英文 key，稳定不变
- label_zh：中文标签
- category：分组（tires / gearing / alignment / suspension / damping / aero / brakes / differential）
- unit：单位（PSI / deg / N/mm / kgf/mm / % 等）
- min_value / max_value：滑块范围
- step：步进值
- value_type：float / int / enum
- display_order：显示顺序
- is_enabled：是否启用（可从 1 开始，后续按需禁用）

#### tune_parameter_values 填法

当用户在 Tune "high_speed_stability v01" 中设置前胎压 32.5 PSI：

```
tune_id = "tune_amg_stock_stable"
tune_parameter_id = (tire_pressure_front 的 ID)
value_real = 32.5
value_text = "32.5"
```

这些写入通过 TuneParameterRepository.save_values() 的 UPSERT 逻辑完成。

---

### 9.3 车辆性能总览 -> 应进入 setup_snapshots

游戏界面中车辆的性能数据如 PI、Class、Drivetrain、Power (hp)、Torque (Nm)、Weight (kg)、Front Weight %、Speed/Handling/Acceleration/Launch/Braking/Offroad 评分：

**全部进入 setup_snapshots 表：**

| 游戏数据 | setup_snapshots 字段 |
| --- | --- |
| PI | pi (INTEGER) |
| Class（S1/A/B 等） | car_class (TEXT) |
| Drivetrain（RWD/AWD/FWD） | drivetrain (TEXT) |
| Power (hp) | power (REAL) |
| Torque (Nm) | torque (REAL) |
| Weight (kg) | weight (REAL) |
| Front Weight % | front_weight_percent (REAL) |
| Tire Compound | tire_compound (TEXT) |
| Speed 评分 (1-10) | performance_ratings JSON -> speed |
| Handling 评分 | performance_ratings JSON -> handling |
| Acceleration 评分 | performance_ratings JSON -> acceleration |
| Launch 评分 | performance_ratings JSON -> launch |
| Braking 评分 | performance_ratings JSON -> braking |
| Offroad 评分 | performance_ratings JSON -> offroad |

**performance_ratings JSON 格式：**
```json
{
  "speed": 8.0,
  "handling": 7.5,
  "acceleration": 8.2,
  "launch": 7.1,
  "braking": 7.4,
  "offroad": 3.0
}
```

**为什么是 Setup Snapshot 而不是 Tag：**
- PI、Power、Weight 等是车辆的结构化状态数值，会随 Build/Tune 变化而变化
- Setup Snapshot 的设计目的就是记录 Recording 前的最终车辆状态
- 将它们存为 tag 会丢失数值精度、无法进行量化比较

---

### 9.4 哪些应该是 Tag

#### 应该标记为 Tag 的事物（定性/行为/意图）

| 示例 | 应进入 | Category |
| --- | --- | --- |
| 基准测试 | tags -> run_tags | intent_tag |
| 重刻测试 | tags -> run_tags | intent_tag |
| 完整跑圈 | (record_type 字段) + 可选 tag | intent_tag |
| 自由驾驶 | (record_type 字段) + 可选 tag | intent_tag |
| 故意推头 | tags -> run_tags | intent_tag / behavior_tag |
| 故意甩尾 | tags -> run_tags | intent_tag / behavior_tag |
| 出弯打滑 | tags -> run_tags | behavior_tag |
| 有暂停 | tags -> run_tags | run_state_tag |
| 赛道测量 | tags -> run_tags | intent_tag |
| 低速弯 / 高速弯 | (record_type 字段) + 可选 tag | intent_tag |
| 路肩/颠簸 | tags -> run_tags | intent_tag |

#### 不应只标记为 Tag 的事物（结构化/数值型）

| 示例 | 应进入 | 原因 |
| --- | --- | --- |
| 发动机类型（V8/V12/电动） | cars 或 upgrade_categories | 车辆本体或改装属性 |
| 轮胎宽度 | upgrade_options | 改装选项数值 |
| 齿比数值 | tune_parameter_values | 调校参数数值 |
| 弹簧刚度 | tune_parameter_values | 调校参数数值 |
| 车重 | setup_snapshots.weight | 结构化数值字段 |
| 马力 | setup_snapshots.power | 结构化数值字段 |
| PI | setup_snapshots.pi | 结构化数值字段 |

**判断原则：** 如果是一个精确的数值，属于结构化字段或参数值；如果是一个定性的描述/意图/行为标记，属于 Tag。

---

### 9.5 未来 Experiment Matrix 用法

Experiment Matrix 表结构已预留，用于系统化对比测试：

```
experiment_matrices       <- 一组测试的名称和目的
  +-- experiment_variables  <- 测试变量（如 "轮胎类型", "轮胎胎压"）
  +-- experiment_tasks      <- 具体测试任务
      +-- build_id          <- 用哪个 Build
      +-- tune_id           <- 用哪个 Tune
      +-- setup_snapshot_id <- 确认的快照
      +-- route_id          <- 在哪条路线跑
      +-- required_run_count <- 需要跑几次
      +-- completed_run_count <- 已完成几次
```

**使用场景示例：**

```
测试矩阵: "AMG GT 轮胎对比测试"
  car_id: car_demo_amg
  变量: 轮胎类型 (upgrade_options 中的 tire 选项)
  任务:
    +-- Stock Tires  -> 在地平线高速公路跑 3 圈 (completed: 0/3)
    +-- Sport Tires  -> 在地平线高速公路跑 3 圈 (completed: 0/3)
    +-- Semi-Slick   -> 在地平线高速公路跑 3 圈 (completed: 0/3)
```

当前状态：表结构已就绪，ExperimentRepository.create_placeholder_matrix() 可创建占位矩阵。UI 尚未实现实验矩阵页面。

---

## 10. 架构数据流图

```
                   +-------------+
                   |  FH6 Game   |
                   |  Data Out   |
                   +------+------+
                          | UDP :9999
                          v
                 +-----------------+
                 |  RecordingWorker | (QThread)
                 |  packet_parser   |
                 |  TelemetryCsvLogger |
                 +--------+--------+
                          | raw CSV
                          v
                   +-------------+
                   | data/raw/   |
                   | {sid}.csv   |
                   +-------------+
                          |
             +------------+------------+
             v            v            v
       feature_eng   plot_timeseries  report_generator
             |            |            |
             v            v            v
      data/processed/  reports/      reports/

  +----------------------------------------------+
  |               SQLite (data/fh6_tuning_sim.db) |
  |                                              |
  |  cars -> builds -> tunes -> setup_snapshots     |
  |                          |                   |
  |                          v                   |
  |             runs <- routes                    |
  |              |                               |
  |         run_tags -> tags                      |
  |              |                               |
  |         annotations                          |
  |                                              |
  |  upgrade_categories <-> upgrade_options        |
  |  build_upgrade_selections                    |
  |  tune_parameter_definitions                   |
  |  tune_parameter_values                       |
  |  experiment_matrices / variables / tasks     |
  +--------------------+-------------------------+
                       | Repository Layer
                       v
             +------------------+
             | DesktopDataService |
             +--------+---------+
                      |
                      v
             +------------------+
             |  PySide6 Desktop  |
             |  (MainWindow +    |
             |   9 Pages +       |
             |   Dialogs +       |
             |   Widgets)        |
             +------------------+
```

---

## 11. 菜单导航图

```
MainWindow Sidebar
+-- 首页 (Dashboard)
|   +-- 点击车辆 -> Car Detail
|
+-- 车辆库 (Cars Page)
|   +-- 点击车辆 -> Car Detail
|   |   +-- Build Cards（点击进入 Build）
|   |   |   +-- Build Detail
|   |   |       +-- Upgrade Selections
|   |   |       +-- Tune Cards（点击进入 Tune）
|   |   |       |   +-- Tune Detail
|   |   |       |       +-- Tune Parameter Editor
|   |   |       |       +-- Setup Snapshots（可编辑）
|   |   |       +-- Runs
|   |   +-- "开始新记录" -> Record Run Wizard
|   |   +-- Recent Runs
|   +-- 编辑车辆按钮
|
+-- 数据总库 (Run Library)
|   +-- 左侧筛选面板
|   |   +-- Car / Build / Tune / Snapshot 级联
|   |   +-- Route Mode / Record Type / Quality
|   |   +-- Tag 筛选
|   |   +-- 关键词搜索
|   |   +-- 归档开关
|   +-- 右侧 Run 列表
|       +-- 每个 Run Card: 编辑备注 / 添加标签 / 移除标签 / 归档
|
+-- 标签库 (Tag Library)
|   +-- 按 Category 分组显示 TagChip
|
+-- 设置 (Settings)
    +-- 版本/环境信息
```

---

## 12. 我接下来发图时你应如何归类

当你在后续 coding run 中给我发送 FH6 游戏界面截图或文字时，请按以下决策树归类：

```
你发的截图/文字是关于：
|
+-- 车辆基础信息（制造商、型号、年份、车序）
|   -> cars 表
|
+-- 改装类别/选项列表（发动机、进气、涡轮、轮胎种类等）
|   +-- 类别名称 -> upgrade_categories
|   +-- 每个选项 -> upgrade_options
|
+-- 某个 Build 选择了哪些改装件
|   -> build_upgrade_selections
|
+-- 调校参数列表（胎压、齿比、弹簧、阻尼等）
|   +-- 参数定义（名称、范围、单位）-> tune_parameter_definitions
|   +-- 某个 Tune 的具体值 -> tune_parameter_values
|
+-- Recording 前车辆状态（PI/Class/Power/Weight/评分）
|   -> setup_snapshots（performance_ratings JSON 字段存评分）
|
+-- 定性标签（基准、推头、甩尾、暂停等）
|   -> tags 表（选择合适 category）
|
+-- 路线信息
|   -> routes 表
|
+-- 实验计划（测轮胎、测差速器、测齿比等）
    -> experiment_matrices / variables / tasks
```

---

## 13. 风险与建议

### 当前架构风险

| 风险 | 级别 | 说明 |
| --- | --- | --- |
| upgrade_categories/options 表为空 | 中 | 表结构就绪但无数据，Build Detail 的 Upgrade Selections 显示占位信息 |
| tune_parameter_definitions 表为空 | 中 | Tune Parameter Editor 显示暂无参数定义的提示，但框架可用 |
| .venv 无法加载 PySide6 | 低 | 已有 .venv312 作为替代环境 |
| Git 不可用 | 低 | 当前环境无 git，无法验证 .gitignore |
| 部分旧页面有 mojibake 标签 | 低 | 新 v0.99.1 页面使用正常中文标签 |
| 无真实 FH6 录制测试 | 中 | 自动化测试通过但未进行真机录制 |

### 后续优先级建议

当你开始发送游戏数据时，建议按以下优先级整理：

1. **调校参数定义（tune_parameter_definitions）** --- 最直接影响 Tune Parameter Editor 可用性
2. **改装类别和选项（upgrade_categories + upgrade_options）** --- 让 Build Detail 的 Upgrade Selections 有内容
3. **Setup Snapshot 性能数据** --- Recording 前状态记录更完整
4. **Tags 扩展** --- 按需补充 behavior_tag / run_state_tag
5. **Experiment Matrix 数据** --- 需要先有 upgrade_options 和 tune 数据后再使用

---

*文档结束。本文仅做架构审阅和解释，不包含代码修改。*
