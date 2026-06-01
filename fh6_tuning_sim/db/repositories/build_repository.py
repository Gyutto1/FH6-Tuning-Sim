from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import active_flag, clean_key, require_text, utc_now


class BuildRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_by_car(self, car_id: str, include_archived: bool = False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM builds WHERE car_id = ?"
            params: list[Any] = [car_id]
            if not include_archived:
                sql += " AND is_active = 1 AND status != 'archived'"
            sql += " ORDER BY lower(display_name)"
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def get_build(self, build_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM builds WHERE build_id = ?", (build_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def latest_build_snapshot(self, build_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT * FROM build_snapshots
                WHERE build_id = ?
                ORDER BY created_at_utc DESC
                LIMIT 1
                """,
                (build_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_upgrade_selections(self, build_id: str) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    s.*,
                    c.category_key,
                    c.label_zh AS category_label,
                    us.slot_key,
                    us.label_zh AS slot_label_zh,
                    o.option_key,
                    o.label_zh AS option_label,
                    COALESCE(o.default_pi_delta, o.pi_impact) AS pi_delta
                FROM build_upgrade_selections s
                JOIN upgrade_categories c ON c.upgrade_category_id = s.upgrade_category_id
                JOIN upgrade_slots us ON us.slot_id = s.slot_id
                LEFT JOIN upgrade_options o ON o.upgrade_option_id = s.upgrade_option_id
                WHERE s.build_id = ?
                ORDER BY c.display_order, us.sort_order, c.category_key
                """,
                (build_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def create_build(self, car_id: str, data: dict[str, Any]) -> dict[str, Any]:
        display_name = require_text(data.get("display_name"), "display_name")
        build_key = str(data.get("build_key") or clean_key(display_name, "default_stock_build"))
        build_id = str(data.get("build_id") or f"{car_id}__build__{build_key}")
        now = utc_now()
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO builds (
                    build_id, car_id, display_name, build_key, status, is_active, notes,
                    source, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    build_id,
                    car_id,
                    display_name,
                    build_key,
                    data.get("status") or "active",
                    active_flag(data.get("is_active", True)),
                    data.get("notes") or "",
                    data.get("source") or "manual",
                    now,
                    now,
                ),
            )
        created = self.get_build(build_id)
        if created is None:
            raise RuntimeError("build insert failed")
        return created

    def ensure_default_stock_build(self, car_id: str) -> dict[str, Any]:
        build_id = f"{car_id}__build__default_stock_build"
        existing = self.get_build(build_id)
        if existing:
            return existing
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM builds WHERE car_id = ? AND build_key = 'default_stock_build'",
                (car_id,),
            ).fetchone()
            if row:
                return dict(row)
        finally:
            conn.close()
        return self.create_build(
            car_id,
            {
                "build_id": build_id,
                "build_key": "default_stock_build",
                "display_name": "原厂默认",
                "source": "system_default",
            },
        )

    def update_build(self, build_id: str, updates: dict[str, Any]) -> bool:
        allowed = {"display_name", "pi", "car_class", "pi_source", "status", "is_active", "notes"}
        fields = [(key, updates[key]) for key in updates if key in allowed]
        if not fields:
            return False
        set_clause = ", ".join([f"{key} = ?" for key, _ in fields] + ["updated_at_utc = ?"])
        values = [active_flag(value) if key == "is_active" else value for key, value in fields]
        values.extend([utc_now(), build_id])
        with transaction(self.db_path) as conn:
            cur = conn.execute(f"UPDATE builds SET {set_clause} WHERE build_id = ?", values)
            return cur.rowcount > 0

    def archive_build(self, build_id: str) -> bool:
        return self.update_build(build_id, {"status": "archived", "is_active": 0})
