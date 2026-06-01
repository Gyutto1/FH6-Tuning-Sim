# Client Menu Logic

FH6 Desktop remains vehicle-centered:

```text
Car -> Build -> Tune -> Setup Snapshot -> Run
```

## Core hierarchy meaning
- `Car`: vehicle container.
- `Build`: hardware/upgrade selections.
- `Tune`: parameter values under one Build.
- `Setup Snapshot`: frozen state before recording.
- `Run`: one recording bound to one snapshot.

## Upgrade Store flow
Upgrade Store is one page with internal state flow:

```text
category_grid -> slot_list -> option_list
```

Data hierarchy:

```text
upgrade_categories -> upgrade_slots -> upgrade_options
build_upgrade_selections
```

Persistence model:
- One build selects one option per slot.
- Unique key is `(build_id, slot_id)`.
- Save validation requires `option.slot_id == slot_id`.

## Car-specific catalog adaptation
For each car, category/slot/option visibility can differ:
- Add category/slot/option from catalog manager.
- Hide/show per current car via availability table.
- Avoid global hard-delete for normal adaptation.

Catalog entry points:
- `设置 -> 车型升级目录`
- `车辆详情 -> 管理车型升级目录`

## Record wizard and draft protection
Record uses a 5-step wizard:
1. Select/Confirm Build
2. Select/Edit Tune
3. Confirm Snapshot
4. Route/RecordType/IntentTags
5. Ready/Start

When editing from Record:
- If selected Build already has runs, auto-clone Draft Build.
- If selected Tune already has runs or build mismatch, auto-clone Draft Tune.
- UI shows Draft/Base state hints in Step1/Step2 and summary.
- Returning from Upgrade Store keeps Draft selections stable.

## Tune page flow
Tune Detail uses:
- Section list first.
- Section parameter editor second.
- Back returns to section list.

## Snapshot and run requirements
Snapshot confirmation freezes:
- Build selections
- Tune values
- Vehicle data panel values
- Snapshot PI/Class and notes

Run creation requires:
- car/build/tune/snapshot/route/record_type

Intent tags:
- Core creation should not be blocked by missing tags.
- Fallback path uses a non-raw default such as `未分类`.

## Verification entry
Use:
- `docs/current/upgrade_record_rewire_manual_checklist.md`
- `docs/current/upgrade_record_rewire_test_result_template.md`
- `docs/current/upgrade_record_rewire_sql_checks.sql`
