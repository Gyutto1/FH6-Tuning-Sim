# Upgrade / Record Rewire Requirement Matrix

This matrix maps user requirements to implementation anchors and verification evidence.

## R1. v4 migration accepted; slot-level persistence required
- Requirement:
  - One build selects one option per slot (not per category).
- Implementation:
  - `build_upgrade_selections` primary key `(build_id, slot_id)` in schema.
  - Save path writes by `(build_id, slot_id)`.
- Code anchors:
  - `fh6_tuning_sim/db/schema.sql` (`build_upgrade_selections`)
  - `fh6_tuning_sim/db/repositories/upgrade_store_repository.py::save_build_upgrade_selection`
- Evidence:
  - SQL check in manual checklist section 12 (`build_upgrade_selections` by slot).

## R2. save_build_upgrade_selection must validate option-slot consistency
- Requirement:
  - Reject cross-slot option selection.
- Implementation:
  - Enforced checks:
    - option exists and active
    - `option.slot_id == slot_id`
    - option category matches slot category
- Code anchor:
  - `fh6_tuning_sim/db/repositories/upgrade_store_repository.py::save_build_upgrade_selection`
- Evidence:
  - Manual checklist negative path case `Cross-slot option validation`.

## R3. UpgradeStorePage uses internal state flow
- Requirement:
  - `category_grid -> slot_list -> option_list` in one page.
- Implementation:
  - Internal `view_state` rendering flow.
- Code anchor:
  - `fh6_tuning_sim/ui_desktop/pages/upgrade_store_page.py`
- Evidence:
  - Manual checklist navigation + store operations.

## R4. Tune page section -> parameter flow
- Requirement:
  - Section list first, section parameter page second, with back.
- Implementation:
  - Section list + `_enter_section` + `_back_to_sections`.
- Code anchor:
  - `fh6_tuning_sim/ui_desktop/pages/tune_detail_page.py`
- Evidence:
  - Manual checklist Draft Tune + tune detail path.

## R5. intent_tags should not block core run creation
- Requirement:
  - Required chain fields remain enforceable.
  - No tag selection should still allow creation via fallback/warning policy.
- Implementation:
  - Run creation path injects fallback intent tag (`未分类`) when no tag id resolved.
- Code anchor:
  - `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py::create_run_from_recording`
- Evidence:
  - Template Case 13 + SQL evidence for run/tag rows.

## R6. Record path must not overwrite historical Build/Tune
- Requirement:
  - If selected Build/Tune already used by runs, create Draft objects before editing.
- Implementation:
  - `ensure_recording_draft_build`
  - `ensure_recording_draft_tune`
  - Record page entry points call these before editing flows.
- Code anchors:
  - `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py`
  - `fh6_tuning_sim/ui_desktop/pages/record_run_page.py::_open_upgrade_store`
  - `fh6_tuning_sim/ui_desktop/pages/record_run_page.py::_open_tune_detail`
- Evidence:
  - Template Cases 2,3,14 + SQL-B/T evidence IDs.

## R7. Upgrade Store back path from Record
- Requirement:
  - Back from store returns to Record when opened from Record.
- Implementation:
  - Source-aware store entry and back route.
- Code anchors:
  - `fh6_tuning_sim/ui_desktop/main_window.py::_enter_upgrade_store`
  - `fh6_tuning_sim/ui_desktop/main_window.py::_go_back`
- Evidence:
  - Template Case 1.

## R8. Remove overlap/duplication in Record flow
- Requirement:
  - Avoid duplicate category UI blocks in Record.
- Implementation:
  - Record Step1 uses single entry button to Upgrade Store (no duplicated 2x3 category panel).
- Code anchor:
  - `fh6_tuning_sim/ui_desktop/pages/record_run_page.py::_build_step`
- Evidence:
  - Template Case 1/2 visual check.

## R9. Snapshot should show missing unselected slots
- Requirement:
  - Show selected + unselected status clearly.
- Implementation:
  - Missing slot total + category summary + detail list.
- Code anchor:
  - `fh6_tuning_sim/ui_desktop/pages/setup_snapshot_confirm_page.py`
- Evidence:
  - Template Case 11.

## R10. Tag deletion rule
- Requirement:
  - Cannot delete tag if already used in existing records.
- Implementation:
  - `can_archive_tag` checks run/annotation usage before archive.
- Code anchors:
  - `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py::can_archive_tag`
  - `fh6_tuning_sim/ui_desktop/pages/tag_library_page.py`
- Evidence:
  - Negative manual check in Tag UI.

## R11. Car-specific catalog add/delete(adapted as hide/show)
- Requirement:
  - Category/slot/option can be adjusted per car; avoid global hard delete.
- Implementation:
  - Add category/slot/option APIs.
  - Per-car hide/show via availability table.
  - Pre-submit key checks in dialog.
- Code anchors:
  - `fh6_tuning_sim/db/repositories/upgrade_store_repository.py`
  - `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py`
  - `fh6_tuning_sim/ui_desktop/pages/car_upgrade_catalog_dialog.py`
- Evidence:
  - Template Cases 5-9.

## Evidence Pack
- Manual checklist:
  - `docs/current/upgrade_record_rewire_manual_checklist.md`
- Result template:
  - `docs/current/upgrade_record_rewire_test_result_template.md`
- SQL checks:
  - `docs/current/upgrade_record_rewire_sql_checks.sql`
- Handoff summary:
  - `docs/current/upgrade_record_rewire_handoff.md`
