from __future__ import annotations

from pathlib import Path
import shutil
from datetime import datetime, UTC

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect


def _backup_db(db_path: Path) -> Path | None:
    if not db_path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_suffix(f".bak.{ts}{db_path.suffix}")
    shutil.copy2(db_path, backup)
    return backup


def migrate_phase1(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Phase 1 migration: stock_pi, record_types, schema_version=2."""
    db_path = Path(db_path)

    from fh6_tuning_sim.db.migrations import init_schema
    init_schema(db_path, run_migrations=False)

    conn = connect(db_path)
    try:
        cur = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        current_version = int(row["version"]) if row else 1
        if current_version >= 2:
            return
    finally:
        conn.close()

    _backup_db(db_path)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    conn = connect(db_path)
    try:
        conn.execute("BEGIN")
        try:
            conn.execute("ALTER TABLE cars ADD COLUMN stock_pi INTEGER")
        except Exception:
            pass
        conn.execute("UPDATE cars SET stock_pi = default_pi WHERE stock_pi IS NULL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS record_types (
                record_type_id TEXT PRIMARY KEY,
                record_type_key TEXT NOT NULL UNIQUE,
                label_zh TEXT NOT NULL,
                label_en TEXT,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)
        record_types = [
            ("rt_full_lap", "full_lap", "完整跑圈", "Full Lap", "计时完整跑圈", 1),
            ("rt_free_drive", "free_drive", "自由驾驶", "Free Drive", "自由驾驶记录", 2),
            ("rt_drag_strip", "drag_strip", "直线加速", "Drag Strip", "直线加速测试", 3),
            ("rt_heavy_braking", "heavy_braking", "重刹测试", "Heavy Braking", "重刹测试记录", 4),
            ("rt_normal_recording", "normal_recording", "普通记录", "Normal Recording", "普通行车记录", 5),
            ("rt_low_speed_corner", "low_speed_corner", "低速弯", "Low Speed Corner", "低速弯道测试", 6),
            ("rt_mid_speed_corner", "mid_speed_corner", "中速弯", "Mid Speed Corner", "中速弯道测试", 7),
            ("rt_high_speed_corner", "high_speed_corner", "高速弯", "High Speed Corner", "高速弯道测试", 8),
            ("rt_track_survey", "track_survey", "赛道测量", "Track Survey", "赛道边界测量", 9),
            ("rt_other", "other", "其他", "Other", "其他记录类型", 10),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO record_types (record_type_id, record_type_key, label_zh, label_en, description, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
            record_types,
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version, name, applied_at_utc) VALUES (?, ?, ?)",
            (2, "v1_0_phase1_stock_pi_record_types", now),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_phase1()
    print("Phase 1 migration complete (version 2).")
