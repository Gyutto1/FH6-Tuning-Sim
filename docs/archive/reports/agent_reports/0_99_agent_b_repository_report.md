# 0.99 beta Agent B：Repository / Data Layer 报告

生成时间：2026-05-31

## 完成内容

新增 SQLite repository layer：

```text
fh6_tuning_sim/db/repositories/
  car_repository.py
  build_repository.py
  tune_repository.py
  setup_snapshot_repository.py
  run_repository.py
  tag_repository.py
  route_repository.py
  experiment_repository.py
```

每个 repository 接收 `db_path`，默认使用：

```text
data/fh6_tuning_sim.db
```

## 已提供能力

| Repository | 能力 |
|------------|------|
| CarRepository | 创建 / 编辑 / 查询 / 归档 Car |
| BuildRepository | 创建 / 查询 / 归档 Build，创建或复用 `default_stock_build` |
| TuneRepository | 创建 / 查询 / 归档 Tune，创建或复用 `baseline_tune` |
| SetupSnapshotRepository | 创建 / 查询 Setup Snapshot，校验 Car/Build/Tune 链路 |
| RunRepository | 创建 / 查询 / 编辑 notes / 归档 Run，绑定 / 移除 tag，多条件查询 |
| TagRepository | 创建 / 查询 / 编辑 / 归档 tags |
| RouteRepository | 创建 / 查询 routes |
| ExperimentRepository | Experiment Matrix placeholder 查询 / 创建 |

## 关键约束

- 所有写操作使用 `transaction()`。
- 所有 SQLite connection 启用 `PRAGMA foreign_keys = ON`。
- 删除类操作全部使用 archive / `is_active = 0`。
- `RunRepository.create_run()` 强制：
  - `car_id`
  - `build_id`
  - `tune_id`
  - `setup_snapshot_id`
  - `route_mode`
  - `record_type`
  - 至少一个 intent tag
- `RunRepository.create_run()` 会校验 setup snapshot 链路，防止 Build/Tune/Setup Snapshot 不一致。

## 测试结果

新增：

```text
tests/test_sqlite_repositories.py
```

验证：

- 创建并归档 Car / Build / Tune。
- 创建默认 Setup Snapshot。
- 创建 Run 时校验完整上下文。
- 无 tag 或上下文不匹配时拒绝创建 Run。
- Run Library query 支持 car/tag/keyword/archived。
- Tag / Route / Experiment placeholder repository 可用。
- Schema-only 空库可安全查询。

运行结果：

```text
compileall fh6_tuning_sim: PASS
unittest discover -s tests: PASS
Ran 36 tests
```

## Phase Gate

| 问题 | 结果 |
|------|------|
| 当前 Phase 是否通过？ | 是 |
| 是否破坏 CLI / Streamlit / parser / UDP listener？ | 否，本 Phase 未修改这些模块 |
| 是否有 schema 冲突？ | 未发现 |
| 是否有 repository / UI API 冲突？ | UI 尚未接入，RunRepository 已提供兼容 query view model |
| 是否有无上下文 run 风险？ | repository 已拒绝无完整上下文 run |
| 测试是否通过？ | 是 |
| 是否允许进入下一 Phase？ | 是 |

## 已知后续事项

- PySide6 `DesktopDataService` 尚未切换到 SQLite repository。
- Run Library 页面仍直接调用 JSON-backed service。
- Record Run 尚未有 Build/Tune/Setup Snapshot 选择控件。
