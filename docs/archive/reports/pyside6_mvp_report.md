# PySide6 Desktop MVP 报告

更新时间：2026-05-30

## 概述

完成了 FH6 Tuning Sim 的 PySide6 桌面 MVP（Proof of Concept）。本 MVP 在小范围内验证了 FH6 Tuning Sim 可以作为本地桌面车辆数据平台运行，同时完全不修改后端逻辑。

## 环境说明

| 项目 | 值 |
|------|-----|
| Python | 3.12.13 (conda-forge) |
| 虚拟环境 | `.venv312` |
| PySide6 | 6.11.1 |
| 启动命令 | `.venv312\python.exe -m fh6_tuning_sim.ui_desktop.app` |
| 启动脚本 | `start_desktop.bat` |

> 原始 `.venv` 是 Conda Python 3.13，与 pip PySide6 存在 VC++ 运行时 ABI 不兼容。
> `.venv312` 使用 Python 3.12，PySide6 QtWidgets 加载正常。

## 已实现页面

### 首页 Dashboard
- 显示平台概览：车辆数、记录数、未绑定记录数
- 显示车辆预览行（名称、PI、驱动形式、记录数、数据集组数、建模准备度）
- 显示最近 5 条记录（session_id、时长、质量状态）
- 无车辆时显示 empty state

### 车辆库 My Cars
- 以卡片形式展示所有车辆（不使用 DataFrame/表格作为主视图）
- 每张卡片显示：车辆名、PI 徽章、驱动形式、记录数、数据集组数、质量分、建模准备度
- 操作按钮：「进入车辆」「开始记录」

### 车辆详情 Car Detail
- 车辆信息、指标卡片行、调校版本列表、数据集组摘要、记录列表
- 路线/测试覆盖 placeholder

### 开始记录 Record Run
- UI shell：调校版本、路线、记录类型、数据集组、备注、Start/Stop 占位
- 不接入 UDP listener

### 标签库 Tag Library
- 按类别分组可视化展示所有标签（chips）
- 9 个标签类别，25 个字典文件

### 设置 Settings
- 项目路径、依赖信息、CLI 命令、Streamlit 保留说明

## 验证结果

| 检查项 | 状态 |
|--------|------|
| QtWidgets import | PASS |
| compileall (全部文件) | PASS |
| unittest (12 tests) | PASS (0.243s) |
| app 启动 | PASS (GUI 窗口启动，Qt 事件循环运行) |
| Streamlit 未修改 | PASS |
| CLI / parser / UDP listener 未修改 | PASS |

## 未实现功能

- Routes / Route Detail / Dataset Groups / Run Review / Dictionary Manager 独立页面
- UDP listener 接入（Record Run Start/Stop 为占位符）
- 车辆编辑/创建功能
- Route Profile 完整算法

## 下一步建议

1. 接入 RecordingController 实现实际录制
2. 实现 Run Review 页面
3. 实现 Routes 和 Route Detail 页面
