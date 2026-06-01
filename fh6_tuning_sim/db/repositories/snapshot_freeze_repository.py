from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import utc_now


class SnapshotFreezeRepository:
    """Write and read frozen snapshot detail tables."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def freeze_build_items(self, snapshot_id: str, items: list[dict[str, Any]]) -> None:
        now = utc_now()
        with transaction(self.db_path) as conn:
            conn.execute("DELETE FROM snapshot_build_items WHERE snapshot_id = ?", (snapshot_id,))
            for idx, item in enumerate(items):
                conn.execute(
                    """
                    INSERT INTO snapshot_build_items (
                        snapshot_id, category_label_zh, slot_label_zh, option_label_zh,
                        pi_delta, unit, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        item.get("category_label_zh"),
                        item.get("slot_label_zh"),
                        item.get("option_label_zh"),
                        item.get("pi_delta"),
                        item.get("unit"),
                        item.get("sort_order", idx),
                    ),
                )

    def freeze_tune_values(self, snapshot_id: str, values: list[dict[str, Any]]) -> None:
        with transaction(self.db_path) as conn:
            conn.execute("DELETE FROM snapshot_tune_values WHERE snapshot_id = ?", (snapshot_id,))
            for idx, val in enumerate(values):
                conn.execute(
                    """
                    INSERT INTO snapshot_tune_values (
                        snapshot_id, section_label_zh, parameter_label_zh,
                        value, unit, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        val.get("section_label_zh"),
                        val.get("parameter_label_zh"),
                        val.get("value"),
                        val.get("unit"),
                        val.get("sort_order", idx),
                    ),
                )

    def freeze_vehicle_data(self, snapshot_id: str, data: list[dict[str, Any]]) -> None:
        with transaction(self.db_path) as conn:
            conn.execute("DELETE FROM snapshot_vehicle_data WHERE snapshot_id = ?", (snapshot_id,))
            for idx, item in enumerate(data):
                conn.execute(
                    """
                    INSERT INTO snapshot_vehicle_data (
                        snapshot_id, data_key, label_zh, value, unit, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        item.get("data_key", ""),
                        item.get("label_zh"),
                        str(item.get("value", "")),
                        item.get("unit"),
                        item.get("sort_order", idx),
                    ),
                )

    def get_build_items(self, snapshot_id: str) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM snapshot_build_items WHERE snapshot_id = ? ORDER BY sort_order",
                (snapshot_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_tune_values(self, snapshot_id: str) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM snapshot_tune_values WHERE snapshot_id = ? ORDER BY sort_order",
                (snapshot_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_vehicle_data(self, snapshot_id: str) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM snapshot_vehicle_data WHERE snapshot_id = ? ORDER BY sort_order",
                (snapshot_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def build_frozen_summary_json(self, snapshot_id: str) -> str:
        """Generate optional frozen_summary_json from freeze tables."""
        summary = {
            "build_items": self.get_build_items(snapshot_id),
            "tune_values": self.get_tune_values(snapshot_id),
            "vehicle_data": self.get_vehicle_data(snapshot_id),
        }
        return json.dumps(summary, ensure_ascii=False)
