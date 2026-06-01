from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService


class CarUpgradeCatalogDialog(QDialog):
    """Per-car upgrade catalog manager: category -> slot -> option."""

    def __init__(self, data_service: DesktopDataService, car_id: str, parent=None) -> None:
        super().__init__(parent)
        self._data = data_service
        self._car_id = car_id
        self._selected_category_id = ""
        self._selected_slot_id = ""
        self.setWindowTitle("车型升级目录管理")
        self.setMinimumSize(920, 640)
        self._build()
        self._refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        hint = QLabel("说明：可新增分类/槽位/选项；删除采用“按当前车型隐藏”，不会全局硬删。")
        hint.setStyleSheet("font-size: 12px; color: #555555;")
        root.addWidget(hint)

        grid = QGridLayout()
        grid.setSpacing(12)
        root.addLayout(grid, 1)

        self._category_frame = QFrame()
        self._category_layout = QVBoxLayout(self._category_frame)
        self._category_layout.setContentsMargins(8, 8, 8, 8)
        self._category_layout.setSpacing(8)
        grid.addWidget(self._category_frame, 0, 0)

        self._slot_frame = QFrame()
        self._slot_layout = QVBoxLayout(self._slot_frame)
        self._slot_layout.setContentsMargins(8, 8, 8, 8)
        self._slot_layout.setSpacing(8)
        grid.addWidget(self._slot_frame, 0, 1)

        self._option_frame = QFrame()
        self._option_layout = QVBoxLayout(self._option_frame)
        self._option_layout.setContentsMargins(8, 8, 8, 8)
        self._option_layout.setSpacing(8)
        grid.addWidget(self._option_frame, 0, 2)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

    def _refresh(self) -> None:
        self._refresh_categories()
        self._refresh_slots()
        self._refresh_options()

    def _refresh_categories(self) -> None:
        self._clear_layout(self._category_layout)
        self._category_layout.addWidget(QLabel("升级分类"))

        tools = QHBoxLayout()
        add_btn = QPushButton("+ 新增分类")
        add_btn.clicked.connect(self._add_category)
        tools.addWidget(add_btn)
        tools.addStretch()
        self._category_layout.addLayout(tools)

        categories = self._data.get_upgrade_categories_for_car(self._car_id)
        for cat in categories:
            cid = str(cat.get("upgrade_category_id") or "")
            is_on = bool(cat.get("is_available_for_car", 1))
            title = str(cat.get("label_zh") or "")
            if not is_on:
                title = f"{title}（已隐藏）"

            row = QHBoxLayout()
            pick = QPushButton(title)
            pick.setCheckable(True)
            pick.setChecked(cid == self._selected_category_id)
            pick.clicked.connect(lambda checked=False, x=cid: self._select_category(x))
            row.addWidget(pick, 1)

            toggle = QPushButton("隐藏" if is_on else "显示")
            toggle.clicked.connect(lambda checked=False, x=cid, v=is_on: self._toggle_category(x, v))
            row.addWidget(toggle)
            self._category_layout.addLayout(row)

        self._category_layout.addStretch()
        if not self._selected_category_id and categories:
            self._selected_category_id = str(categories[0].get("upgrade_category_id") or "")

    def _refresh_slots(self) -> None:
        self._clear_layout(self._slot_layout)
        self._slot_layout.addWidget(QLabel("槽位"))
        if not self._selected_category_id:
            self._slot_layout.addWidget(QLabel("请先选择分类"))
            return

        tools = QHBoxLayout()
        add_btn = QPushButton("+ 新增槽位")
        add_btn.clicked.connect(self._add_slot)
        tools.addWidget(add_btn)
        tools.addStretch()
        self._slot_layout.addLayout(tools)

        slots = self._data.get_upgrade_slots_for_car(self._car_id, self._selected_category_id)
        for slot in slots:
            sid = str(slot.get("slot_id") or "")
            is_on = bool(slot.get("is_available_for_car", 1))
            title = str(slot.get("label_zh") or "")
            if not is_on:
                title = f"{title}（已隐藏）"

            row = QHBoxLayout()
            pick = QPushButton(title)
            pick.setCheckable(True)
            pick.setChecked(sid == self._selected_slot_id)
            pick.clicked.connect(lambda checked=False, x=sid: self._select_slot(x))
            row.addWidget(pick, 1)

            toggle = QPushButton("隐藏" if is_on else "显示")
            toggle.clicked.connect(lambda checked=False, x=sid, v=is_on: self._toggle_slot(x, v))
            row.addWidget(toggle)
            self._slot_layout.addLayout(row)

        self._slot_layout.addStretch()
        if not self._selected_slot_id and slots:
            self._selected_slot_id = str(slots[0].get("slot_id") or "")

    def _refresh_options(self) -> None:
        self._clear_layout(self._option_layout)
        self._option_layout.addWidget(QLabel("选项"))
        if not self._selected_slot_id:
            self._option_layout.addWidget(QLabel("请先选择槽位"))
            return

        tools = QHBoxLayout()
        add_btn = QPushButton("+ 新增选项")
        add_btn.clicked.connect(self._add_option)
        tools.addWidget(add_btn)
        tools.addStretch()
        self._option_layout.addLayout(tools)

        options = self._data.get_upgrade_options_for_car(self._car_id, self._selected_slot_id)
        for opt in options:
            oid = str(opt.get("upgrade_option_id") or "")
            is_on = bool(opt.get("is_available_for_car", 1))
            title = str(opt.get("display_label_zh") or opt.get("label_zh") or "")
            if not is_on:
                title = f"{title}（已隐藏）"

            row = QHBoxLayout()
            row.addWidget(QLabel(title), 1)
            toggle = QPushButton("隐藏" if is_on else "显示")
            toggle.clicked.connect(lambda checked=False, x=oid, v=is_on: self._toggle_option(x, v))
            row.addWidget(toggle)
            self._option_layout.addLayout(row)

        self._option_layout.addStretch()

    def _select_category(self, category_id: str) -> None:
        self._selected_category_id = category_id
        self._selected_slot_id = ""
        self._refresh()

    def _select_slot(self, slot_id: str) -> None:
        self._selected_slot_id = slot_id
        self._refresh_options()

    def _add_category(self) -> None:
        categories = self._data.get_upgrade_categories_for_car(self._car_id)
        labels = [str(c.get("label_zh") or "") for c in categories if c.get("label_zh")]
        choice, ok = QInputDialog.getItem(self, "添加分类", "优先选择已有中文分类：", labels + ["<新建分类>"], 0, False)
        if not ok:
            return
        if choice and choice != "<新建分类>":
            picked = next((c for c in categories if str(c.get("label_zh") or "") == choice), None)
            if picked:
                self._data.set_car_upgrade_category_available(self._car_id, str(picked.get("upgrade_category_id") or ""), True)
                self._selected_category_id = str(picked.get("upgrade_category_id") or "")
                self._refresh()
            return
        label, ok = QInputDialog.getText(self, "新增分类", "中文名称:")
        if not ok or not label.strip():
            return
        key = self._normalize_key(label)
        try:
            self._data.add_upgrade_category(key, label.strip())
        except Exception as exc:
            QMessageBox.warning(self, "新增失败", f"分类创建失败: {self._friendly_error(exc)}")
            return
        self._selected_category_id = ""
        self._refresh()

    def _add_slot(self) -> None:
        if not self._selected_category_id:
            return
        slots = self._data.get_upgrade_slots_for_car(self._car_id, self._selected_category_id)
        labels = [str(s.get("label_zh") or "") for s in slots if s.get("label_zh")]
        choice, ok = QInputDialog.getItem(self, "添加槽位", "优先选择已有中文槽位：", labels + ["<新建槽位>"], 0, False)
        if not ok:
            return
        if choice and choice != "<新建槽位>":
            picked = next((s for s in slots if str(s.get("label_zh") or "") == choice), None)
            if picked:
                self._data.set_car_upgrade_slot_available(self._car_id, str(picked.get("slot_id") or ""), True)
                self._selected_slot_id = str(picked.get("slot_id") or "")
                self._refresh_slots()
                self._refresh_options()
            return
        label, ok = QInputDialog.getText(self, "新增槽位", "中文名称:")
        if not ok or not label.strip():
            return
        key = self._normalize_key(label)
        try:
            self._data.add_upgrade_slot(self._selected_category_id, key, label.strip())
        except Exception as exc:
            QMessageBox.warning(self, "新增失败", f"槽位创建失败: {self._friendly_error(exc)}")
            return
        self._selected_slot_id = ""
        self._refresh_slots()
        self._refresh_options()

    def _add_option(self) -> None:
        if not self._selected_category_id or not self._selected_slot_id:
            return
        options = self._data.get_upgrade_options_for_car(self._car_id, self._selected_slot_id)
        labels = [str(o.get("display_label_zh") or o.get("label_zh") or "") for o in options]
        choice, ok = QInputDialog.getItem(self, "添加选项", "优先选择已有中文选项：", labels + ["<新建选项>"], 0, False)
        if not ok:
            return
        if choice and choice != "<新建选项>":
            picked = next((o for o in options if str(o.get("display_label_zh") or o.get("label_zh") or "") == choice), None)
            if picked:
                self._data.set_car_upgrade_option_available(self._car_id, str(picked.get("upgrade_option_id") or ""), True)
                self._refresh_options()
            return
        label, ok = QInputDialog.getText(self, "新增选项", "中文名称:")
        if not ok or not label.strip():
            return
        key = self._normalize_key(label)
        try:
            self._data.add_upgrade_option(
                upgrade_category_id=self._selected_category_id,
                slot_id=self._selected_slot_id,
                option_key=key,
                label_zh=label.strip(),
            )
        except Exception as exc:
            QMessageBox.warning(self, "新增失败", f"选项创建失败: {self._friendly_error(exc)}")
            return
        self._refresh_options()

    def _toggle_category(self, category_id: str, current_on: bool) -> None:
        self._data.set_car_upgrade_category_available(self._car_id, category_id, not current_on)
        self._selected_category_id = ""
        self._selected_slot_id = ""
        self._refresh()

    def _toggle_slot(self, slot_id: str, current_on: bool) -> None:
        self._data.set_car_upgrade_slot_available(self._car_id, slot_id, not current_on)
        self._selected_slot_id = ""
        self._refresh_slots()
        self._refresh_options()

    def _toggle_option(self, option_id: str, current_on: bool) -> None:
        self._data.set_car_upgrade_option_available(self._car_id, option_id, not current_on)
        self._refresh_options()

    @staticmethod
    def _normalize_key(text: str) -> str:
        key = text.strip().lower().replace(" ", "_").replace("-", "_")
        key = re.sub(r"__+", "_", key)
        return key

    @staticmethod
    def _is_valid_key(text: str) -> bool:
        return bool(re.fullmatch(r"[a-z0-9_]+", text))

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        text = str(exc)
        if "UNIQUE constraint failed" in text:
            return "key 已存在，请使用不同的英文 key。"
        return text

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout:
                while child_layout.count():
                    sub = child_layout.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
            if item.widget():
                item.widget().deleteLater()
