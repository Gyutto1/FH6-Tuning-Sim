# PySide6 RecordingController 最小接入报告

更新时间：2026-05-30

## 概述

本阶段（v0.4.1）实现了 PySide6 Desktop MVP 的最小真实录制闭环：

```
车辆详情 → 开始新记录 → Record Run 页面 → Start Recording → Stop Recording
→ 生成 raw CSV / metadata → 新 run 归入当前车辆 → 返回车辆详情后可见
```

## 接入了哪些文件

### 新建文件

| 文件 | 用途 |
|------|------|
| `fh6_tuning_sim/ui_desktop/services/recording_worker.py` | QObject + QThread 封装 UDP 录制循环 |

### 修改文件

| 文件 | 变更内容 |
|------|---------|
| `fh6_tuning_sim/ui_desktop/pages/record_run_page.py` | 从占位符 shell 替换为完整录制页面：含 UDP 设置、状态机、QThread 管理、run index 同步 |
| `fh6_tuning_sim/ui_desktop/main_window.py` | 新增 `_connect_signals()` 连接 `recording_completed` 信号；录制完成后自动跳转回 Car Detail；版本号更新为 v0.4.1 |

### 未修改文件

- `fh6_tuning_sim/receiver/udp_listener.py`
- `fh6_tuning_sim/receiver/packet_parser.py`
- `fh6_tuning_sim/receiver/raw_logger.py`
- `fh6_tuning_sim/data_management/run_index.py`
- `fh6_tuning_sim/data_management/platform_store.py`
- `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py`
- 所有 Streamlit / CLI 文件

## RecordingController 现有接口理解

项目中不存在 `fh6_tuning_sim/data_management/recording_controller.py`（AGENTS.md 中列出的路径为空，可能是一个规划中但未实现的文件）。现有录制功能完全由 CLI 工具链提供：

- `fh6_tuning_sim/receiver/udp_listener.py` — CLI 入口，包含 `listen()` 阻塞函数
- `fh6_tuning_sim/receiver/raw_logger.py` — `TelemetryCsvLogger` 上下文管理器，负责 `open()` / `write_row()` / `close()`
- `fh6_tuning_sim/receiver/packet_parser.py` — `parse_packet()` 解析 324 字节 FH6 数据包

`listen()` 函数是阻塞的 `while True` 循环，不适合直接用在 PySide6 主线程。因此采用 QThread + RecordingWorker 模式封装。

## PySide6 如何调用录制逻辑

### 架构

```
RecordRunPage (主线程 UI)
  ├── QThread
  │   └── RecordingWorker (moveToThread)
  │       ├── socket.socket (UDP bind + recvfrom)
  │       ├── parse_packet() (复用 packet_parser)
  │       └── TelemetryCsvLogger (复用 raw_logger)
  └── Signals 连接
      ├── status_changed → 更新状态标签
      ├── packet_count_changed → 更新数据包计数
      ├── elapsed_changed → 更新已用时间
      ├── session_ready → 索引 run + 导航回 Car Detail
      └── error_occurred → 显示错误
```

### 关键设计决策

1. **不导入 `udp_listener.listen()`** — 它是阻塞函数，不可直接复用。而是复用其底层组件（socket + parser + logger）。
2. **socket timeout = 1.0s** — 与 CLI listener 一致的超时设置，确保 `_stop_flag` 检查在一秒内生效。
3. **`_finalize()` 确保安全关闭** — 无论正常停止还是异常退出，都会调用 `logger.close()` + `sock.close()`，保证元数据文件完整写入。
4. **信号节流** — `packet_count_changed` 和 `elapsed_changed` 每 30 个包才发射一次，避免 UI 刷新过频。
5. **run index 同步在主线程** — `_on_session_ready` 信号回调在主线程执行，调用 `build_run_record()` + `upsert_run()`，避免跨线程写 JSON 问题。

### RecordingWorker 信号

| 信号 | 参数 | 触发时机 |
|------|------|---------|
| `status_changed` | `str` | 状态转换时（等待数据/记录中/已停止/错误） |
| `packet_count_changed` | `int` | 每 30 个包 + 最终停止时 |
| `elapsed_changed` | `float` | 每 30 个包 + 最终停止时 |
| `session_ready` | `str, str` | 录制停止且有数据时（session_id, csv_path） |
| `error_occurred` | `str` | 无法绑定端口或其他 socket 错误时 |

## Start/Stop 状态机

```
                  ┌──────────┐
                  │  未开始   │ ← 初始状态 / load_car 重置
                  └────┬─────┘
                       │ [Start 按钮]
                  ┌────▼─────┐
                  │ 等待数据   │ ← socket bind 成功，等待首个数据包
                  └────┬─────┘
                       │ [首个数据包到达]
                  ┌────▼─────┐
             ┌────│  记录中   │────┐
             │    └────┬─────┘    │
             │         │          │
      [Stop] │    [socket 错误]   │ [socket 错误]
             │         │          │
        ┌────▼──┐  ┌──▼───┐  ┌───▼──┐
        │ 已停止 │  │ 错误  │  │ 错误  │
        └───────┘  └──────┘  └──────┘
```

状态转换规则：
- **未开始 → 等待数据**：socket bind 成功，开始监听
- **等待数据 → 记录中**：首个有效数据包被解析
- **记录中 → 已停止**：用户点击 Stop，正常停止
- **记录中 → 错误**：socket 异常（端口被占用等）
- **等待数据 → 错误**：socket 异常
- **未开始 → 错误**：bind 失败（端口不可用）

## Record Run 页面最小字段

| 字段 | 来源 | 备注 |
|------|------|------|
| 当前车辆 | `car.display_name` + PI + drivetrain | 不可编辑，从车辆上下文传入 |
| 调校版本 | `car.tune_versions` 下拉 | 默认"默认调校" |
| 路线 | `list_routes()` + "自由驾驶" | 默认"自由驾驶" |
| 记录类型 | 硬编码 4 项（完整跑圈/自由驾驶/赛道测量/测试场景） | 内部映射为英文 key |
| 数据集组 | `car.dataset_groups` 下拉 | 默认"默认组" |
| 备注 | QTextEdit 自由文本 | 写入 metadata.notes |
| UDP host | QLineEdit 默认 127.0.0.1 | 可编辑 |
| UDP port | QLineEdit 默认 9999 | 可编辑 |
| Session ID | 自动生成或录制后显示 | 录制完成后显示 |
| 输出路径 | 录制完成后显示 | data/raw/{session_id}.csv |
| 状态 | 5 状态指示器 | 颜色编码 |
| 数据包计数 | 实时更新 | 录制中 |
| 已用时间 | 实时更新 | 录制中 |

## 测试结果

| 检查项 | 状态 |
|--------|------|
| compileall (全部文件) | PASS |
| unittest (12 tests) | PASS (0.229s) |
| Desktop app import | PASS |
| RecordingWorker import | PASS |
| RecordingWorker 状态常量 | PASS (5 个状态全部存在) |
| data/raw 目录存在 | PASS |
| data/sessions 目录存在 | PASS |
| Streamlit / CLI 未修改 | PASS |
| packet parser 未修改 | PASS |
| UDP listener 未修改 | PASS |
| raw telemetry schema 未修改 | PASS |

### 未执行的测试

由于无法在 CI 环境中启动 GUI 窗口或连接真实 FH6 游戏，以下测试需人工验证：

1. 启动桌面端：`start_desktop.bat`
2. 从车辆库进入 Mercedes-AMG GT
3. 点击"开始新记录"
4. 验证 Record Run 页面显示当前车辆信息
5. 点击 Start — 验证状态变为"等待数据"且 UI 不阻塞
6. 如有 FH6 数据发送，验证状态变为"记录中"、packet count 增长
7. 点击 Stop — 验证状态变为"已停止"
8. 验证自动返回 Car Detail 页面
9. 验证新 run 出现在记录列表中

## 未完成的部分

- Run Review 页面（不在本阶段范围）
- Routes / Route Detail 页面（不在本阶段范围）
- Record Run 的调校版本、路线、数据集组字段目前仅做 UI 展示，metadata 写入后需验证 `build_run_record` 是否能正确关联
- 没有 packet 到达时的超时自动停止（当前会无限等待，需用户手动 Stop）

## 下一步建议

1. **人工 GUI 验证** — 启动桌面端执行完整录制闭环测试
2. **实现 Run Review 页面** — 录制完成后用户需回看标签/评分
3. **Routes / Route Detail 页面** — 完成路线维度的车辆数据中心
4. **Record Run 字段深度集成** — 让调校版本、路线选择、数据集组字段真正影响 run index 写入

## 架构评估

本阶段实现严格遵循 AGENTS.md 约束：

- ✅ 复用现有 UDP listener 底层组件（packet_parser + raw_logger）
- ✅ 未重写 UDP listener（`udp_listener.py` 未修改）
- ✅ 未修改 packet parser
- ✅ 未修改 raw telemetry schema
- ✅ PySide6 UI 不被录制过程阻塞（QThread 模式）
- ✅ 使用 QThread + Signal-Slot 安全模式
- ✅ Start/Stop 安全（TelemetryCsvLogger 正确 close，元数据完整写入）
- ✅ 无 packet 时状态显示合理（"等待数据"）
- ✅ 未实现 AI training / RL / optimizer / world model
- ✅ 未实现 Run Review / Routes / Route Profile
- ✅ 未迁移 SQLite / 未打包 EXE
- ✅ 现有 tests 全部通过
