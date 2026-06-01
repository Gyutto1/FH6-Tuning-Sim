# Upgrade / Record Rewire Handoff

## Objective
Implement car-specific upgrade catalog adaptation and pre-record Build/Tune draft workflow, while preventing overwrite of historical Build/Tune used by runs.

## What Is Implemented

### 1) Upgrade selection data model and validation
- `build_upgrade_selections` key uses `(build_id, slot_id)`.
- Save path enforces slot-option consistency:
  - `option.slot_id == slot_id`
  - option category matches slot category
- Main save entry:
  - `fh6_tuning_sim/db/repositories/upgrade_store_repository.py::save_build_upgrade_selection`

### 2) Upgrade Store page flow
- Internal view-state flow implemented:
  - `category_grid -> slot_list -> option_list`
- No per-category/per-slot stacked page explosion.
- Save status feedback added (`current / pending / saved` behavior).
- File:
  - `fh6_tuning_sim/ui_desktop/pages/upgrade_store_page.py`

### 3) Car-specific upgrade catalog visibility and management
- Per-car visibility in read path:
  - category / slot / option level
- Per-car management dialog supports:
  - add category / slot / option
  - hide/show category / slot / option per current car
  - pre-submit duplicate key prevention
  - key normalization/format checks
- Files:
  - `fh6_tuning_sim/ui_desktop/pages/car_upgrade_catalog_dialog.py`
  - `fh6_tuning_sim/db/repositories/upgrade_store_repository.py`
  - `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py`

### 4) Record wizard draft protections
- When entering upgrade/tune editing from Record:
  - auto-clone Draft Build if selected build already has runs
  - auto-clone Draft Tune if tune already has runs or build mismatch
- Draft state exposed in UI summaries/hints.
- Draft selection persistence improved after upgrade-store save.
- Files:
  - `fh6_tuning_sim/ui_desktop/pages/record_run_page.py`
  - `fh6_tuning_sim/ui_desktop/main_window.py`
  - `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py`

### 5) Navigation correctness
- Back path from Upgrade Store respects source context:
  - from Record -> back to Record
  - from Build detail -> back to Build detail
- File:
  - `fh6_tuning_sim/ui_desktop/main_window.py`

### 6) Snapshot missing-slot visibility
- Snapshot confirm page now shows:
  - missing-slot total
  - missing-slot count by category
  - missing-slot detail list
- File:
  - `fh6_tuning_sim/ui_desktop/pages/setup_snapshot_confirm_page.py`

### 7) Tag fallback for run creation
- If no intent tags selected, run creation path can fallback to `未分类` intent tag.
- File:
  - `fh6_tuning_sim/ui_desktop/services/desktop_data_service.py`

## Verification Artifacts
- Manual checklist:
  - `docs/current/upgrade_record_rewire_manual_checklist.md`
- Result template:
  - `docs/current/upgrade_record_rewire_test_result_template.md`

## Known Risks / Notes
1. Multiple files had historical encoding corruption; key pages were rewritten, but any untouched page with legacy text should be watched during manual run.
2. No full end-to-end GUI automation exists yet for this flow; current verification is compile + checklist-driven manual validation.
3. Catalog key uniqueness constraints are DB-backed; UI now pre-checks, but concurrent edits can still race and must rely on DB constraint.

## Remaining Work (Recommended Next)
1. Execute the manual checklist and fill result template with evidence (screenshots + SQL evidence ids).
2. Add one lightweight integration test around draft-clone protection logic:
   - build with historical runs -> ensure draft build selected/used
   - tune with historical runs -> ensure draft tune selected/used
3. Optional: add explicit warning banner in Record step when current selection is Base but historical runs exist.

## Quick Start For Next Agent
1. Read:
   - `docs/current/upgrade_record_rewire_manual_checklist.md`
   - `docs/current/upgrade_record_rewire_test_result_template.md`
2. Run compile sanity:
   - `py -m compileall fh6_tuning_sim/ui_desktop/pages/record_run_page.py fh6_tuning_sim/ui_desktop/pages/upgrade_store_page.py fh6_tuning_sim/ui_desktop/main_window.py`
3. Execute checklist cases and collect evidence into template.
