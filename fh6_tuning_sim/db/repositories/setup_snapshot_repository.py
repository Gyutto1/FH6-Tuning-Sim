from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import active_flag, clean_key, utc_now


DEFAULT_RATINGS = {
    "speed": None,
    "handling": None,
    "acceleration": None,
    "launch": None,
    "braking": None,
    "offroad": None,
}


class SetupSnapshotRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def get_snapshot(self, setup_snapshot_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM setup_snapshots WHERE setup_snapshot_id = ?", (setup_snapshot_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_by_tune(self, tune_id: str, include_archived: bool = False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM setup_snapshots WHERE tune_id = ?"
            params: list[Any] = [tune_id]
            if not include_archived:
                sql += " AND is_active = 1"
            sql += " ORDER BY updated_at_utc DESC"
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def validate_context(self, car_id: str, build_id: str, tune_id: str, setup_snapshot_id: str) -> bool:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT 1
                FROM setup_snapshots ss
                JOIN builds b ON b.build_id = ss.build_id AND b.car_id = ss.car_id
                JOIN tunes t ON t.tune_id = ss.tune_id AND t.build_id = ss.build_id
                WHERE ss.setup_snapshot_id = ? AND ss.car_id = ? AND ss.build_id = ? AND ss.tune_id = ?
                """,
                (setup_snapshot_id, car_id, build_id, tune_id),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def create_snapshot(self, car_id: str, build_id: str, tune_id: str, data: dict[str, Any]) -> dict[str, Any]:
        snapshot_name = str(data.get("snapshot_name") or "默认记录前快照")
        setup_snapshot_id = str(
            data.get("setup_snapshot_id")
            or f"{car_id}__setup__{clean_key(build_id, 'build')}__{clean_key(tune_id, 'tune')}__{clean_key(snapshot_name, 'default')}"
        )
        ratings = data.get("performance_ratings") or DEFAULT_RATINGS
        ratings_json = ratings if isinstance(ratings, str) else json.dumps(ratings, ensure_ascii=False)
        now = utc_now()
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO setup_snapshots (
                    setup_snapshot_id, car_id, build_id, tune_id, snapshot_name, pi, car_class,
                    drivetrain, power, torque, weight, front_weight_percent, tire_compound,
                    performance_ratings, source, notes, is_active, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    setup_snapshot_id,
                    car_id,
                    build_id,
                    tune_id,
                    snapshot_name,
                    data.get("pi"),
                    data.get("car_class"),
                    data.get("drivetrain"),
                    data.get("power"),
                    data.get("torque"),
                    data.get("weight"),
                    data.get("front_weight_percent"),
                    data.get("tire_compound"),
                    ratings_json,
                    data.get("source") or "manual",
                    data.get("notes") or "",
                    active_flag(data.get("is_active", True)),
                    now,
                    now,
                ),
            )
        created = self.get_snapshot(setup_snapshot_id)
        if created is None:
            raise RuntimeError("setup snapshot insert failed")
        return created

    def update_snapshot(self, setup_snapshot_id: str, updates: dict[str, Any]) -> bool:
        allowed = {
            "snapshot_name",
            "pi",
            "car_class",
            "drivetrain",
            "power",
            "torque",
            "weight",
            "front_weight_percent",
            "tire_compound",
            "performance_ratings",
            "source",
            "notes",
            "is_active",
        }
        fields: list[tuple[str, Any]] = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "performance_ratings" and not isinstance(value, str):
                value = json.dumps(value or DEFAULT_RATINGS, ensure_ascii=False)
            fields.append((key, active_flag(value) if key == "is_active" else value))
        if not fields:
            return False
        set_clause = ", ".join([f"{key} = ?" for key, _ in fields] + ["updated_at_utc = ?"])
        values = [value for _, value in fields]
        values.extend([utc_now(), setup_snapshot_id])
        with transaction(self.db_path) as conn:
            cur = conn.execute(f"UPDATE setup_snapshots SET {set_clause} WHERE setup_snapshot_id = ?", values)
            return cur.rowcount > 0

    def confirm_snapshot(self, setup_snapshot_id: str, confirmed_pi: int | None = None, confirmed_class: str | None = None, frozen_summary_json: str | None = None) -> bool:
        """Confirm a snapshot: set confirmed_at, confirmed_pi, confirmed_class, and optional frozen_json."""
        now = utc_now()
        with transaction(self.db_path) as conn:
            cur = conn.execute(
                """UPDATE setup_snapshots
                   SET confirmed_at = ?, confirmed_pi = COALESCE(?, confirmed_pi, pi),
                       confirmed_class = COALESCE(?, confirmed_class, car_class),
                       frozen_summary_json = COALESCE(?, frozen_summary_json),
                       updated_at_utc = ?
                   WHERE setup_snapshot_id = ?""",
                (now, confirmed_pi, confirmed_class, frozen_summary_json, now, setup_snapshot_id),
            )
            return cur.rowcount > 0

    def get_current_for_car(self, car_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM setup_snapshots WHERE car_id = ? AND is_current = 1 ORDER BY updated_at_utc DESC LIMIT 1",
                (car_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def ensure_default_setup_snapshot(self, car_id: str, build_id: str, tune_id: str) -> dict[str, Any]:
        setup_snapshot_id = f"{car_id}__setup__{clean_key(build_id, 'build')}__{clean_key(tune_id, 'tune')}__default"
        existing = self.get_snapshot(setup_snapshot_id)
        if existing:
            return existing
        return self.create_snapshot(
            car_id,
            build_id,
            tune_id,
            {
                "setup_snapshot_id": setup_snapshot_id,
                "snapshot_name": "默认记录前快照",
                "source": "system_default",
                "performance_ratings": DEFAULT_RATINGS,
            },
        )
