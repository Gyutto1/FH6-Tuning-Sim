# v1.1 Manual Checklist

Use this checklist to verify the v1.1 recording chain end-to-end.

## 1) New Record Flow
- Enter `Car Detail -> 开始新记录`.
- Confirm first page is `Step 0 Preset`.
- Keep preset as `不使用预设`.
- Go next and verify:
  - `Step 1 Upgrade`
  - `Step 2 Tune`
  - `Step 3 Snapshot`
  - `Step 4 Naming`
  - `Step 5 Route/Tags`
  - `Step 6 Ready`
- Confirm `开始记录` only appears at `Step 6`.

## 2) Existing Build Record Flow
- Enter from `Build Card -> 开始记录`.
- Confirm page opens at `Step 5 Route/Tags`.
- Confirm back button is hidden for setup steps.
- Confirm no Build/Tune/Snapshot editing is required before recording.

## 3) Snapshot Integrity
- In Upgrade + Tune, modify selections and values.
- In Snapshot, click `确认并冻结`.
- In Run Detail after save, verify frozen:
  - Build selections
  - Tune parameters
  - Vehicle data panel

## 4) Route Library
- In Step 5 set `Route Mode = 计时赛 / 路线`.
- Create a new route and select it.
- Confirm route appears in next runs as reusable option.

## 5) Start/Stop and Metrics
- Start recording on Step 6.
- Feed UDP packets to `127.0.0.1:9999`.
- Stop and save.
- In Run Detail verify metrics summary exists (`packet_count`, speed/rpm/power/torque etc).

## 6) Build Card Delete Cascade
- Delete a build card with associated runs.
- Confirm Build/Tune/Snapshot/Run become archived (not hard deleted).
- Confirm default active lists no longer show archived records.
