from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import active_flag, clean_key, require_text, utc_now


class CarRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_cars(self, include_archived: bool = False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM cars"
            if not include_archived:
                sql += " WHERE is_active = 1 AND status != 'archived'"
            sql += " ORDER BY lower(display_name)"
            return [dict(row) for row in conn.execute(sql).fetchall()]
        finally:
            conn.close()

    def get_car(self, car_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM cars WHERE car_id = ?", (car_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_car(self, data: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        display_name = require_text(data.get("display_name"), "display_name")
        car_id = str(data.get("car_id") or f"car_{clean_key(display_name, 'unnamed_car')}")
        stock_pi = data.get("stock_pi") or data.get("default_pi") or data.get("performance_index")
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO cars (
                    car_id, display_name, manufacturer, model, year, car_ordinal, car_group,
                    default_car_class, stock_pi, default_pi, default_drivetrain, status, is_active,
                    notes, source, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    car_id,
                    display_name,
                    data.get("manufacturer"),
                    data.get("model"),
                    data.get("year"),
                    data.get("car_ordinal"),
                    data.get("car_group"),
                    data.get("default_car_class") or data.get("car_class"),
                    stock_pi,
                    stock_pi,
                    data.get("default_drivetrain") or data.get("drivetrain"),
                    data.get("status") or "active",
                    active_flag(data.get("is_active", True)),
                    data.get("notes") or "",
                    data.get("source") or "manual",
                    now,
                    now,
                ),
            )
        created = self.get_car(car_id)
        if created is None:
            raise RuntimeError("car insert failed")
        return created

    def update_car(self, car_id: str, updates: dict[str, Any]) -> bool:
        allowed = {
            "display_name",
            "manufacturer",
            "model",
            "year",
            "car_ordinal",
            "car_group",
            "default_car_class",
            "stock_pi",
            "default_drivetrain",
            "status",
            "is_active",
            "notes",
        }
        fields = [(key, updates[key]) for key in updates if key in allowed]
        if not fields:
            return False
        set_clause = ", ".join([f"{key} = ?" for key, _ in fields] + ["updated_at_utc = ?"])
        values = [active_flag(value) if key == "is_active" else value for key, value in fields]
        values.extend([utc_now(), car_id])
        with transaction(self.db_path) as conn:
            cur = conn.execute(f"UPDATE cars SET {set_clause} WHERE car_id = ?", values)
            return cur.rowcount > 0

    def archive_car(self, car_id: str) -> bool:
        return self.update_car(car_id, {"status": "archived", "is_active": 0})
