PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cars (
    car_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    year INTEGER,
    car_ordinal INTEGER,
    car_group INTEGER,
    default_car_class TEXT,
    stock_pi INTEGER,
    default_pi INTEGER,
    default_drivetrain TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS builds (
    build_id TEXT PRIMARY KEY,
    car_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    build_key TEXT NOT NULL,
    pi INTEGER,
    car_class TEXT,
    pi_source TEXT DEFAULT 'manual_total',
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    UNIQUE (car_id, build_key)
);

CREATE TABLE IF NOT EXISTS build_snapshots (
    build_snapshot_id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    snapshot_name TEXT,
    pi INTEGER,
    car_class TEXT,
    drivetrain TEXT,
    power REAL,
    torque REAL,
    weight REAL,
    tire_compound TEXT,
    upgrade_summary TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (build_id) REFERENCES builds(build_id)
);

CREATE TABLE IF NOT EXISTS upgrade_categories (
    upgrade_category_id TEXT PRIMARY KEY,
    category_key TEXT NOT NULL UNIQUE,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    display_order INTEGER DEFAULT 0,
    section_id TEXT REFERENCES tune_sections(section_id),
    display_type TEXT DEFAULT 'slider',
    side TEXT,
    unlock_condition TEXT,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS upgrade_options (
    upgrade_option_id TEXT PRIMARY KEY,
    upgrade_category_id TEXT NOT NULL,
    slot_id TEXT,
    option_key TEXT NOT NULL,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    is_stock INTEGER NOT NULL DEFAULT 0,
    pi_impact INTEGER,
    weight_impact REAL,
    cost_credits INTEGER,
    default_pi_delta INTEGER,
    unlock_tune_sections TEXT,
    tier INTEGER DEFAULT 0,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
    FOREIGN KEY (slot_id) REFERENCES upgrade_slots(slot_id),
    UNIQUE (upgrade_category_id, option_key)
);

CREATE TABLE IF NOT EXISTS build_upgrade_selections (
    build_id TEXT NOT NULL,
    slot_id TEXT NOT NULL,
    upgrade_category_id TEXT NOT NULL,
    upgrade_option_id TEXT,
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY (build_id, slot_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (slot_id) REFERENCES upgrade_slots(slot_id),
    FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
    FOREIGN KEY (upgrade_option_id) REFERENCES upgrade_options(upgrade_option_id)
);

CREATE TABLE IF NOT EXISTS upgrade_compatibility_rules (
    upgrade_rule_id TEXT PRIMARY KEY,
    rule_type TEXT NOT NULL,
    source_option_id TEXT,
    target_option_id TEXT,
    payload_json TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);


CREATE TABLE IF NOT EXISTS upgrade_slots (
    slot_id TEXT PRIMARY KEY,
    upgrade_category_id TEXT NOT NULL,
    slot_key TEXT NOT NULL,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
    UNIQUE (upgrade_category_id, slot_key)
);

CREATE TABLE IF NOT EXISTS car_upgrade_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id TEXT NOT NULL,
    upgrade_category_id TEXT,
    slot_id TEXT,
    option_id TEXT,
    is_available INTEGER NOT NULL DEFAULT 1,
    override_label_zh TEXT,
    override_label_en TEXT,
    override_pi_delta INTEGER,
    notes TEXT,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (upgrade_category_id) REFERENCES upgrade_categories(upgrade_category_id),
    FOREIGN KEY (slot_id) REFERENCES upgrade_slots(slot_id),
    FOREIGN KEY (option_id) REFERENCES upgrade_options(upgrade_option_id)
);

CREATE TABLE IF NOT EXISTS tune_sections (
    section_id TEXT PRIMARY KEY,
    section_key TEXT NOT NULL UNIQUE,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS car_tune_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id TEXT NOT NULL,
    build_id TEXT,
    section_id TEXT,
    parameter_id TEXT,
    is_available INTEGER NOT NULL DEFAULT 1,
    override_min_value REAL,
    override_max_value REAL,
    override_step REAL,
    override_unit TEXT,
    override_default_value REAL,
    notes TEXT,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (section_id) REFERENCES tune_sections(section_id),
    FOREIGN KEY (parameter_id) REFERENCES tune_parameter_definitions(tune_parameter_id)
);

CREATE TABLE IF NOT EXISTS snapshot_build_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL,
    category_label_zh TEXT,
    slot_label_zh TEXT,
    option_label_zh TEXT,
    pi_delta INTEGER,
    unit TEXT,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (snapshot_id) REFERENCES setup_snapshots(setup_snapshot_id)
);

CREATE TABLE IF NOT EXISTS snapshot_tune_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL,
    section_label_zh TEXT,
    parameter_label_zh TEXT,
    value REAL,
    unit TEXT,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (snapshot_id) REFERENCES setup_snapshots(setup_snapshot_id)
);

CREATE TABLE IF NOT EXISTS snapshot_vehicle_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL,
    data_key TEXT NOT NULL,
    label_zh TEXT,
    value TEXT,
    unit TEXT,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (snapshot_id) REFERENCES setup_snapshots(setup_snapshot_id)
);
CREATE TABLE IF NOT EXISTS tunes (
    tune_id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    tune_key TEXT NOT NULL,
    version TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    UNIQUE (build_id, tune_key, version)
);

CREATE TABLE IF NOT EXISTS tune_parameter_definitions (
    tune_parameter_id TEXT PRIMARY KEY,
    parameter_key TEXT NOT NULL UNIQUE,
    category TEXT,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    unit TEXT,
    min_value REAL,
    max_value REAL,
    step REAL,
    value_type TEXT NOT NULL DEFAULT 'float',
    description TEXT,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER DEFAULT 0,
    section_id TEXT REFERENCES tune_sections(section_id),
    display_type TEXT DEFAULT 'slider',
    side TEXT,
    unlock_condition TEXT
);

CREATE TABLE IF NOT EXISTS tune_parameter_values (
    tune_id TEXT NOT NULL,
    tune_parameter_id TEXT NOT NULL,
    value_text TEXT,
    value_real REAL,
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY (tune_id, tune_parameter_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    FOREIGN KEY (tune_parameter_id) REFERENCES tune_parameter_definitions(tune_parameter_id)
);

CREATE TABLE IF NOT EXISTS setup_snapshots (
    setup_snapshot_id TEXT PRIMARY KEY,
    car_id TEXT NOT NULL,
    build_id TEXT NOT NULL,
    tune_id TEXT NOT NULL,
    snapshot_name TEXT,
    pi INTEGER,
    car_class TEXT,
    drivetrain TEXT,
    power REAL,
    torque REAL,
    weight REAL,
    front_weight_percent REAL,
    tire_compound TEXT,
    performance_ratings TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    UNIQUE (setup_snapshot_id, car_id, build_id, tune_id)
);

CREATE TABLE IF NOT EXISTS routes (
    route_id TEXT PRIMARY KEY,
    route_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    route_mode TEXT NOT NULL,
    surface_type TEXT,
    route_type TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id TEXT PRIMARY KEY,
    tag_key TEXT NOT NULL,
    category TEXT NOT NULL,
    label_zh TEXT NOT NULL,
    label_en TEXT,
    description TEXT,
    is_system INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER DEFAULT 0,
    section_id TEXT REFERENCES tune_sections(section_id),
    display_type TEXT DEFAULT 'slider',
    side TEXT,
    unlock_condition TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    UNIQUE (category, tag_key)
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    car_id TEXT NOT NULL,
    build_id TEXT NOT NULL,
    tune_id TEXT NOT NULL,
    setup_snapshot_id TEXT NOT NULL,
    route_id TEXT,
    route_mode TEXT NOT NULL,
    record_type TEXT NOT NULL,
    use_case TEXT,
    raw_csv_path TEXT,
    processed_csv_path TEXT,
    plot_path TEXT,
    report_path TEXT,
    dataset_path TEXT,
    metadata_path TEXT,
    tune_snapshot_path TEXT,
    duration_seconds REAL,
    packet_count INTEGER,
    estimated_sample_rate REAL,
    quality_status TEXT,
    quality_warnings TEXT,
    metrics_json TEXT,
    notes TEXT,
    review_notes TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    FOREIGN KEY (setup_snapshot_id, car_id, build_id, tune_id)
        REFERENCES setup_snapshots(setup_snapshot_id, car_id, build_id, tune_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);

CREATE TABLE IF NOT EXISTS run_tags (
    run_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    tag_role TEXT NOT NULL DEFAULT 'intent',
    created_at_utc TEXT NOT NULL,
    PRIMARY KEY (run_id, tag_id, tag_role),
    FOREIGN KEY (run_id) REFERENCES runs(run_id),
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
);

CREATE TABLE IF NOT EXISTS annotations (
    annotation_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    run_id TEXT,
    start_time REAL,
    end_time REAL,
    source TEXT NOT NULL DEFAULT 'manual',
    confidence REAL DEFAULT 1.0,
    note TEXT,
    payload_json TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS annotation_tags (
    annotation_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    PRIMARY KEY (annotation_id, tag_id),
    FOREIGN KEY (annotation_id) REFERENCES annotations(annotation_id),
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
);

CREATE TABLE IF NOT EXISTS dataset_groups (
    dataset_group_id TEXT PRIMARY KEY,
    car_id TEXT,
    display_name TEXT NOT NULL,
    purpose TEXT,
    route_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);

CREATE TABLE IF NOT EXISTS dataset_group_runs (
    dataset_group_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    PRIMARY KEY (dataset_group_id, run_id),
    FOREIGN KEY (dataset_group_id) REFERENCES dataset_groups(dataset_group_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS experiment_matrices (
    experiment_matrix_id TEXT PRIMARY KEY,
    car_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    purpose TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    payload_json TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars(car_id)
);

CREATE TABLE IF NOT EXISTS experiment_variables (
    experiment_variable_id TEXT PRIMARY KEY,
    experiment_matrix_id TEXT NOT NULL,
    variable_type TEXT NOT NULL,
    variable_key TEXT NOT NULL,
    payload_json TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (experiment_matrix_id) REFERENCES experiment_matrices(experiment_matrix_id)
);

CREATE TABLE IF NOT EXISTS experiment_tasks (
    experiment_task_id TEXT PRIMARY KEY,
    experiment_matrix_id TEXT NOT NULL,
    build_id TEXT,
    tune_id TEXT,
    setup_snapshot_id TEXT,
    route_id TEXT,
    record_type TEXT,
    required_run_count INTEGER NOT NULL DEFAULT 1,
    completed_run_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (experiment_matrix_id) REFERENCES experiment_matrices(experiment_matrix_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    FOREIGN KEY (setup_snapshot_id) REFERENCES setup_snapshots(setup_snapshot_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);

CREATE TABLE IF NOT EXISTS recording_sessions (
    recording_session_id TEXT PRIMARY KEY,
    run_id TEXT,
    car_id TEXT NOT NULL,
    build_id TEXT NOT NULL,
    tune_id TEXT NOT NULL,
    setup_snapshot_id TEXT NOT NULL,
    route_id TEXT,
    route_mode TEXT NOT NULL,
    record_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at_utc TEXT,
    stopped_at_utc TEXT,
    packet_count INTEGER DEFAULT 0,
    metadata_json TEXT,
    error_message TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id),
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (build_id) REFERENCES builds(build_id),
    FOREIGN KEY (tune_id) REFERENCES tunes(tune_id),
    FOREIGN KEY (setup_snapshot_id, car_id, build_id, tune_id)
        REFERENCES setup_snapshots(setup_snapshot_id, car_id, build_id, tune_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);

CREATE INDEX IF NOT EXISTS idx_builds_car_id ON builds(car_id);
CREATE INDEX IF NOT EXISTS idx_tunes_build_id ON tunes(build_id);
CREATE INDEX IF NOT EXISTS idx_setup_snapshots_context ON setup_snapshots(car_id, build_id, tune_id);
CREATE INDEX IF NOT EXISTS idx_runs_context ON runs(car_id, build_id, tune_id, setup_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_runs_route ON runs(route_id, route_mode);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status, is_active);
CREATE INDEX IF NOT EXISTS idx_run_tags_tag_id ON run_tags(tag_id);

INSERT OR IGNORE INTO schema_version (version, name, applied_at_utc)
VALUES (1, 'desktop_0_99_beta_initial_schema', datetime('now'));
