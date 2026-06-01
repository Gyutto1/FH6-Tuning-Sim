from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import active_flag, clean_key, require_text, utc_now


class TuneRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_by_build(self, build_id: str, include_archived: bool = False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM tunes WHERE build_id = ?"
            params: list[Any] = [build_id]
            if not include_archived:
                sql += " AND is_active = 1 AND status != 'archived'"
            sql += " ORDER BY lower(display_name), version"
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def get_tune(self, tune_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM tunes WHERE tune_id = ?", (tune_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_tune(self, build_id: str, data: dict[str, Any]) -> dict[str, Any]:
        display_name = require_text(data.get("display_name"), "display_name")
        tune_key = str(data.get("tune_key") or clean_key(display_name, "baseline_tune"))
        version = str(data.get("version") or "v00")
        tune_id = str(data.get("tune_id") or f"{build_id}__tune__{tune_key}__{clean_key(version, 'v00')}")
        now = utc_now()
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tunes (
                    tune_id, build_id, display_name, tune_key, version, status, is_active,
                    notes, source, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tune_id,
                    build_id,
                    display_name,
                    tune_key,
                    version,
                    data.get("status") or "active",
                    active_flag(data.get("is_active", True)),
                    data.get("notes") or "",
                    data.get("source") or "manual",
                    now,
                    now,
                ),
            )
        created = self.get_tune(tune_id)
        if created is None:
            raise RuntimeError("tune insert failed")
        return created

    def ensure_baseline_tune(self, build_id: str) -> dict[str, Any]:
        tune_id = f"{build_id}__tune__baseline_tune__v00"
        existing = self.get_tune(tune_id)
        if existing:
            return existing
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM tunes WHERE build_id = ? AND tune_key = 'baseline_tune'",
                (build_id,),
            ).fetchone()
            if row:
                return dict(row)
        finally:
            conn.close()
        return self.create_tune(
            build_id,
            {
                "tune_id": tune_id,
                "display_name": "baseline_tune",
                "tune_key": "baseline_tune",
                "version": "v00",
                "source": "system_default",
            },
        )

    def update_tune(self, tune_id: str, updates: dict[str, Any]) -> bool:
        allowed = {"display_name", "version", "status", "is_active", "notes"}
        fields = [(key, updates[key]) for key in updates if key in allowed]
        if not fields:
            return False
        set_clause = ", ".join([f"{key} = ?" for key, _ in fields] + ["updated_at_utc = ?"])
        values = [active_flag(value) if key == "is_active" else value for key, value in fields]
        values.extend([utc_now(), tune_id])
        with transaction(self.db_path) as conn:
            cur = conn.execute(f"UPDATE tunes SET {set_clause} WHERE tune_id = ?", values)
            return cur.rowcount > 0

    def archive_tune(self, tune_id: str) -> bool:
        return self.update_tune(tune_id, {"status": "archived", "is_active": 0})
