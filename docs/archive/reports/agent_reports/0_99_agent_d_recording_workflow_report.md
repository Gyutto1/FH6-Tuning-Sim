# 0.99 beta Agent D：Recording Context Validation 报告

生成时间：2026-05-31

## 完成内容

- 新增 `RecordingContextService`：
  - `ensure_default_context(car_id)`
  - `validate(context)`
  - `validate_or_raise(context)`
- `DesktopDataService` 暴露：
  - `ensure_default_recording_context(car_id)`
  - `validate_recording_context(context)`
- Record Run 页面改为调用统一 context validator。
- Start 按钮只在完整上下文时启用。

## Recording 前置条件

校验项：

```text
car_id
build_id
tune_id
setup_snapshot_id
route_mode
record_type
至少一个 intent tag
Car/Build/Tune/Setup Snapshot 链路一致
intent tag 存在于 SQLite tags
```

`unset` route mode 是显式可选状态，会显示可比性警告，但不视为缺失。

## 修复的问题

测试发现 `ensure_default_stock_build()` 在已有 `build_key=default_stock_build` 但 `build_id` 不同的 demo/legacy 数据上会触发唯一约束冲突。已修复为：

```text
先按固定 build_id 查找
再按 (car_id, build_key='default_stock_build') 查找
都不存在才创建
```

同理，`ensure_baseline_tune()` 现在会按 `(build_id, tune_key='baseline_tune')` 复用已有 tune。

## 测试结果

新增：

```text
tests/test_recording_context_service.py
```

验证：

- 完整上下文通过。
- 缺少 Build/Tune/Setup Snapshot/Route/Record Type/Intent Tags 时失败。
- Build/Tune/Setup Snapshot 链路不一致时失败。
- 默认原厂上下文可创建或复用。

运行结果：

```text
compileall fh6_tuning_sim: PASS
unittest discover -s tests: PASS
Ran 40 tests
PySide6 offscreen Record Run context smoke: PASS
```

## Phase Gate

| 问题 | 结果 |
|------|------|
| 当前 Phase 是否通过？ | 是 |
| 是否破坏 CLI / Streamlit / parser / UDP listener？ | 否 |
| 是否有 schema 冲突？ | 未发现 |
| 是否有 repository / UI API 冲突？ | 已修复默认上下文复用冲突 |
| 是否有无上下文 run 风险？ | context validator 已阻止 |
| 测试是否通过？ | 是 |
| 是否允许进入下一 Phase？ | 是 |

## 下一步

进入 Phase 7 前置判断：真实 RecordingController 最小接入是否安全。
