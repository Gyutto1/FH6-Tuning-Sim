-- Upgrade / Record Rewire read-only SQL checks
-- Replace :car_id, :base_build_id, :base_tune_id with actual values in your SQL client.
-- This file is read-only verification only. Do not use for writes.

-- SQL-B1: Base build row
SELECT build_id, car_id, display_name, source, created_at_utc, updated_at_utc
FROM builds
WHERE build_id = :base_build_id;

-- SQL-T1: Base tune row
SELECT tune_id, build_id, display_name, source, created_at_utc, updated_at_utc
FROM tunes
WHERE tune_id = :base_tune_id;

-- SQL-B2: Draft build rows for car
SELECT build_id, car_id, display_name, source, created_at_utc, updated_at_utc
FROM builds
WHERE car_id = :car_id
  AND (source = 'clone_for_recording' OR lower(display_name) LIKE '%draft%')
ORDER BY created_at_utc DESC;

-- SQL-T2: Draft tune rows for car/build scope
SELECT t.tune_id, t.build_id, t.display_name, t.source, t.created_at_utc, t.updated_at_utc
FROM tunes t
JOIN builds b ON b.build_id = t.build_id
WHERE b.car_id = :car_id
  AND (t.source = 'clone_for_recording' OR lower(t.display_name) LIKE '%draft%')
ORDER BY t.created_at_utc DESC;

-- SQL-B3: Base build slot selections
SELECT build_id, slot_id, upgrade_option_id, updated_at_utc
FROM build_upgrade_selections
WHERE build_id = :base_build_id
ORDER BY slot_id;

-- SQL-T3: Base tune parameter values
SELECT tune_id, tune_parameter_id, value_real, value_text, updated_at_utc
FROM tune_parameter_values
WHERE tune_id = :base_tune_id
ORDER BY tune_parameter_id;

-- Optional: show selected option labels for base build
SELECT s.build_id, s.slot_id, o.option_key, o.label_zh, s.updated_at_utc
FROM build_upgrade_selections s
LEFT JOIN upgrade_options o ON o.upgrade_option_id = s.upgrade_option_id
WHERE s.build_id = :base_build_id
ORDER BY s.slot_id;
