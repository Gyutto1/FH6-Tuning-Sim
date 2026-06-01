from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.setup_snapshot_repository import SetupSnapshotRepository
from fh6_tuning_sim.db.repositories.utils import active_flag, require_text, utc_now


class RunRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ? OR session_id = ?", (run_id, run_id)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_run(self, data: dict[str, Any], intent_tag_ids: list[str] | None = None) -> dict[str, Any]:
        car_id = require_text(data.get("car_id"), "car_id")
        build_id = require_text(data.get("build_id"), "build_id")
        tune_id = require_text(data.get("tune_id"), "tune_id")
        setup_snapshot_id = require_text(data.get("setup_snapshot_id"), "setup_snapshot_id")
        route_mode = require_text(data.get("route_mode"), "route_mode")
        record_type = require_text(data.get("record_type"), "record_type")
        intent_tag_ids = list(intent_tag_ids or [])
        if not SetupSnapshotRepository(self.db_path).validate_context(car_id, build_id, tune_id, setup_snapshot_id):
            raise ValueError("run context does not match setup snapshot")

        session_id = require_text(data.get("session_id"), "session_id")
        run_id = str(data.get("run_id") or session_id)
        now = utc_now()
        with transaction(self.db_path) as conn:
            for tag_id in intent_tag_ids:
                if not conn.execute("SELECT 1 FROM tags WHERE tag_id = ?", (tag_id,)).fetchone():
                    raise ValueError(f"tag not found: {tag_id}")
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, session_id, car_id, build_id, tune_id, setup_snapshot_id, route_id,
                    route_mode, record_type, use_case, raw_csv_path, processed_csv_path, plot_path,
                    report_path, dataset_path, metadata_path, tune_snapshot_path, duration_seconds,
                    packet_count, estimated_sample_rate, quality_status, quality_warnings,
                    metrics_json, notes, review_notes, status, is_active, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    session_id,
                    car_id,
                    build_id,
                    tune_id,
                    setup_snapshot_id,
                    data.get("route_id"),
                    route_mode,
                    record_type,
                    data.get("use_case"),
                    data.get("raw_csv_path"),
                    data.get("processed_csv_path"),
                    data.get("plot_path"),
                    data.get("report_path"),
                    data.get("dataset_path"),
                    data.get("metadata_path"),
                    data.get("tune_snapshot_path"),
                    data.get("duration_seconds"),
                    data.get("packet_count"),
                    data.get("estimated_sample_rate"),
                    data.get("quality_status") or "draft",
                    data.get("quality_warnings") or "[]",
                    data.get("metrics_json") or "{}",
                    data.get("notes") or "",
                    data.get("review_notes") or "",
                    data.get("status") or "active",
                    active_flag(data.get("is_active", True)),
                    data.get("created_at_utc") or now,
                    now,
                ),
            )
            for tag_id in sorted(set(intent_tag_ids)):
                conn.execute(
                    "INSERT INTO run_tags (run_id, tag_id, tag_role, created_at_utc) VALUES (?, ?, 'intent', ?)",
                    (run_id, tag_id, now),
                )
        created = self.get_run(run_id)
        if created is None:
            raise RuntimeError("run insert failed")
        return created

    def update_run_notes(self, run_id: str, notes: str) -> bool:
        with transaction(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE runs SET notes = ?, updated_at_utc = ? WHERE run_id = ? OR session_id = ?",
                (notes, utc_now(), run_id, run_id),
            )
            return cur.rowcount > 0

    def update_run_metrics(self, run_id: str, metrics_json: str, packet_count: int | None = None) -> bool:
        with transaction(self.db_path) as conn:
            if packet_count is None:
                cur = conn.execute(
                    "UPDATE runs SET metrics_json = ?, updated_at_utc = ? WHERE run_id = ? OR session_id = ?",
                    (metrics_json, utc_now(), run_id, run_id),
                )
            else:
                cur = conn.execute(
                    "UPDATE runs SET metrics_json = ?, packet_count = ?, updated_at_utc = ? WHERE run_id = ? OR session_id = ?",
                    (metrics_json, packet_count, utc_now(), run_id, run_id),
                )
            return cur.rowcount > 0

    def archive_run(self, run_id: str) -> bool:
        with transaction(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE runs SET status = 'archived', is_active = 0, updated_at_utc = ? WHERE run_id = ? OR session_id = ?",
                (utc_now(), run_id, run_id),
            )
            return cur.rowcount > 0

    def add_tag_to_run(self, run_id: str, tag_id: str, tag_role: str = "intent") -> bool:
        now = utc_now()
        with transaction(self.db_path) as conn:
            real_run_id = self._resolve_run_id(conn, run_id)
            if not real_run_id:
                return False
            if not conn.execute("SELECT 1 FROM tags WHERE tag_id = ?", (tag_id,)).fetchone():
                raise ValueError(f"tag not found: {tag_id}")
            conn.execute(
                "INSERT OR IGNORE INTO run_tags (run_id, tag_id, tag_role, created_at_utc) VALUES (?, ?, ?, ?)",
                (real_run_id, tag_id, tag_role, now),
            )
            return True

    def remove_tag_from_run(self, run_id: str, tag_id: str, tag_role: str = "intent") -> bool:
        with transaction(self.db_path) as conn:
            real_run_id = self._resolve_run_id(conn, run_id)
            if not real_run_id:
                return False
            cur = conn.execute(
                "DELETE FROM run_tags WHERE run_id = ? AND tag_id = ? AND tag_role = ?",
                (real_run_id, tag_id, tag_role),
            )
            return cur.rowcount > 0

    def query_run_records(
        self,
        *,
        car_id: str = "",
        build_id: str = "",
        tune_id: str = "",
        setup_snapshot_id: str = "",
        route_id: str = "",
        route_mode: str = "",
        record_type: str = "",
        tag_id: str = "",
        keyword: str = "",
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            sql = """
                SELECT
                    r.*,
                    c.display_name AS car_name,
                    b.display_name AS build_name,
                    t.display_name AS tune_name,
                    ss.snapshot_name AS setup_snapshot_name, ss.confirmed_pi, ss.confirmed_class,
                    routes.display_name AS route_name
                FROM runs r
                JOIN cars c ON c.car_id = r.car_id
                JOIN builds b ON b.build_id = r.build_id
                JOIN tunes t ON t.tune_id = r.tune_id
                JOIN setup_snapshots ss ON ss.setup_snapshot_id = r.setup_snapshot_id
                LEFT JOIN routes ON routes.route_id = r.route_id
                WHERE 1=1
            """
            params: list[Any] = []
            filters = {
                "r.car_id": car_id,
                "r.build_id": build_id,
                "r.tune_id": tune_id,
                "r.setup_snapshot_id": setup_snapshot_id,
                "r.route_id": route_id,
                "r.route_mode": route_mode,
                "r.record_type": record_type,
            }
            for column, value in filters.items():
                if value:
                    sql += f" AND {column} = ?"
                    params.append(value)
            if not include_archived:
                sql += " AND r.is_active = 1 AND r.status != 'archived'"
            if tag_id:
                sql += " AND EXISTS (SELECT 1 FROM run_tags rt WHERE rt.run_id = r.run_id AND rt.tag_id = ?)"
                params.append(tag_id)
            sql += " ORDER BY r.created_at_utc DESC"
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
            tag_map = self._tags_for_runs(conn, [str(row["run_id"]) for row in rows])
            records: list[dict[str, Any]] = []
            for row in rows:
                tag_items = tag_map.get(str(row["run_id"]), [])
                tag_keys = [item["tag_key"] for item in tag_items]
                tag_labels = [item["label_zh"] for item in tag_items]
                display_title = f"{row.get('car_name') or '未知车辆'} · {row.get('route_name') or '未设置'} · {row.get('record_type') or 'unknown'}"
                search_text = " ".join(
                    str(part)
                    for part in [
                        display_title,
                        row.get("session_id"),
                        row.get("car_name"),
                        row.get("build_name"),
                        row.get("tune_name"),
                        row.get("setup_snapshot_name"),
                        row.get("route_name"),
                        " ".join(tag_keys),
                        " ".join(tag_labels),
                        row.get("notes"),
                    ]
                    if part
                )
                record = {
                    "run_id": row.get("run_id"),
                    "session_id": row.get("session_id"),
                    "display_title": display_title,
                    "car_id": row.get("car_id"),
                    "car_name": row.get("car_name"),
                    "build_id": row.get("build_id"),
                    "build_name": row.get("build_name"),
                    "tune_id": row.get("tune_id"),
                    "tune_name": row.get("tune_name"),
                    "setup_snapshot_id": row.get("setup_snapshot_id"),
                    "setup_snapshot_name": row.get("setup_snapshot_name"),
                    "confirmed_pi": row.get("confirmed_pi"),
                    "confirmed_class": row.get("confirmed_class"),
                    "route_id": row.get("route_id"),
                    "route_name": row.get("route_name") or "未设置",
                    "route_mode": row.get("route_mode"),
                    "record_type": row.get("record_type"),
                    "record_type_label": row.get("record_type"),
                    "raw_csv_path": row.get("raw_csv_path") or "",
                    "processed_csv_path": row.get("processed_csv_path") or "",
                    "tag_keys": tag_keys,
                    "tag_labels": tag_labels,
                    "tag_ids": [item["tag_id"] for item in tag_items],
                    "tag_items": tag_items,
                    "quality_status": row.get("quality_status"),
                    "metrics_json": row.get("metrics_json") or "{}",
                    "duration_seconds": float(row.get("duration_seconds") or 0),
                    "created_at": row.get("created_at_utc"),
                    "notes": row.get("notes") or "",
                    "search_text": search_text,
                    "status": row.get("status"),
                    "is_active": bool(row.get("is_active")),
                }
                records.append(record)
            if keyword:
                kw = keyword.lower()
                records = [record for record in records if kw in str(record.get("search_text", "")).lower()]
            return records
        finally:
            conn.close()

    @staticmethod
    def _resolve_run_id(conn, run_id: str) -> str | None:
        row = conn.execute("SELECT run_id FROM runs WHERE run_id = ? OR session_id = ?", (run_id, run_id)).fetchone()
        return str(row["run_id"]) if row else None

    @staticmethod
    def _tags_for_runs(conn, run_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not run_ids:
            return {}
        placeholders = ",".join(["?"] * len(run_ids))
        rows = conn.execute(
            f"""
            SELECT rt.run_id, t.tag_id, t.tag_key, t.category, t.label_zh
            FROM run_tags rt
            JOIN tags t ON t.tag_id = rt.tag_id
            WHERE rt.run_id IN ({placeholders})
            ORDER BY t.category, t.display_order, t.tag_key
            """,
            run_ids,
        ).fetchall()
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            item = dict(row)
            result.setdefault(str(item.pop("run_id")), []).append(item)
        return result
