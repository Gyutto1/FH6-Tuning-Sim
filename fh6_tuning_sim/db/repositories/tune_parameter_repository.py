from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import utc_now


class TuneParameterRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_definitions(self, include_disabled: bool = False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM tune_parameter_definitions"
            if not include_disabled:
                sql += " WHERE is_enabled = 1"
            sql += " ORDER BY category, display_order, parameter_key"
            return [dict(row) for row in conn.execute(sql).fetchall()]
        finally:
            conn.close()

    def list_values(self, tune_id: str) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    d.tune_parameter_id, d.parameter_key, d.category, d.label_zh, d.label_en, d.unit, d.min_value, d.max_value, d.step, d.value_type, d.description, d.is_enabled, d.display_order, d.section_id, d.display_type, d.side, d.unlock_condition,
                    ts.label_zh AS section_label_zh,
                    ts.sort_order AS section_sort_order,
                    v.tune_id,
                    v.value_text,
                    v.value_real,
                    v.notes AS value_notes,
                    v.updated_at_utc AS value_updated_at_utc
                FROM tune_parameter_definitions d
                LEFT JOIN tune_sections ts ON ts.section_id = d.section_id
                LEFT JOIN tune_parameter_values v
                    ON v.tune_parameter_id = d.tune_parameter_id
                   AND v.tune_id = ?
                WHERE d.is_enabled = 1
                ORDER BY COALESCE(ts.sort_order, 999), d.display_order, d.parameter_key
                """,
                (tune_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_by_section(self, tune_id: str) -> dict[str, list[dict[str, Any]]]:
        """Return parameters grouped by section_id with values."""
        rows = self.list_values(tune_id)
        sections: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            section_id = str(row.get("section_id") or "other")
            sections.setdefault(section_id, []).append(row)
        return sections

    def get_sections(self) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM tune_sections WHERE is_active = 1 ORDER BY sort_order"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def save_values(self, tune_id: str, values: list[dict[str, Any]]) -> None:
        now = utc_now()
        with transaction(self.db_path) as conn:
            for value in values:
                parameter_id = str(value.get("tune_parameter_id") or "").strip()
                if not parameter_id:
                    continue
                conn.execute(
                    """
                    INSERT INTO tune_parameter_values (
                        tune_id, tune_parameter_id, value_text, value_real, notes,
                        created_at_utc, updated_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(tune_id, tune_parameter_id) DO UPDATE SET
                        value_text = excluded.value_text,
                        value_real = excluded.value_real,
                        notes = excluded.notes,
                        updated_at_utc = excluded.updated_at_utc
                    """,
                    (
                        tune_id,
                        parameter_id,
                        value.get("value_text"),
                        value.get("value_real"),
                        value.get("notes") or "",
                        now,
                        now,
                    ),
                )
