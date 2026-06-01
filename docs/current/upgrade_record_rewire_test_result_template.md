# Upgrade/Record Rewire Test Result Template

## How To Use
- For each case, fill:
  - `Result`: `PASS` / `FAIL` / `BLOCKED`
  - `Evidence`: screenshot path / log snippet / DB query result / run_id
  - `SQL Evidence`: SQL query id + returned row summary (if applicable)
  - `Notes`: short reason when not `PASS`

---

## Case 1: Record -> Upgrade Store -> Back return path
- Expected:
  - Enter from Record, back should return to Record (not Build Detail).
- Result:
- Evidence:
- Notes:

## Case 2: Draft Build auto-create on protected Build
- Expected:
  - If selected Build already has runs, entering Upgrade Store from Record creates/selects Draft Build.
  - Step1 hint shows Draft.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 3: Draft Tune auto-create on protected Tune
- Expected:
  - If selected Tune already has runs or build mismatch, entering Tune Detail from Record creates/selects Draft Tune.
  - Step2 hint shows Draft.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 4: Draft selection persistence after save
- Expected:
  - Save option in Upgrade Store, back to Record keeps Draft Build selected.
  - Tune selection remains stable after refresh.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 5: Catalog add category (positive path)
- Expected:
  - New category appears in catalog for current car.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 6: Catalog add slot (positive path)
- Expected:
  - New slot appears under selected category.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 7: Catalog add option (positive path)
- Expected:
  - New option appears under selected slot.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 8: Catalog hide/show category/slot/option
- Expected:
  - Hide/show toggles affect current car visibility only.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 9: Duplicate key prevention (negative path)
- Expected:
  - Duplicate key blocked before DB write with clear warning.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 10: Cross-slot option selection blocked (negative path)
- Expected:
  - `save_build_upgrade_selection(build_id, slot_id, option_id)` rejects option when `option.slot_id != slot_id`.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 11: Snapshot missing-slot summary
- Expected:
  - Show missing slot total.
  - Show missing slot count by category.
  - Show missing slot detail list.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 12: Record context required field guard
- Expected:
  - Missing required fields blocks recording start, shows missing list.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 13: Record creation with no intent tags fallback
- Expected:
  - Recording can still create run with fallback tag path.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

## Case 14: No historical overwrite guarantee
- Expected:
  - Original Build/Tune used by historical runs remain unchanged after Draft editing.
- Result:
- Evidence:
- SQL Evidence:
- Notes:

---

## SQL Query IDs (reference)
- `SQL-B1`: Base build row
- `SQL-T1`: Base tune row
- `SQL-B2`: Draft build rows for car
- `SQL-T2`: Draft tune rows for car/build scope
- `SQL-B3`: Base build slot selections
- `SQL-T3`: Base tune parameter values

SQL file:
- `docs/current/upgrade_record_rewire_sql_checks.sql`

---

## Environment
- App commit/checkpoint:
- DB path:
- Test car_id:
- Test build_id (base):
- Test tune_id (base):
- Tester:
- Date:

## Final Decision
- Release decision: `GO` / `NO-GO`
- Blocking issues:
- Follow-up tasks:
