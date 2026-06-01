# FH6 Tuning Sim Desktop 0.99 beta Migration Report

生成时间：2026-05-31

## 输入

```text
data/platform/platform_index.json
data/index/runs_index.json
data/index/tags.json
data/index/annotations.json
configs/dictionaries/*.json
```

Raw telemetry / processed / report 文件仅保存路径引用，未修改。

## 输出

```text
data/fh6_tuning_sim.db
data/demo/fh6_demo.db
```

## Legacy 导入策略

- cars 保留原有 `car_id`。
- runs 保留 `session_id` 作为 `run_id`。
- legacy run 缺少 Build 时创建 `default_stock_build`。
- legacy run 缺少 Setup Snapshot 时创建 `default_setup_snapshot`。
- Tune 优先使用 legacy `tune_id` / `tune_name`。
- `route_name=unknown` 的 legacy run 映射为 `route_mode=unset`。
- 每个 run 至少绑定一个 intent tag；legacy 无 tag 时使用 `normal_driving`。

## 迁移计数

| 对象 | Legacy | SQLite |
|------|--------|--------|
| cars | 2 | 2 |
| runs | 4 | 4 |
| builds | N/A | 2 |
| tunes | N/A | 2 |
| setup_snapshots | N/A | 2 |
| tags | dictionaries + user tags | 148 |
| annotations | 1 | 1 |

## 验证

```text
PRAGMA foreign_key_check: PASS
orphan_runs: 0
```

## 已知限制

- Legacy JSON 没有真实 Build 改件信息，因此迁移为 `default_stock_build`。
- Legacy JSON 没有真实 Setup Snapshot general/performance 完整字段，缺失数值保留为 NULL。
- Legacy routes 多为 `unknown`，迁移为显式 `unset` route mode。
- 新写入应进入 SQLite；JSON 仅作为 legacy/import/export。
