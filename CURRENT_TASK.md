# Current Task

## Goal

实施 FH6 项目瘦身与工作区治理，保持 PySide6 主线可用并降低默认读取噪音。

## Allowed Read Scope

- `AI_READING_GUIDE.md`
- `README.md`
- `PROJECT_STATUS.md`
- `CURRENT_TASK.md`
- `docs/current/*`
- `current_handoff_after_client_rewire.md`
- 当前任务明确需要的实现文件

## Allowed Edit Scope

- 文档入口与工作区规则文档
- 归档目录与归档迁移
- 主线依赖声明与启动脚本文案
- 不影响业务行为的 UI 文案

## Do Not Read Unless Asked

- `docs/archive/`
- `_archive/`
- `old_versions/`
- `reports/old/`
- `logs/`
- `backup/`
- `data/raw/`
- `data/processed/`

## Do Not Edit

- `data/fh6_tuning_sim.db`
- 实时采集 raw telemetry CSV
- packet parser / UDP listener behavior

## Done Criteria

1. PySide6 主线入口与文档收敛完成  
2. 旧报告与旧 Streamlit 产物完成归档  
3. 缓存/pyc 清理完成  
4. `compileall`、测试和 desktop smoke 通过  
5. 输出瘦身前后对比与 REVIEW 清单
