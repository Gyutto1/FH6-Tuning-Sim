# 0.99.1 Subtask F: Tag Consistency Report

Date: 2026-05-31

## Status

Complete for v0.99.1.

## Completed

- RunRepository now exposes tag labels and tag items in run records.
- DesktopDataService supports tag-id filtering while preserving tag-key compatibility.
- Run Library tag filter uses `tag_id`.
- Run cards display `label_zh`.
- Add/remove tag actions use tag IDs.
- Tag Library duplicate user-tag rendering remains fixed.

## Verification

Unit test covers:

```text
create Chinese tag
bind it to a run
verify tag_id and label_zh are present
filter by tag_id
remove the tag
verify it no longer matches
```
