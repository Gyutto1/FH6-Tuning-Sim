from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import active_flag, clean_key, require_text, utc_now


class RouteRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_routes(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM routes"
            if not include_inactive:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY route_mode, lower(display_name)"
            return [dict(row) for row in conn.execute(sql).fetchall()]
        finally:
            conn.close()

    def get_route(self, route_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM routes WHERE route_id = ?", (route_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_route(self, data: dict[str, Any]) -> dict[str, Any]:
        display_name = require_text(data.get("display_name"), "display_name")
        route_key = str(data.get("route_key") or clean_key(display_name, "route"))
        route_id = str(data.get("route_id") or f"route_{route_key}")
        now = utc_now()
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO routes (
                    route_id, route_key, display_name, route_mode, surface_type, route_type,
                    source, notes, is_active, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    route_id,
                    route_key,
                    display_name,
                    data.get("route_mode") or "timed_route",
                    data.get("surface_type"),
                    data.get("route_type"),
                    data.get("source") or "manual",
                    data.get("notes") or "",
                    active_flag(data.get("is_active", True)),
                    now,
                    now,
                ),
            )
        created = self.get_route(route_id)
        if created is None:
            raise RuntimeError("route insert failed")
        return created
