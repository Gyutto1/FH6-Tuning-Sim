# 0.99 beta Agent A：SQLite Schema / Migration 报告

生成时间：2026-05-31

## 完成内容

- 新增 SQLite 存储包：`fh6_tuning_sim/db/`
- 新增 schema：`fh6_tuning_sim/db/schema.sql`
- 新增连接与 transaction helper：`connection.py`
- 新增 schema 初始化：`migrations.py`
- 新增 legacy JSON migration：`legacy_migration.py`
- 新增 demo seed：`seed_data/demo_seed.py`
- 新增初始化入口：`init_db.py`
- 新增测试：`tests/test_sqlite_schema_migration.py`

## 数据库产物

| 数据库 | 状态 |
|--------|------|
| `data/fh6_tuning_sim.db` | 已创建，legacy JSON 已导入 |
| `data/demo/fh6_demo.db` | 已创建，demo seed 已导入 |

## 主数据库迁移结果

| 表 | 数量 |
|----|------|
| cars | 2 |
| builds | 2 |
| tunes | 2 |
| setup_snapshots | 2 |
| runs | 4 |
| tags | 148 |
| routes | 3 |
| annotations | 1 |

检查结果：

```text
PRAGMA foreign_key_check: PASS
orphan_runs: 0
```

Legacy JSON 缺少 Build / Setup Snapshot 的上下文时，迁移自动创建：

```text
default_stock_build
baseline_tune / legacy tune name
default_setup_snapshot
```

## Demo 数据库结果

| 表 | 数量 |
|----|------|
| cars | 2 |
| builds | 3 |
| tunes | 4 |
| setup_snapshots | 4 |
| routes | 3 |
| runs | 10 |
| tags | 10 |

Demo 覆盖：

```text
Car -> Build -> Tune -> Setup Snapshot -> Run
Run tags
Route mode
Archived status
Keyword-search notes
1 archived run
1+ free drive run
1+ unset route run
```

检查结果：

```text
PRAGMA foreign_key_check: PASS
orphan_runs: 0
```

## 测试结果

```text
compileall fh6_tuning_sim: PASS
unittest discover -s tests: PASS
Ran 32 tests
```

## Phase Gate

| 问题 | 结果 |
|------|------|
| 当前 Phase 是否通过？ | 是 |
| 是否破坏 CLI / Streamlit / parser / UDP listener？ | 否，本 Phase 未修改这些模块 |
| 是否有 schema 冲突？ | 未发现 |
| 是否有 repository / UI API 冲突？ | 未接入 UI，暂无冲突 |
| 是否有无上下文 run 风险？ | 当前迁移与 demo 均为 0 orphan |
| 测试是否通过？ | 是 |
| 是否允许进入下一 Phase？ | 是 |

## 已知后续事项

- Repository layer 尚未实现。
- PySide6 仍在使用 v0.5 JSON `DesktopDataService`。
- `.gitignore` 当前会忽略 `reports/*.md`，后续 Agent E 阶段必须修正。
