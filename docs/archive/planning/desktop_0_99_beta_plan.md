# FH6 Tuning Sim Desktop 0.99 beta 正式计划

生成时间：2026-05-31

---

## 1. 版本定位

Desktop 0.99 beta 是 **数据架构定型版**，目标不是继续堆 UI 页面，而是把 FH6 Tuning Sim 从 v0.5 的 JSON 原型存储升级为可长期演进的 SQLite 车辆遥测数据平台。

0.99 beta 的核心交付：

1. SQLite 成为主存储，JSON 仅保留为 import/export/legacy migration。
2. 正式采用 `Car -> Build -> Tune -> Setup Snapshot -> Run` 层级。
3. 所有写入使用 transaction，所有连接启用 foreign keys。
4. Run 不允许孤立存在，必须绑定 `car_id`、`build_id`、`tune_id`、`setup_snapshot_id`。
5. 建立 upgrade parts、tune parameters、routes、tags、datasets、annotations、experiment matrix 的数据库基础。
6. PySide6 Desktop 改为 SQLite repository layer 驱动。
7. RecordingController 可以规划接入，但必须排在 schema、migration、repository、上下文结构之后。

0.99 beta 不做 AI，不做优化器，不做 world model training。

---

## 2. 当前基线

当前 v0.5 已完成：

- PySide6 Desktop 7 页：Dashboard / My Cars / Car Detail / Record Run / Run Library / Tag Library / Settings。
- Run Library 已有 JSON 层筛选和 notes/tag/archive 级 CRUD。
- `RecordingWorker` 已存在，但 Record Run 仍是上下文表单和占位逻辑，没有形成完整 RecordingController -> Run 保存闭环。
- 现有主数据在 JSON：
  - `data/platform/platform_index.json`
  - `data/index/runs_index.json`
  - `data/index/tags.json`
  - `data/index/annotations.json`
  - `configs/dictionaries/*.json`
- 当前数据规模：2 cars，4 runs。
- 既有 CLI 和管线必须保持兼容：
  - UDP listener
  - packet parser
  - raw CSV logger
  - feature engineering
  - plotting
  - reports
  - compare
  - dataset builder

---

## 3. 核心数据关系

正式层级：

```text
Car
└── Build
    └── Tune
        └── Setup Snapshot
            └── Run
```

含义必须固定：

| 层级 | 含义 | 示例 |
|------|------|------|
| Car | 车辆本体 | Mercedes-AMG GT |
| Build | 改装/硬件组合 | Stock PI900 RWD / Stage 2 AWD |
| Tune | 某个 Build 下的调教参数 | baseline_tune / high_speed_stability_v01 |
| Setup Snapshot | Build + Tune 确认后、开始 Run 前的最终 general/performance 状态 | PI、class、power、torque、weight、ratings |
| Run | 某个 Setup Snapshot 下的一次遥测记录 | 20260530_082410_road_test |

约束：

- Build 归属于 Car。
- Tune 归属于 Build。
- Setup Snapshot 同时绑定 Car、Build、Tune。
- Run 同时保存 `car_id`、`build_id`、`tune_id`、`setup_snapshot_id`。
- Run 的 `car_id/build_id/tune_id/setup_snapshot_id` 必须一致，不能指向彼此不匹配的对象。
- 如果用户选择原厂默认，系统自动创建或复用：
  - `default_stock_build`
  - `baseline_tune`
  - `default_setup_snapshot`
- 不能用 `unknown` 作为跳过上下文结构的替代品。

---

## 4. Build Snapshot 与 Setup Snapshot 区分

### Build

Build 是改装/硬件组合。它描述车辆装了什么硬件、哪些升级件、是否 engine swap、轮胎/传动/悬挂/刹车/差速器/空力/减重等组合。

### Build Snapshot

Build Snapshot 是 Build 层信息，用于记录某个 Build 在某个时间点的硬件组合摘要。它不代表某一次 Recording 的最终上下文，也不绑定具体 Run。

典型字段：

```text
build_snapshot_id
build_id
pi
car_class
drivetrain
power
torque
weight
tire_compound
upgrade_summary
source
notes
```

### Tune

Tune 是某个 Build 下的调教参数集合。Tune 不能脱离 Build 存在。

### Setup Snapshot

Setup Snapshot 是 Build + Tune 确认后、开始 Run 前的最终车辆 general/performance 状态。它是 Recording 前上下文的一部分，Run 必须绑定它。

最小字段：

```text
setup_snapshot_id
car_id
build_id
tune_id
pi
car_class
drivetrain
power
torque
weight
front_weight_percent
tire_compound
performance_ratings
source
notes
```

`performance_ratings` 先保存为 JSON 字段：

```json
{
  "speed": null,
  "handling": null,
  "acceleration": null,
  "launch": null,
  "braking": null,
  "offroad": null
}
```

---

## 5. SQLite Schema 设计

数据库路径：

```text
data/fh6_tuning_sim.db
```

建议目录：

```text
fh6_tuning_sim/data_management/db/
  schema.sql
  migrations/
  seed_data/
```

所有 SQLite 连接必须执行：

```sql
PRAGMA foreign_keys = ON;
```

所有写操作必须包在 transaction 中。

### 5.1 Schema Version

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at_utc TEXT NOT NULL
);
```

### 5.2 Cars

```sql
CREATE TABLE cars (
    car_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    year INTEGER,
    car_ordinal INTEGER,
    car_group INTEGER,
    default_car_class TEXT,
    default_pi INTEGER,
    default_drivetrain TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);
```

### 5.3 Builds

```sql
CREATE TABLE builds (
    build_id TEXT PRIMARY KEY,
    car_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    build_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    UNIQUE (car_id, build_key)
);
```

### 5.4 Build Snapshots

```sql
CREATE TABLE build_snapshots (
    build_snapshot_id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    snapshot_name TEXT,
    pi INTEGER,
    car_class TEXT,
    drivetrain TEXT,
    power REAL,
    torque REAL,
    weight REAL,
    tire_compound TEXT,
    upgrade_summary TEXT,        -- JSON
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (build_id) REFERENCES builds(build_id)
);
```

### 5.5 Tunes

```sql
CREATE TABLE tunes (
    tune_id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    tune_key TEXT NOT NULL,
    version TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    UNIQUE (build_id, tune_key, version)
);
```

### 5.6 Setup Snapshots

```sql
CREATE TABLE setup_snapshots (
    setup_snapshot_id TEXT PRIMARY KEY,
    car_id TEXT NOT NULL,
    build_id TEXT NOT NULL,
    tune_id TEXT NOT NULL,
    snapshot_name TEXT,
    pi INTEGER,
    car_class TEXT,
    drivetrain TEXT,
    power REAL,
    torque REAL,
    weight REAL,
    front_weight_percent REAL,
    tire_compound TEXT,
    performance_ratings TEXT,    -- JSON
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    UNIQUE (setup_snapshot_id, car_id, build_id, tune_id)
);
```

Repository 层必须校验：

- `builds.car_id == setup_snapshots.car_id`
- `tunes.build_id == setup_snapshots.build_id`
- Run 写入时的四个 ID 与 setup snapshot 完全一致

### 5.7 Runs

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    car_id TEXT NOT NULL,
    build_id TEXT NOT NULL,
    tune_id TEXT NOT NULL,
    setup_snapshot_id TEXT NOT NULL,
    route_id TEXT,
    route_mode TEXT NOT NULL,
    record_type TEXT NOT NULL,
    use_case TEXT,
    raw_csv_path TEXT,
    processed_csv_path TEXT,
    plot_path TEXT,
    report_path TEXT,
    dataset_path TEXT,
    metadata_path TEXT,
    tune_snapshot_path TEXT,
    duration_seconds REAL,
    packet_count INTEGER,
    estimated_sample_rate REAL,
    quality_status TEXT,
    quality_warnings TEXT,       -- JSON
    metrics_json TEXT,           -- JSON summary from analysis layer
    notes TEXT,
    review_notes TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    FOREIGN KEY (setup_snapshot_id, car_id, build_id, tune_id)
        REFERENCES setup_snapshots(setup_snapshot_id, car_id, build_id, tune_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);
```

`route_mode` 允许值由字典或 DB seed 控制：

```text
timed_route
free_drive
unset
```

Recording 时 `unset` 可以作为显式选择，但仍必须完成 Car/Build/Tune/Setup Snapshot/Record Type/Intent Tags。

### 5.8 Tags

```sql
CREATE TABLE tags (
    tag_id TEXT PRIMARY KEY,
    tag_key TEXT NOT NULL,
    category TEXT NOT NULL,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    description TEXT,
    is_system INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER DEFAULT 0,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    UNIQUE (category, tag_key)
);

CREATE TABLE run_tags (
    run_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    tag_role TEXT NOT NULL DEFAULT 'intent',
    created_at_utc TEXT NOT NULL,
    PRIMARY KEY (run_id, tag_id, tag_role),
    FOREIGN KEY (run_id) REFERENCES runs(run_id),
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
);
```

至少一个 intent tag 的约束由 repository 层在创建 run 前校验。

### 5.9 Routes

```sql
CREATE TABLE routes (
    route_id TEXT PRIMARY KEY,
    route_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    route_mode TEXT NOT NULL,
    surface_type TEXT,
    route_type TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);
```

### 5.10 Datasets

```sql
CREATE TABLE datasets (
    dataset_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    purpose TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE dataset_runs (
    dataset_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    PRIMARY KEY (dataset_id, run_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
```

### 5.11 Annotations

```sql
CREATE TABLE annotations (
    annotation_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    run_id TEXT,
    start_time REAL,
    end_time REAL,
    source TEXT NOT NULL DEFAULT 'manual',
    confidence REAL DEFAULT 1.0,
    note TEXT,
    payload_json TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE annotation_tags (
    annotation_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    PRIMARY KEY (annotation_id, tag_id),
    FOREIGN KEY (annotation_id) REFERENCES annotations(annotation_id),
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
);
```

### 5.12 Upgrade Parts

```sql
CREATE TABLE upgrade_categories (
    upgrade_category_id TEXT PRIMARY KEY,
    category_key TEXT NOT NULL UNIQUE,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    display_order INTEGER DEFAULT 0,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE upgrade_options (
    upgrade_option_id TEXT PRIMARY KEY,
    upgrade_category_id TEXT NOT NULL,
    option_key TEXT NOT NULL,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    is_stock INTEGER NOT NULL DEFAULT 0,
    pi_impact INTEGER,
    weight_impact REAL,
    cost_credits INTEGER,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
    UNIQUE (upgrade_category_id, option_key)
);

CREATE TABLE build_upgrade_selections (
    build_id TEXT NOT NULL,
    upgrade_category_id TEXT NOT NULL,
    upgrade_option_id TEXT,
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY (build_id, upgrade_category_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
    FOREIGN KEY (upgrade_option_id) REFERENCES upgrade_options(upgrade_option_id)
);

CREATE TABLE upgrade_rules (
    upgrade_rule_id TEXT PRIMARY KEY,
    rule_type TEXT NOT NULL,
    source_option_id TEXT,
    target_option_id TEXT,
    payload_json TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

0.99 beta 只要求结构存在，具体 FH6 改件目录可以为空或只 seed 基础 category。

### 5.13 Tune Parameters

```sql
CREATE TABLE tune_parameter_definitions (
    tune_parameter_id TEXT PRIMARY KEY,
    parameter_key TEXT NOT NULL UNIQUE,
    category TEXT,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    unit TEXT,
    min_value REAL,
    max_value REAL,
    step REAL,
    value_type TEXT NOT NULL DEFAULT 'float',
    description TEXT,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER DEFAULT 0
);

CREATE TABLE tune_parameter_values (
    tune_id TEXT NOT NULL,
    tune_parameter_id TEXT NOT NULL,
    value_text TEXT,
    value_real REAL,
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY (tune_id, tune_parameter_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    FOREIGN KEY (tune_parameter_id) REFERENCES tune_parameter_definitions(tune_parameter_id)
);
```

Tune 参数定义可先为空或 seed 最少分类，不把具体参数写死进 UI 字段。

### 5.14 Experiment Matrix Placeholder

```sql
CREATE TABLE experiment_plans (
    experiment_plan_id TEXT PRIMARY KEY,
    car_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    purpose TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    payload_json TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id)
);

CREATE TABLE experiment_tasks (
    experiment_task_id TEXT PRIMARY KEY,
    experiment_plan_id TEXT NOT NULL,
    build_id TEXT,
    tune_id TEXT,
    setup_snapshot_id TEXT,
    route_id TEXT,
    record_type TEXT,
    required_run_count INTEGER NOT NULL DEFAULT 1,
    completed_run_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (experiment_plan_id) REFERENCES experiment_plans(experiment_plan_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    FOREIGN KEY (setup_snapshot_id) REFERENCES setup_snapshots(setup_snapshot_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);
```

0.99 beta 只做 placeholder 数据结构或 placeholder 页面，不做完整组合遍历算法。

---

## 6. JSON -> SQLite Migration 方案

### 6.1 输入数据

Legacy 输入：

```text
data/platform/platform_index.json
data/index/runs_index.json
data/index/tags.json
data/index/annotations.json
configs/dictionaries/*.json
data/sessions/*_meta.json
data/sessions/*_tune.json
```

Raw telemetry 和 processed 文件只作为路径引用，不修改内容：

```text
data/raw/*.csv
data/processed/*_processed.csv
reports/*_report.md
reports/*_timeseries.png
```

### 6.2 迁移原则

1. 一次性、可重复运行、幂等。
2. 迁移前生成 `.bak.{timestamp}`。
3. 不删除 JSON，不删除 raw/processed/report 文件。
4. SQLite 写入全部使用 transaction。
5. 迁移后校验数量和外键。
6. Legacy JSON 继续可作为 export/import 数据源，但新写入进入 SQLite。

### 6.3 备份策略

迁移前：

```text
data/fh6_tuning_sim.db.bak.{timestamp}        -- 如果 DB 已存在
data/platform/platform_index.json.bak.{timestamp}
data/index/runs_index.json.bak.{timestamp}
data/index/tags.json.bak.{timestamp}
data/index/annotations.json.bak.{timestamp}
```

不做 hard delete。

### 6.4 ID 映射策略

| Legacy 来源 | SQLite 目标 | ID 策略 |
|-------------|-------------|---------|
| platform cars | cars | 保留 `car_id` |
| platform tune_versions | tunes | 保留 `tune_id`，缺 build 时挂到 default stock build |
| runs_index runs | runs | `run_id = session_id` 或 `run__{session_id}`，保持唯一 |
| run car_id | cars/builds/tunes/setup_snapshots | 缺失时创建默认上下文 |
| tags.json + dictionaries | tags | `tag_id = {category}__{tag_key}` |
| annotations.json | annotations + annotation_tags | 保留 annotation_id |

### 6.5 Legacy 数据补全规则

对于 v0.5 的 2 cars / 4 runs：

1. 每辆 car 创建或复用一个默认 Build：
   - `build_key = default_stock_build`
   - `display_name = 原厂默认`
2. 每个 legacy tune 创建或复用一个 Tune：
   - `tune_key` 来自 legacy `tune_name` 或 platform `tune_versions.name`
   - 无 tune 时创建 `baseline_tune`
3. 每个 car/build/tune 创建或复用一个 default Setup Snapshot：
   - `setup_snapshot_id = setup__{car_id}__{build_key}__{tune_key}__default`
   - 字段从 run detected fields、platform car fields、tune metadata 中尽量填充
   - 缺失的数值允许 NULL，但上下文对象不能缺失
4. 每个 run 写入：
   - `car_id`
   - `build_id`
   - `tune_id`
   - `setup_snapshot_id`
   - `route_mode`
   - `record_type`
   - file paths
   - quality summary
5. `route_name = unknown` 的 legacy run：
   - `route_mode = unset`
   - 不创建伪造路线，或创建 `route_unset` 作为显式未设置 route placeholder

### 6.6 迁移校验

迁移脚本完成后必须输出：

```text
cars: expected 2, migrated N
builds: migrated N
tunes: migrated N
setup_snapshots: migrated N
runs: expected 4, migrated N
tags: migrated N
annotations: migrated N
foreign_key_check: PASS
orphan_runs: 0
```

必须执行：

```sql
PRAGMA foreign_key_check;
```

### 6.7 迁移报告

生成：

```text
reports/desktop_0_99_beta_migration_report.md
```

包含：

- 输入文件
- 备份文件
- 迁移计数
- ID 映射摘要
- 缺失字段处理
- 外键检查结果
- 已知 legacy 数据限制

---

## 7. Repository Layer 设计

UI 和 CLI 不直接写 SQL。SQLite 访问集中在 repository layer。

建议目录：

```text
fh6_tuning_sim/data_management/db/
  __init__.py
  connection.py
  migrations.py
  transaction.py
  repositories/
    car_repository.py
    build_repository.py
    tune_repository.py
    setup_snapshot_repository.py
    run_repository.py
    tag_repository.py
    route_repository.py
    dataset_repository.py
    annotation_repository.py
    experiment_repository.py
  services/
    migration_service.py
    recording_context_service.py
    desktop_query_service.py
```

### 7.1 Connection

职责：

- 统一 DB 路径 `data/fh6_tuning_sim.db`
- 每次连接启用 `PRAGMA foreign_keys = ON`
- Row factory 返回 dict-like row
- 提供 read-only query helper 和 transaction helper

### 7.2 Migration Runner

职责：

- 创建 DB
- 按顺序应用 migrations
- 维护 `schema_version`
- 重复运行不重复建表/重复 seed
- 失败时 transaction rollback

### 7.3 Repositories

每个 repository 只负责一个 aggregate 或表组。

| Repository | 职责 |
|------------|------|
| CarRepository | list/get/create/update/archive cars |
| BuildRepository | list builds by car, create default_stock_build, archive build |
| TuneRepository | list tunes by build, create baseline_tune, tune parameter values |
| SetupSnapshotRepository | create/list/confirm setup snapshots, validate belongs-to chain |
| RunRepository | create run, update notes, archive, search/filter, attach tags |
| TagRepository | load seed/system/user tags, create/edit/archive user tags |
| RouteRepository | list/create/archive routes, support route_mode |
| DatasetRepository | dataset CRUD, attach/detach runs |
| AnnotationRepository | run/time-range annotations and annotation tags |
| ExperimentRepository | experiment plan/task placeholder |

### 7.4 Desktop Query Service

替代 v0.5 `DesktopDataService` 中直接读 JSON 的职责，向 PySide6 页面提供稳定 API：

```text
list_cars()
get_car(car_id)
list_builds_for_car(car_id)
list_tunes_for_build(build_id)
list_setup_snapshots(tune_id)
list_runs_for_car(car_id)
list_run_records(filters)
list_tags_by_category()
list_routes()
dashboard_stats()
```

### 7.5 Recording Context Service

RecordingController 接入前必须先有此服务。

职责：

- 校验 Car/Build/Tune/Setup Snapshot/Route Mode/Record Type/Intent Tags。
- 原厂默认时自动创建或复用默认 Build/Tune/Setup Snapshot。
- 生成不可变 recording context。
- 禁止生成 orphan run。

---

## 8. PySide6 页面调整计划

原则：

- 不重写整套 UI。
- 不继续堆页面作为 1.0 核心目标。
- 用现有 7 页承载 SQLite 和上下文层级。
- 默认 UI 显示中文 label，内部 key 保持稳定英文。
- 用户可见 label 来自数据库或 dictionaries seed，不在页面硬编码。

### 8.1 Dashboard

改为 SQLite 统计：

- cars count
- builds count
- tunes count
- setup snapshots count
- active runs count
- archived runs count
- recent runs
- context completeness warnings

### 8.2 My Cars

调整为车辆入口：

- 创建/编辑/归档 Car。
- 车辆卡片显示：
  - display_name
  - default class / PI
  - drivetrain
  - build count
  - tune count
  - run count
  - recent run
- 不展示 raw JSON。

### 8.3 Car Detail

以 Car 为中心组织：

```text
Car Header
Builds
Tunes for selected Build
Setup Snapshots for selected Tune
Runs for selected Setup Snapshot
Experiment Matrix placeholder
```

0.99 beta 可使用 compact sections / tabs，避免信息密度过高。

### 8.4 Record Run

Record Run 不再只选择 Car。必须完整选择：

```text
Car
Build
Tune
Setup Snapshot
Route Mode / Route
Record Type
Intent Tags
Notes
```

Start 按钮默认 disabled，直到前置条件全部满足。

### 8.5 Run Library

改为 SQLite 查询：

- 按 Car / Build / Tune / Setup Snapshot / Route / Record Type / Tag / Quality / Keyword 筛选。
- 编辑 notes。
- 添加/移除 tag。
- archive run：`is_active = 0`，不删除 raw 文件。
- 默认隐藏 archived，可切换显示。

### 8.6 Tag Library

改为 SQLite tags：

- 系统标签从 dictionaries seed 或 migrations 导入。
- 用户标签写入 SQLite。
- `is_active = 0` 代替删除。
- 支持 category/group 展示 chips。

### 8.7 Settings

新增 DB 状态：

- DB path
- schema version
- migration status
- last migration report
- foreign key check result
- legacy JSON import/export entry

### 8.8 Experiment Matrix Placeholder

0.99 beta 只放 placeholder，不做完整算法。

位置建议：

- Car Detail 中一个 section：`测试矩阵`
- 或 Settings/Run Library 中仅显示入口 disabled

展示内容：

```text
未来可为某辆车生成 Build/Tune/Route/Tag 测试任务列表。
0.99 beta 仅建立表结构和占位入口。
```

---

## 9. Recording 前置条件

RecordingController 不放在 0.99 beta 的最前面。接入顺序必须是：

```text
SQLite schema
-> migration
-> repository layer
-> Car/Build/Tune/Setup Snapshot UI context
-> Recording context validation
-> RecordingController integration
```

### 9.1 必须满足的条件

开始 Recording 前必须有：

1. 已选择 Car。
2. 已选择 Build。
3. 已选择 Tune。
4. 已确认或创建 Setup Snapshot。
5. 已选择 Route Mode：
   - `timed_route`
   - `free_drive`
   - `unset`
6. 已选择 Record Type。
7. 至少选择一个 intent tag。

### 9.2 禁止行为

- 禁止创建没有 `car_id` 的 run。
- 禁止创建没有 `build_id` 的 run。
- 禁止创建没有 `tune_id` 的 run。
- 禁止创建没有 `setup_snapshot_id` 的 run。
- 禁止用 `unknown` 直接跳过 Build/Tune/Setup Snapshot。
- 禁止 RecordingWorker 直接写 run metadata 绕过 repository。

### 9.3 默认原厂上下文

如果用户选择原厂默认：

```text
Car -> default_stock_build -> baseline_tune -> default_setup_snapshot -> Run
```

这些对象必须真实存在于 SQLite，并通过 transaction 创建或复用。

### 9.4 Recording 完成后的写入

Recording 停止后：

1. 保存 raw CSV 和 session metadata。
2. repository 在 transaction 中创建 run。
3. 写入 run_tags。
4. 不写 derived analysis 或 manual labels 到 raw CSV。
5. 可选触发 feature engineering/report，但不得阻塞 UI。

---

## 10. GitHub / Windows 分发方案

目标用户流程：

```text
git clone
运行 setup_windows.bat
运行 start_desktop.bat
打开 PySide6 Desktop
配置 FH6 Data Out
创建/选择 Car
创建/选择 Build
创建/选择 Tune
确认 Setup Snapshot
选择 Route / Record Type / Tags
开始 Recording
保存 Run
在 Run Library 检索、编辑、标注、归档 Run
```

### 10.1 不应提交

```text
.venv/
.venv2/
.venv312/
__pycache__/
.pytest_cache/
data/raw/*.csv
data/processed/*.csv
data/processed/*.parquet
data/processed/*.npz
*.bak.*
*.log
dist/
build/
*.exe
```

### 10.2 应提交

```text
fh6_tuning_sim/
tests/
configs/
README.md
ARCHITECTURE.md
PROJECT_STATUS.md
NEXT_STEPS.md
AGENTS.md
requirements.txt
setup_windows.bat
start_desktop.bat
schema.sql / migrations / seed_data
sample database 或 seed data
```

### 10.3 setup_windows.bat

0.99 beta 后应：

1. 检查 Python 3.10+。
2. 创建 `.venv`。
3. 安装 `requirements.txt`。
4. 初始化 SQLite DB。
5. 运行 migration 或 seed sample DB。
6. 给出启动提示。

### 10.4 start_desktop.bat

应优先使用 `.venv`，不要固定 `.venv312`：

```text
.venv\Scripts\python.exe -m fh6_tuning_sim.ui_desktop.app
```

### 10.5 README

README 必须写清：

- Windows 10/11 安装步骤。
- FH6 Data Out 配置。
- DB 初始化命令。
- Desktop 启动命令。
- Streamlit 是 legacy/debug。
- 朋友测试的最小流程。

---

## 11. 五个子代理分工

### 子代理 1：SQLite Schema + Migration

职责：

- 设计并实现 `schema.sql`。
- 建立 migrations。
- 建立 `schema_version`。
- 编写 JSON -> SQLite migration。
- 生成 migration report。
- 校验 foreign keys 和 orphan runs。

交付：

```text
data/fh6_tuning_sim.db
schema.sql
migrations/
reports/desktop_0_99_beta_migration_report.md
```

### 子代理 2：Repository Layer

职责：

- 建立 connection / transaction helper。
- 实现 repositories。
- 保证所有 writes in transaction。
- 保证 UI 不直接读写 SQL。
- 为 v0.5 DesktopDataService 提供 SQLite 替代 API。

交付：

```text
fh6_tuning_sim/data_management/db/
tests/test_sqlite_repositories.py
```

### 子代理 3：Car / Build / Tune / Setup Snapshot UI

职责：

- 调整 My Cars 和 Car Detail。
- 建立 Build/Tune/Setup Snapshot 管理和选择流。
- 保持 UI 车辆中心。
- 减少信息密度，不做页面堆叠。

交付：

```text
PySide6 pages using repository service
manual QA checklist
```

### 子代理 4：Run Library / Tags / Routes / Experiment Placeholder

职责：

- Run Library 改 SQLite。
- Tag Library 改 SQLite。
- Routes 基础管理或选择源。
- Dataset/Annotation 基础 repository 对接。
- Experiment Matrix placeholder。

交付：

```text
SQLite-backed Run Library
SQLite-backed Tag Library
Experiment placeholder
```

### 子代理 5：Recording + Distribution + QA

职责：

- 在前四项完成后接入 RecordingController。
- 强制 Recording 前置条件。
- 确保不产生 orphan run。
- 更新 setup/start bat、README、requirements、.gitignore。
- 运行 compileall/tests/manual QA。

交付：

```text
Recording context flow
Windows distribution flow
reports/desktop_0_99_beta_final_report.md
```

---

## 12. 分阶段实现顺序

### Phase 0：只读审计与边界确认

- 复核现有 JSON 数据和 UI service。
- 明确不可修改模块。
- 输出风险清单。

验收：

- 文件存在性清单。
- legacy 数据计数。
- 不写代码或仅写计划/报告。

### Phase 1：SQLite Schema 与 Migration

- 建 schema。
- 建 migrations。
- 建 seed_data。
- 完成 JSON -> SQLite migration。
- 外键检查。

验收：

- `schema_version` 存在。
- 2 cars / 4 runs 迁移成功。
- runs 全部有 `car_id/build_id/tune_id/setup_snapshot_id`。
- `PRAGMA foreign_key_check` PASS。

### Phase 2：Repository Layer

- 实现 connection/transaction。
- 实现核心 repositories。
- 添加 repository tests。

验收：

- 所有写操作 transaction。
- foreign_keys 每连接启用。
- archive 替代 delete。
- repository tests PASS。

### Phase 3：Desktop Service 切换到 SQLite

- 用 SQLite-backed service 替换 JSON direct service。
- 保持页面调用 API 尽量稳定。

验收：

- Dashboard/My Cars/Car Detail/Run Library/Tag Library 从 SQLite 读取。
- JSON 文件不再作为主写入目标。

### Phase 4：Car -> Build -> Tune -> Setup Snapshot UI

- 在 Car Detail 和 Record Run 建立上下文选择。
- 支持 default stock flow。
- 支持 Setup Snapshot 创建/确认。

验收：

- 用户可以创建/选择 Car。
- 用户可以创建/选择 Build。
- 用户可以创建/选择 Tune。
- 用户可以确认 Setup Snapshot。
- Record Run Start 仍可 disabled，直到上下文完整。

### Phase 5：Run Library / Tags / Routes / Dataset / Annotation 基础

- Run Library SQLite CRUD。
- Tags SQLite CRUD。
- Routes 基础选择。
- Dataset/Annotation 基础数据结构可用。
- Experiment Matrix placeholder。

验收：

- Run 可检索、编辑 notes、标注 tag、归档。
- Tag 可新建/禁用。
- Route mode 可保存。
- Experiment placeholder 可见或表结构可验证。

### Phase 6：RecordingController 接入

前置条件：Phase 1-5 通过。

- 接入 QThread + RecordingWorker。
- Recording start 前调用 RecordingContextService。
- Recording stop 后创建 SQLite run。

验收：

- UI 不阻塞。
- 无上下文时不能 start。
- stop 后 run 在 Run Library 可见。
- 新 run 无 orphan。

### Phase 7：Windows 分发与最终 QA

- 更新 setup/start bat。
- 更新 README。
- 清理 GitHub 分发规则。
- 跑 compileall/tests。
- 写最终报告。

验收：

- 朋友按 README 可完成真实测试流程。
- 不需要手动操作 `.venv312`。
- 不提交 raw/processed/bak/log/venv。

---

## 13. 0.99 beta 验收标准

### 数据层

- SQLite 是主存储。
- JSON 仅作为 import/export/legacy。
- `schema_version` 存在。
- 所有 writes 使用 transaction。
- foreign keys 启用且检查通过。
- runs 表不存在 orphan run。
- 每个 run 有：
  - `car_id`
  - `build_id`
  - `tune_id`
  - `setup_snapshot_id`
  - `route_mode`
  - `record_type`
  - 至少一个 intent tag

### UI

- PySide6 Desktop 可启动。
- Dashboard 从 SQLite 读取。
- My Cars 从 SQLite 读取并可创建/编辑/归档。
- Car Detail 能展示 Build/Tune/Setup Snapshot/Run 层级。
- Record Run 在上下文不完整时不能开始。
- Run Library 能检索、编辑、标注、归档 run。
- Tag Library 使用 SQLite tags。
- Experiment Matrix placeholder 存在。

### Migration

- 现有 2 cars / 4 runs 迁移成功。
- 迁移幂等。
- 迁移前有备份。
- 迁移报告存在。

### Recording

- RecordingController 只在上下文层级完成后接入。
- Recording 不生成孤立 run。
- UI 使用 QThread/worker，不阻塞。

### CLI / Legacy

- UDP listener 行为不变。
- packet parser 不变。
- raw telemetry schema 不变。
- feature engineering / plotting / reports / compare / dataset builder 不破坏。
- Streamlit 保留为 legacy/debug prototype。

### Windows 分发

- `setup_windows.bat` 可安装依赖并初始化 DB。
- `start_desktop.bat` 可启动 Desktop。
- README 中有朋友测试流程。
- GitHub 不提交 venv、raw 大文件、processed 大文件、bak、log。

---

## 14. 不做事项

0.99 beta 和 1.0 都不做：

```text
AI training
world model training
reinforcement learning
automatic tune optimizer
full lap simulation
full Route Profile boundary fusion
full scoring/evaluation system
commercial EXE packaging
packet parser rewrite
UDP listener rewrite
raw telemetry schema change
Streamlit deletion
hard-delete user data
```

0.99 beta 额外不做：

```text
完整 FH6 upgrade parts catalog 填充
完整 tune 参数目录填充
Experiment Matrix 组合遍历算法
复杂 route profile 算法
大规模 UI 重写
```

---

## 15. 主要风险与控制

| 风险 | 影响 | 控制 |
|------|------|------|
| Legacy JSON 关系不完整 | 迁移出错误上下文 | 生成 default_stock_build / baseline_tune / default_setup_snapshot，并写迁移报告 |
| Build 和 Setup Snapshot 混淆 | 后续 run 不可比较 | 分表建模，UI 文案明确，repository 校验链路 |
| Recording 过早接入 | 产生 orphan run | Recording 排在 Phase 6，必须经过 RecordingContextService |
| UI 直接写 SQL | 后续维护困难 | 强制 repository/service 层 |
| 标签多源不一致 | 检索和标注失真 | tags 统一进入 SQLite，legacy dictionaries 只作为 seed/import |
| GitHub 提交大文件或备份 | 分发困难 | 更新 .gitignore，保留 sample/seed 而非真实 raw 大文件 |

---

## 16. 1.0 目标衔接

1.0 的核心目标不是继续堆页面，而是让朋友在 Windows 10/11 上完成真实测试闭环：

```text
安装依赖
启动 PySide6 Desktop
创建/选择 Car
创建/选择 Build
创建/选择 Tune
确认 Setup Snapshot
选择 Route / Record Type / Tags
开始 Recording
保存 Run
在 Run Library 中检索、编辑、标注、归档 Run
```

0.99 beta 负责把这条流程所需的数据结构、repository、migration 和最小 UI 基础定下来。1.0 在此基础上打磨稳定性和测试体验，不进入 AI/optimizer 阶段。

---

Plan completed. Waiting for confirmation before implementation.
