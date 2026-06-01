from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect


class RecordTypeRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_all(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM record_types"
            if not include_inactive:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY sort_order, record_type_key"
            return [dict(row) for row in conn.execute(sql).fetchall()]
        finally:
            conn.close()

    def get_by_key(self, record_type_key: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM record_types WHERE record_type_key = ?", (record_type_key,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_by_id(self, record_type_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM record_types WHERE record_type_id = ?", (record_type_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
