from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import active_flag, clean_key, require_text, utc_now


class TagRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_by_category(self, category: str | None = None, include_inactive: bool = True) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM tags WHERE 1=1"
            params: list[Any] = []
            if category:
                sql += " AND category = ?"
                params.append(category)
            if not include_inactive:
                sql += " AND is_active = 1"
            sql += " ORDER BY category, display_order, tag_key"
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def get_tag(self, tag_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM tags WHERE tag_id = ?", (tag_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def tag_id_for_key(self, tag_key: str, category: str = "intent_tag") -> str | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT tag_id FROM tags WHERE category = ? AND tag_key = ?",
                (category, tag_key),
            ).fetchone()
            return str(row["tag_id"]) if row else None
        finally:
            conn.close()

    def create_tag(self, category: str, tag_key: str, label_zh: str, *, is_system: bool = False) -> dict[str, Any]:
        category = require_text(category, "category")
        tag_key = str(tag_key or clean_key(label_zh, "tag"))
        label_zh = require_text(label_zh, "label_zh")
        tag_id = f"{category}__{tag_key}"
        now = utc_now()
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tags (
                    tag_id, tag_key, category, label_zh, label_en, description, is_system,
                    is_active, display_order, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, '', ?, 1, 0, ?, ?)
                """,
                (tag_id, tag_key, category, label_zh, tag_key, 1 if is_system else 0, now, now),
            )
        created = self.get_tag(tag_id)
        if created is None:
            raise RuntimeError("tag insert failed")
        return created

    def update_tag(self, tag_id: str, updates: dict[str, Any]) -> bool:
        allowed = {"label_zh", "label_en", "description", "is_active", "display_order"}
        fields = [(key, updates[key]) for key in updates if key in allowed]
        if not fields:
            return False
        set_clause = ", ".join([f"{key} = ?" for key, _ in fields] + ["updated_at_utc = ?"])
        values = [active_flag(value) if key == "is_active" else value for key, value in fields]
        values.extend([utc_now(), tag_id])
        with transaction(self.db_path) as conn:
            cur = conn.execute(f"UPDATE tags SET {set_clause} WHERE tag_id = ?", values)
            return cur.rowcount > 0

    def archive_tag(self, tag_id: str) -> bool:
        return self.update_tag(tag_id, {"is_active": 0})

    def tag_usage_counts(self, tag_id: str) -> dict[str, int]:
        conn = connect(self.db_path)
        try:
            run_count_row = conn.execute("SELECT COUNT(1) AS c FROM run_tags WHERE tag_id = ?", (tag_id,)).fetchone()
            annotation_count_row = conn.execute(
                "SELECT COUNT(1) AS c FROM annotation_tags WHERE tag_id = ?",
                (tag_id,),
            ).fetchone()
            return {
                "run_tags": int(run_count_row["c"]) if run_count_row else 0,
                "annotation_tags": int(annotation_count_row["c"]) if annotation_count_row else 0,
            }
        finally:
            conn.close()
