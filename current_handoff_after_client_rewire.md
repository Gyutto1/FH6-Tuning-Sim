# Current Handoff After Client Rewire

Status: active implementation and verification package for upgrade-record rewire is in place.

## Mainline assumptions
- PySide6 Desktop + SQLite mainline.
- Vehicle-centered hierarchy:
  - `Car -> Build -> Tune -> Setup Snapshot -> Run`

## Rewire outcomes
1. Slot-level persistence implemented:
   - Build selections persist by `(build_id, slot_id)`.
   - Save validates slot-option consistency.
2. Upgrade Store flow implemented as internal state page:
   - `category_grid -> slot_list -> option_list`
3. Car-specific upgrade catalog adaptation enabled:
   - add category/slot/option
   - per-car hide/show at category/slot/option level
4. Record wizard draft protection enabled:
   - auto Draft Build/Tune in protected cases
   - prevent overwrite of historical Build/Tune used by runs
5. Snapshot confirm visibility improved:
   - missing slot total + category summary + detail
6. Run creation fallback path:
   - no intent tag still creatable via fallback `未分类` path

## Key verification docs
- `docs/current/upgrade_record_rewire_handoff.md`
- `docs/current/upgrade_record_rewire_requirement_matrix.md`
- `docs/current/upgrade_record_rewire_manual_checklist.md`
- `docs/current/upgrade_record_rewire_test_result_template.md`
- `docs/current/upgrade_record_rewire_sql_checks.sql`
- `docs/current/client_menu_logic.md`

## Next execution
1. Execute manual checklist.
2. Fill result template with UI/log/SQL evidence.
3. Apply SQL checks to prove no-overwrite for base Build/Tune.

## Read order for next agent
1. `AI_READING_GUIDE.md`
2. `README.md`
3. `PROJECT_STATUS.md`
4. `docs/current/client_menu_logic.md`
5. Rewire docs listed above
