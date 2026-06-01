# 0.99 beta Agent C：Run Library on SQLite 报告

生成时间：2026-05-31

## 完成内容

- Run Library 继续通过 `DesktopDataService` 访问 SQLite repository。
- 增加上下文筛选：
  - Car
  - Build
  - Tune
  - Setup Snapshot
  - Route Mode
  - Record Type
  - Quality
  - Tag
  - Keyword
- `DesktopDataService.filter_run_records()` 增加：
  - `build_id`
  - `tune_id`
  - `setup_snapshot_id`
- Run Library 关键控件增加 objectName：
  - `runLibraryPage`
  - `run_library_filter_car`
  - `run_library_filter_build`
  - `run_library_filter_tune`
  - `run_library_filter_setup_snapshot`
  - `run_library_filter_tag`
  - `run_library_search_box`
  - `runRecordCard_*`
  - `runRecordEditNotesButton_*`
  - `runRecordAddTagButton_*`
  - `runRecordRemoveTagButton_*`
  - `runRecordArchiveButton_*`

## CRUD 状态

- 编辑 notes：SQLite `runs.notes`
- 添加 tag：SQLite `run_tags`
- 移除 tag：SQLite `run_tags`
- 归档：SQLite `runs.status='archived'`, `is_active=0`
- 不 hard-delete raw 文件或 run 记录。

## 测试结果

```text
compileall fh6_tuning_sim: PASS
unittest discover -s tests: PASS
Ran 36 tests
PySide6 offscreen Run Library smoke: PASS
```

## Phase Gate

| 问题 | 结果 |
|------|------|
| 当前 Phase 是否通过？ | 是 |
| 是否破坏 CLI / Streamlit / parser / UDP listener？ | 否 |
| 是否有 schema 冲突？ | 未发现 |
| 是否有 repository / UI API 冲突？ | 未发现 |
| 是否有无上下文 run 风险？ | Run Library 不创建 run；archive 只软归档 |
| 测试是否通过？ | 是 |
| 是否允许进入下一 Phase？ | 是 |
