# Upgrade / Record Rewire Manual Checklist

Related:
- Result template: `docs/current/upgrade_record_rewire_test_result_template.md`

## Scope
- Car-specific upgrade catalog management (category/slot/option add + per-car hide/show)
- Pre-recording Draft Build/Tune flow (no overwrite of historical configs)
- Record -> Upgrade Store -> Back navigation correctness
- Snapshot display of missing upgrade slots (total + category summary + detail)

## 1) Navigation chain
1. Enter a car and click `开始记录`.
2. In Record Step1 click `进入升级商店`.
3. Click top back button.
4. Expected: return to Record page, not Build Detail page.

Code anchors:
- `main_window.py::_enter_record`
- `main_window.py::_enter_upgrade_store`
- `main_window.py::_go_back`

## 2) Draft Build protection
1. Select a Build that already has runs.
2. In Record Step1 click `进入升级商店`.
3. Expected:
   - Draft Build is auto-created/selected.
   - Step1 hint shows Draft state.

Code anchors:
- `record_run_page.py::_open_upgrade_store`
- `record_run_page.py::_update_build_summary`
- `record_run_page.py::_build_step`

## 3) Draft Tune protection
1. In Record Step2 click `进入 Tune Detail`.
2. Expected:
   - If tune has runs or build mismatch, Draft Tune is auto-created/selected.
   - Step2 hint shows Draft state.

Code anchors:
- `record_run_page.py::_open_tune_detail`
- `record_run_page.py::_update_tune_summary`
- `record_run_page.py::_tune_step`

## 4) Draft selection persistence after save
1. Save an option in Upgrade Store.
2. Return to Record page.
3. Expected:
   - Draft Build remains selected.
   - Tune selection remains stable after combo refresh.

Code anchors:
- `main_window.py::_on_upgrade_saved`
- `record_run_page.py::ensure_build_selected`
- `record_run_page.py::ensure_tune_selected`

## 5) Car-specific upgrade catalog management
1. Open `设置 -> 车型升级目录`.
2. Add category / slot / option.
3. Hide/show category/slot/option.
4. Expected:
   - Changes apply to current car visibility.
   - No global hard-delete.

Code anchors:
- `car_upgrade_catalog_dialog.py::_add_category`
- `car_upgrade_catalog_dialog.py::_add_slot`
- `car_upgrade_catalog_dialog.py::_add_option`
- `car_upgrade_catalog_dialog.py::_toggle_category`
- `car_upgrade_catalog_dialog.py::_toggle_slot`
- `car_upgrade_catalog_dialog.py::_toggle_option`

## 6) Duplicate key prevention (negative path)
1. Try duplicate `category_key`.
2. Try duplicate `slot_key` in same category.
3. Try duplicate `option_key` in same slot scope.
4. Expected: blocked before DB write with clear warning.

Code anchors:
- `car_upgrade_catalog_dialog.py::_add_category`
- `car_upgrade_catalog_dialog.py::_add_slot`
- `car_upgrade_catalog_dialog.py::_add_option`

## 7) Cross-slot option validation (negative path)
1. Force a cross-slot selection in debug/manual call:
   - call `save_build_upgrade_selection(build_id, slot_id, option_id)` where option belongs to different slot.
2. Expected: validation error; no write.

Code anchor:
- `upgrade_store_repository.py::save_build_upgrade_selection`

## 8) Snapshot missing-slot summary
1. Confirm snapshot with partial upgrade selection.
2. Expected:
   - Missing slot total count.
   - Missing slot count by category.
   - Missing slot detail list.

Code anchor:
- `setup_snapshot_confirm_page.py` (Build 选择项 block)

## 9) Record context required-field guard
1. Leave required context fields incomplete (Build/Tune/Snapshot/Route/RecordType).
2. Try start recording.
3. Expected: start blocked; missing field list shown; no run persisted.

Code anchor:
- `record_run_page.py::_on_start_recording`

## 10) No-intent-tag fallback
1. Do not select intent tags.
2. Complete valid context and create run.
3. Expected: run creation still succeeds via fallback tag path.

Code anchor:
- `desktop_data_service.py::create_run_from_recording`

## 11) No historical overwrite
1. Use base Build/Tune with historical runs and trigger Draft flow.
2. Edit and save only Draft objects.
3. Expected:
   - Base Build selections unchanged.
   - Base Tune values unchanged.

Code anchors:
- `desktop_data_service.py::ensure_recording_draft_build`
- `desktop_data_service.py::ensure_recording_draft_tune`

## 12) Read-only SQL verification (evidence)
Use read-only SQL to prove no-overwrite:

```sql
SELECT build_id, display_name, source, updated_at_utc
FROM builds
WHERE build_id = :base_build_id;

SELECT tune_id, display_name, source, updated_at_utc
FROM tunes
WHERE tune_id = :base_tune_id;

SELECT build_id, car_id, display_name, source, created_at_utc
FROM builds
WHERE car_id = :car_id
  AND (source = 'clone_for_recording' OR lower(display_name) LIKE '%draft%')
ORDER BY created_at_utc DESC;

SELECT tune_id, build_id, display_name, source, created_at_utc
FROM tunes
WHERE build_id IN (SELECT build_id FROM builds WHERE car_id = :car_id)
  AND (source = 'clone_for_recording' OR lower(display_name) LIKE '%draft%')
ORDER BY created_at_utc DESC;

SELECT build_id, slot_id, upgrade_option_id, updated_at_utc
FROM build_upgrade_selections
WHERE build_id = :base_build_id
ORDER BY slot_id;

SELECT tune_id, tune_parameter_id, value_real, updated_at_utc
FROM tune_parameter_values
WHERE tune_id = :base_tune_id
ORDER BY tune_parameter_id;
```
