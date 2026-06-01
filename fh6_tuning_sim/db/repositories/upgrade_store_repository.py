from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.db.connection import DEFAULT_DB_PATH, connect, transaction
from fh6_tuning_sim.db.repositories.utils import utc_now


class UpgradeStoreRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def list_categories(self, build_id: str = "") -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT c.*,
                       COUNT(s.slot_id) AS slot_count
                FROM upgrade_categories c
                LEFT JOIN builds b
                    ON b.build_id = ?
                LEFT JOIN car_upgrade_availability cua
                    ON cua.upgrade_category_id = c.upgrade_category_id
                   AND cua.car_id = b.car_id
                   AND cua.slot_id IS NULL
                   AND cua.option_id IS NULL
                LEFT JOIN upgrade_slots s
                    ON s.upgrade_category_id = c.upgrade_category_id
                   AND s.is_active = 1
                WHERE c.is_active = 1
                  AND COALESCE(cua.is_available, 1) = 1
                GROUP BY c.upgrade_category_id
                ORDER BY c.display_order, c.category_key
                """,
                (build_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_slots(self, upgrade_category_id: str, build_id: str = "") -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    s.*,
                    COUNT(o.upgrade_option_id) AS option_count,
                    sel.upgrade_option_id AS selected_option_id,
                    opt.label_zh AS selected_option_label,
                    opt.default_pi_delta AS selected_pi_delta
                FROM upgrade_slots s
                LEFT JOIN upgrade_options o
                    ON o.slot_id = s.slot_id
                   AND o.is_active = 1
                LEFT JOIN build_upgrade_selections sel
                    ON sel.slot_id = s.slot_id
                   AND sel.build_id = ?
                LEFT JOIN upgrade_options opt
                    ON opt.upgrade_option_id = sel.upgrade_option_id
                LEFT JOIN builds b
                    ON b.build_id = ?
                LEFT JOIN car_upgrade_availability cua
                    ON cua.slot_id = s.slot_id
                   AND cua.car_id = b.car_id
                   AND cua.option_id IS NULL
                WHERE s.upgrade_category_id = ?
                  AND s.is_active = 1
                  AND COALESCE(cua.is_available, 1) = 1
                GROUP BY s.slot_id
                ORDER BY s.sort_order, s.slot_key
                """,
                (build_id, build_id, upgrade_category_id),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_options(self, slot_id: str, build_id: str = "") -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    o.*,
                    COALESCE(cua.override_label_zh, o.label_zh) AS display_label_zh,
                    COALESCE(cua.override_label_en, o.label_en) AS display_label_en,
                    COALESCE(cua.override_pi_delta, o.default_pi_delta, o.pi_impact) AS pi_delta,
                    CASE WHEN sel.upgrade_option_id = o.upgrade_option_id THEN 1 ELSE 0 END AS is_selected
                FROM upgrade_options o
                LEFT JOIN build_upgrade_selections sel
                    ON sel.slot_id = o.slot_id
                   AND sel.build_id = ?
                LEFT JOIN builds b
                    ON b.build_id = ?
                LEFT JOIN car_upgrade_availability cua
                    ON cua.option_id = o.upgrade_option_id
                   AND cua.slot_id = o.slot_id
                   AND cua.car_id = b.car_id
                WHERE o.slot_id = ?
                  AND o.is_active = 1
                  AND COALESCE(cua.is_available, 1) = 1
                ORDER BY o.is_stock DESC, o.tier, o.option_key
                """,
                (build_id, build_id, slot_id),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_categories_for_car(self, car_id: str) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    c.*,
                    COUNT(s.slot_id) AS slot_count,
                    COALESCE(cua.is_available, 1) AS is_available_for_car
                FROM upgrade_categories c
                LEFT JOIN car_upgrade_availability cua
                    ON cua.upgrade_category_id = c.upgrade_category_id
                   AND cua.car_id = ?
                   AND cua.slot_id IS NULL
                   AND cua.option_id IS NULL
                LEFT JOIN upgrade_slots s
                    ON s.upgrade_category_id = c.upgrade_category_id
                   AND s.is_active = 1
                WHERE c.is_active = 1
                GROUP BY c.upgrade_category_id
                ORDER BY c.display_order, c.category_key
                """,
                (car_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_slots_for_car(self, car_id: str, upgrade_category_id: str) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    s.*,
                    COUNT(o.upgrade_option_id) AS option_count,
                    COALESCE(cua.is_available, 1) AS is_available_for_car
                FROM upgrade_slots s
                LEFT JOIN car_upgrade_availability cua
                    ON cua.slot_id = s.slot_id
                   AND cua.car_id = ?
                   AND cua.option_id IS NULL
                LEFT JOIN upgrade_options o
                    ON o.slot_id = s.slot_id
                   AND o.is_active = 1
                WHERE s.upgrade_category_id = ?
                  AND s.is_active = 1
                GROUP BY s.slot_id
                ORDER BY s.sort_order, s.slot_key
                """,
                (car_id, upgrade_category_id),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_options_for_car(self, car_id: str, slot_id: str) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    o.*,
                    COALESCE(cua.override_label_zh, o.label_zh) AS display_label_zh,
                    COALESCE(cua.override_label_en, o.label_en) AS display_label_en,
                    COALESCE(cua.override_pi_delta, o.default_pi_delta, o.pi_impact) AS pi_delta,
                    COALESCE(cua.is_available, 1) AS is_available_for_car
                FROM upgrade_options o
                LEFT JOIN car_upgrade_availability cua
                    ON cua.option_id = o.upgrade_option_id
                   AND cua.car_id = ?
                WHERE o.slot_id = ?
                  AND o.is_active = 1
                ORDER BY o.is_stock DESC, o.tier, o.option_key
                """,
                (car_id, slot_id),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_selection(self, build_id: str, slot_id: str) -> dict[str, Any] | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT
                    sel.*,
                    c.label_zh AS category_label,
                    s.label_zh AS slot_label,
                    o.label_zh AS option_label,
                    COALESCE(o.default_pi_delta, o.pi_impact) AS pi_delta
                FROM build_upgrade_selections sel
                JOIN upgrade_categories c ON c.upgrade_category_id = sel.upgrade_category_id
                JOIN upgrade_slots s ON s.slot_id = sel.slot_id
                LEFT JOIN upgrade_options o ON o.upgrade_option_id = sel.upgrade_option_id
                WHERE sel.build_id = ? AND sel.slot_id = ?
                """,
                (build_id, slot_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def save_build_upgrade_selection(self, build_id: str, slot_id: str, option_id: str, notes: str = "") -> dict[str, Any]:
        conn = connect(self.db_path)
        try:
            slot = conn.execute(
                "SELECT slot_id, upgrade_category_id FROM upgrade_slots WHERE slot_id = ? AND is_active = 1",
                (slot_id,),
            ).fetchone()
            if not slot:
                raise ValueError(f"upgrade slot not found: {slot_id}")
            option = conn.execute(
                """
                SELECT upgrade_option_id, slot_id, upgrade_category_id
                FROM upgrade_options
                WHERE upgrade_option_id = ? AND is_active = 1
                """,
                (option_id,),
            ).fetchone()
            if not option:
                raise ValueError(f"upgrade option not found: {option_id}")
            if str(option["slot_id"] or "") != slot_id:
                raise ValueError("upgrade option does not belong to the selected slot")
            if str(option["upgrade_category_id"]) != str(slot["upgrade_category_id"]):
                raise ValueError("upgrade option category does not match selected slot")
            category_id = str(slot["upgrade_category_id"])
        finally:
            conn.close()

        now = utc_now()
        with transaction(self.db_path) as write_conn:
            write_conn.execute(
                """
                INSERT INTO build_upgrade_selections (
                    build_id, slot_id, upgrade_category_id, upgrade_option_id,
                    notes, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(build_id, slot_id) DO UPDATE SET
                    upgrade_category_id = excluded.upgrade_category_id,
                    upgrade_option_id = excluded.upgrade_option_id,
                    notes = excluded.notes,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (build_id, slot_id, category_id, option_id, notes, now, now),
            )
        selection = self.get_selection(build_id, slot_id)
        if selection is None:
            raise RuntimeError("upgrade selection save failed")
        return selection

    def create_category(self, category_key: str, label_zh: str, label_en: str = "", display_order: int = 0) -> dict[str, Any]:
        now_key = utc_now().replace("-", "").replace(":", "").replace("T", "").replace("Z", "")
        category_id = f"cat_{category_key}_{now_key}"
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO upgrade_categories (
                    upgrade_category_id, category_key, label_zh, label_en, display_order, is_active
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (category_id, category_key, label_zh, label_en or None, int(display_order)),
            )
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM upgrade_categories WHERE upgrade_category_id = ?",
                (category_id,),
            ).fetchone()
            if not row:
                raise RuntimeError("category create failed")
            return dict(row)
        finally:
            conn.close()

    def create_slot(
        self,
        upgrade_category_id: str,
        slot_key: str,
        label_zh: str,
        label_en: str = "",
        sort_order: int = 0,
    ) -> dict[str, Any]:
        now_key = utc_now().replace("-", "").replace(":", "").replace("T", "").replace("Z", "")
        slot_id = f"slot_{slot_key}_{now_key}"
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO upgrade_slots (
                    slot_id, upgrade_category_id, slot_key, label_zh, label_en, sort_order, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (slot_id, upgrade_category_id, slot_key, label_zh, label_en or None, int(sort_order)),
            )
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM upgrade_slots WHERE slot_id = ?", (slot_id,)).fetchone()
            if not row:
                raise RuntimeError("slot create failed")
            return dict(row)
        finally:
            conn.close()

    def create_option(
        self,
        upgrade_category_id: str,
        slot_id: str,
        option_key: str,
        label_zh: str,
        label_en: str = "",
        default_pi_delta: int | None = None,
        is_stock: bool = False,
        tier: int = 0,
    ) -> dict[str, Any]:
        now_key = utc_now().replace("-", "").replace(":", "").replace("T", "").replace("Z", "")
        option_id = f"opt_{option_key}_{now_key}"
        with transaction(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO upgrade_options (
                    upgrade_option_id, upgrade_category_id, slot_id, option_key, label_zh, label_en,
                    is_stock, default_pi_delta, tier, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    option_id,
                    upgrade_category_id,
                    slot_id,
                    option_key,
                    label_zh,
                    label_en or None,
                    1 if is_stock else 0,
                    default_pi_delta,
                    int(tier),
                ),
            )
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT * FROM upgrade_options WHERE upgrade_option_id = ?", (option_id,)).fetchone()
            if not row:
                raise RuntimeError("option create failed")
            return dict(row)
        finally:
            conn.close()

    def set_car_category_availability(self, car_id: str, category_id: str, is_available: bool) -> None:
        with transaction(self.db_path) as conn:
            existing = conn.execute(
                """
                SELECT id
                FROM car_upgrade_availability
                WHERE car_id = ?
                  AND upgrade_category_id = ?
                  AND slot_id IS NULL
                  AND option_id IS NULL
                LIMIT 1
                """,
                (car_id, category_id),
            ).fetchone()
            if existing:
                conn.execute("UPDATE car_upgrade_availability SET is_available = ? WHERE id = ?", (1 if is_available else 0, int(existing["id"])))
            else:
                conn.execute(
                    """
                    INSERT INTO car_upgrade_availability (
                        car_id, upgrade_category_id, slot_id, option_id, is_available
                    ) VALUES (?, ?, NULL, NULL, ?)
                    """,
                    (car_id, category_id, 1 if is_available else 0),
                )

    def set_car_slot_availability(self, car_id: str, slot_id: str, is_available: bool) -> None:
        with transaction(self.db_path) as conn:
            slot = conn.execute(
                "SELECT upgrade_category_id FROM upgrade_slots WHERE slot_id = ?",
                (slot_id,),
            ).fetchone()
            if not slot:
                raise ValueError(f"slot not found: {slot_id}")
            existing = conn.execute(
                """
                SELECT id
                FROM car_upgrade_availability
                WHERE car_id = ?
                  AND slot_id = ?
                  AND option_id IS NULL
                LIMIT 1
                """,
                (car_id, slot_id),
            ).fetchone()
            if existing:
                conn.execute("UPDATE car_upgrade_availability SET is_available = ? WHERE id = ?", (1 if is_available else 0, int(existing["id"])))
            else:
                conn.execute(
                    """
                    INSERT INTO car_upgrade_availability (
                        car_id, upgrade_category_id, slot_id, option_id, is_available
                    ) VALUES (?, ?, ?, NULL, ?)
                    """,
                    (car_id, str(slot["upgrade_category_id"]), slot_id, 1 if is_available else 0),
                )

    def set_car_option_availability(self, car_id: str, option_id: str, is_available: bool) -> None:
        with transaction(self.db_path) as conn:
            opt = conn.execute(
                "SELECT upgrade_category_id, slot_id FROM upgrade_options WHERE upgrade_option_id = ?",
                (option_id,),
            ).fetchone()
            if not opt:
                raise ValueError(f"option not found: {option_id}")
            existing = conn.execute(
                """
                SELECT id
                FROM car_upgrade_availability
                WHERE car_id = ?
                  AND option_id = ?
                LIMIT 1
                """,
                (car_id, option_id),
            ).fetchone()
            if existing:
                conn.execute("UPDATE car_upgrade_availability SET is_available = ? WHERE id = ?", (1 if is_available else 0, int(existing["id"])))
            else:
                conn.execute(
                    """
                    INSERT INTO car_upgrade_availability (
                        car_id, upgrade_category_id, slot_id, option_id, is_available
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        car_id,
                        str(opt["upgrade_category_id"]),
                        str(opt["slot_id"] or ""),
                        option_id,
                        1 if is_available else 0,
                    ),
                )
