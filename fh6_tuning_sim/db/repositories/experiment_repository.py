from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import active_flag, clean_key, require_text, utc_now


class ExperimentRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_matrices(self, car_id: str | None = None, include_archived: bool = False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM experiment_matrices WHERE 1=1"
            params: list[Any] = []
            if car_id:
                sql += " AND car_id = ?"
                params.append(car_id)
            if not include_archived:
                sql += " AND is_active = 1"
            sql += " ORDER BY updated_at_utc DESC"
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def create_placeholder_matrix(self, car_id: str, display_name: str) -> dict[str, Any]:
        display_name = require_text(display_name, "display_name")
        matrix_id = f"{car_id}__matrix__{clean_key(display_name, 'placeholder')}"
        now = utc_now()
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO experiment_matrices (
                    experiment_matrix_id, car_id, display_name, purpose, status, payload_json,
                    notes, is_active, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, 'placeholder', 'draft', '{}', '', ?, ?, ?)
                """,
                (matrix_id, car_id, display_name, active_flag(True), now, now),
            )
        matrices = self.list_matrices(car_id)
        return next(item for item in matrices if item["experiment_matrix_id"] == matrix_id)
