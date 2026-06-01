# 0.99 beta Agent C：Car / Build / Tune / Setup Snapshot Workflow 报告

生成时间：2026-05-31

## 完成内容

- Car Detail 增加 `Build -> Tune -> Setup Snapshot` 层级展示。
- Record Run 增加上下文选择：
  - Build
  - Tune
  - Setup Snapshot
  - Route mode
  - Record type
  - Intent tags
- Record Run 下拉联动：
  - 选择 Build 后刷新 Tune。
  - 选择 Tune 后刷新 Setup Snapshot。
- Start 按钮启用条件扩展为完整上下文：
  - Car
  - Build
  - Tune
  - Setup Snapshot
  - Record Type
  - 至少一个 Intent Tag
- `unset` route mode 作为显式选择允许记录准备完成，但显示可比性警告。
- 为关键控件增加 objectName：
  - `mainStack`
  - `backButton`
  - `backTitle`
  - `carDetailPage`
  - `carDetailRecordButton`
  - `carDetailBuildRow_*`
  - `carDetailTuneRow_*`
  - `carDetailSetupSnapshotRow_*`
  - `carDetailRunRow_*`
  - `recordRunPage`
  - `combo_build`
  - `combo_tune`
  - `combo_setup_snapshot`
  - `combo_route_mode`
  - `recordTypeCombo`
  - `recordDatasetGroupCombo`
  - `recordIntentTagButton_*`
  - `recordNotesEdit`
  - `recordStatusLabel`
  - `recordReadyHint`
  - `btn_start_record`

## 未做

- 未接入真实 RecordingController。
- 未创建 Build/Tune/Setup Snapshot 编辑对话框；当前使用迁移/demo 中已有上下文。

## 测试结果

```text
compileall fh6_tuning_sim: PASS
unittest discover -s tests: PASS
Ran 36 tests
PySide6 offscreen context smoke: PASS
```

## Phase Gate

| 问题 | 结果 |
|------|------|
| 当前 Phase 是否通过？ | 是 |
| 是否破坏 CLI / Streamlit / parser / UDP listener？ | 否 |
| 是否有 schema 冲突？ | 未发现 |
| 是否有 repository / UI API 冲突？ | 未发现 |
| 是否有无上下文 run 风险？ | Start 准备态已要求完整上下文；尚未创建 run |
| 测试是否通过？ | 是 |
| 是否允许进入下一 Phase？ | 是 |
