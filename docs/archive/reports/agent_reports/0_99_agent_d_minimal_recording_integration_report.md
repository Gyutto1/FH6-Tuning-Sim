# 0.99 beta Agent D：Minimal RecordingController Integration 报告

生成时间：2026-05-31

## 完成内容

- Record Run 页面接入 `RecordingWorker + QThread`。
- 新增 Stop 按钮。
- Start 前使用 `validate_recording_context()` 校验完整上下文。
- Worker 不修改 UDP listener 行为，不修改 packet parser，不修改 raw telemetry schema。
- Worker 停止后通过 `DesktopDataService.create_run_from_recording()` 写入 SQLite `runs` 和 `run_tags`。
- `create_run_from_recording()` 内部调用 repository，继续强制：
  - `car_id`
  - `build_id`
  - `tune_id`
  - `setup_snapshot_id`
  - `route_mode`
  - `record_type`
  - 至少一个可解析 intent tag

## Recording 状态

UI 当前支持：

```text
未开始
上下文不完整
准备完成
等待数据
记录中
已停止
错误
```

## 数据写入

Recording 完成后创建 run：

```text
runs.raw_csv_path
runs.packet_count
runs.duration_seconds
runs.status = active
runs.quality_status = draft
run_tags intent tags
```

不在 raw CSV 写入 manual labels 或 derived analysis。

## 测试结果

新增/扩展：

```text
tests/test_recording_context_service.py
```

验证：

- Desktop service 可以从完整 recording context 创建 run。
- 创建的 run 能出现在 Run Library records 中。
- 无完整上下文仍由 validator/repository 拒绝。

运行结果：

```text
compileall fh6_tuning_sim: PASS
unittest discover -s tests: PASS
Ran 41 tests
PySide6 offscreen Recording integration smoke: PASS
```

## Phase Gate

| 问题 | 结果 |
|------|------|
| 当前 Phase 是否通过？ | 是 |
| 是否破坏 CLI / Streamlit / parser / UDP listener？ | 否 |
| 是否有 schema 冲突？ | 未发现 |
| 是否有 repository / UI API 冲突？ | 未发现 |
| 是否有无上下文 run 风险？ | repository 和 UI validator 均阻止 |
| 测试是否通过？ | 是 |
| 是否允许进入下一 Phase？ | 是 |

## 已知限制

- 当前 Recording 停止后只创建 SQLite run，不自动跑 feature engineering / plot / report。
- 若用户点击开始但 FH6 没有发送 UDP 数据，Worker 仍会进入等待状态，用户可手动停止。
