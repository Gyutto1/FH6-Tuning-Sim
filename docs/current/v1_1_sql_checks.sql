-- v1.1 SQL checks

-- 1) run context completeness
SELECT run_id, car_id, build_id, tune_id, setup_snapshot_id
FROM runs
WHERE is_active = 1
  AND status != 'archived'
  AND (
    car_id IS NULL OR car_id = '' OR
    build_id IS NULL OR build_id = '' OR
    tune_id IS NULL OR tune_id = '' OR
    setup_snapshot_id IS NULL OR setup_snapshot_id = ''
  );

-- 2) snapshot freeze existence for active runs
SELECT r.run_id
FROM runs r
LEFT JOIN snapshot_freeze_build_items b ON b.setup_snapshot_id = r.setup_snapshot_id
LEFT JOIN snapshot_freeze_tune_values t ON t.setup_snapshot_id = r.setup_snapshot_id
LEFT JOIN snapshot_freeze_vehicle_data v ON v.setup_snapshot_id = r.setup_snapshot_id
WHERE r.is_active = 1
  AND r.status != 'archived'
GROUP BY r.run_id
HAVING COUNT(DISTINCT b.id) = 0 OR COUNT(DISTINCT t.id) = 0 OR COUNT(DISTINCT v.id) = 0;

-- 3) route requirement for timed_route
SELECT run_id, route_mode, route_id
FROM runs
WHERE is_active = 1
  AND status != 'archived'
  AND route_mode = 'timed_route'
  AND (route_id IS NULL OR route_id = '');

-- 4) archived cascade inspection for build card delete
SELECT b.build_id, b.status AS build_status, b.is_active AS build_active
FROM builds b
WHERE b.status = 'archived';

SELECT t.tune_id, t.build_id, t.status AS tune_status, t.is_active AS tune_active
FROM tunes t
WHERE t.status = 'archived';

SELECT r.run_id, r.build_id, r.status AS run_status, r.is_active AS run_active
FROM runs r
WHERE r.status = 'archived';
