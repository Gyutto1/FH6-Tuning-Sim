# 0.99 beta Agent C：PySide6 UI / SQLite Service 报告

生成时间：2026-05-31

## 完成内容

- `DesktopDataService` 已从 JSON facade 切换为 SQLite-backed facade。
- 保留 v0.5 页面依赖的类名、构造方式和主要 API。
- PySide6 页面仍通过 service/repository 访问数据，不直接写 SQL。
- 新增 service API：
  - `list_builds_for_car(car_id)`
  - `list_tunes_for_build(build_id)`
  - `list_setup_snapshots_for_tune(tune_id)`
- `Run Library` 数据源切换为 SQLite `RunRepository.query_run_records()`。
- `Tag Library` 数据源切换为 SQLite `tags` 表。
- `update_car`、`update_run_notes`、`add_tag_to_run`、`remove_tag_from_run`、`archive_run` 改为 SQLite 写入。
- `tests/test_run_library_filter.py` 的 CRUD 测试改用临时 SQLite demo DB，避免污染真实 JSON / 主 DB。

## 保持兼容的 UI API

继续保留：

```text
list_cars()
get_car(car_id)
list_runs_for_car(car_id)
list_dataset_groups_for_car(car_id)
list_unassigned_runs()
list_all_runs()
search_runs()
list_routes()
list_tags_by_category()
dashboard_stats()
update_car()
add_user_tag()
list_user_tags()
run_display_title()
run_subtitle()
list_run_records()
filter_run_records()
update_run_notes()
add_tag_to_run()
remove_tag_from_run()
archive_run()
```

## 当前 UI 状态

- Dashboard / My Cars / Car Detail / Run Library / Tag Library / Settings 可通过 SQLite-backed service 初始化。
- Record Run 页面仍是 v0.5 表单，还没有 Build/Tune/Setup Snapshot 选择控件。
- Build/Tune/Setup Snapshot API 已在 service 中准备，供 Phase 4 接入。

## 测试结果

```text
compileall fh6_tuning_sim: PASS
unittest discover -s tests: PASS
Ran 36 tests
PySide6 offscreen MainWindow smoke: PASS
```

## Phase Gate

| 问题 | 结果 |
|------|------|
| 当前 Phase 是否通过？ | 是 |
| 是否破坏 CLI / Streamlit / parser / UDP listener？ | 否，本 Phase 未修改这些模块 |
| 是否有 schema 冲突？ | 未发现 |
| 是否有 repository / UI API 冲突？ | 现有页面 API 保持兼容 |
| 是否有无上下文 run 风险？ | UI 尚未创建新 run；repository 仍拒绝 orphan run |
| 测试是否通过？ | 是 |
| 是否允许进入下一 Phase？ | 是 |

## 已知后续事项

- Record Run 需要新增 Build / Tune / Setup Snapshot 选择和上下文校验。
- Car Detail 需要显式展示 Builds、Tunes、Setup Snapshots。
- 关键 PySide6 控件需要补 `objectName`。
