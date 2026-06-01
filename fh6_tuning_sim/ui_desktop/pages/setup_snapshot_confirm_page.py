from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QComboBox, QDialog, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QScrollArea,
    QVBoxLayout, QWidget, QMessageBox, QPushButton,
)

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.i18n.snapshot_labels import VEHICLE_DATA_FIELDS
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


class SetupSnapshotConfirmPage(QDialog):
    """Full Setup Snapshot confirmation with Vehicle Data Panel (table layout)."""

    def __init__(
        self,
        data_service: DesktopDataService,
        car_id: str,
        build_id: str,
        tune_id: str,
        snapshot_id: str | None = None,
        on_confirmed: callable | None = None,
        parent: QWidget | None = None,
        embedded: bool = False,
    ) -> None:
        super().__init__(parent)
        self._data = data_service
        self._car_id = car_id
        self._build_id = build_id
        self._tune_id = tune_id
        self._snapshot_id = snapshot_id
        self._on_confirmed = on_confirmed
        self._embedded = embedded
        self._vehicle_fields: dict[str, QLineEdit] = {}
        self._confirmed = False
        self.setWindowTitle("确认 Setup Snapshot")
        if embedded:
            self.setWindowFlags(Qt.Widget)
            self.setMinimumSize(0, 0)
        else:
            self.setMinimumSize(620, 760)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")

        content = QWidget()
        content.setStyleSheet("background: #ffffff;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        car = self._data.get_car(self._car_id)
        build = self._data.builds.get_build(self._build_id)
        tune = self._data.tunes.get_tune(self._tune_id)
        snapshot = self._data.snapshots.get_snapshot(self._snapshot_id) if self._snapshot_id else None

        layout.addWidget(SectionHeader("Setup Snapshot 确认", "确认并冻结当前 Build + Tune + Vehicle Data"))

        # Summary
        summary = QGroupBox("当前配置")
        sf = QVBoxLayout(summary)
        sf.addWidget(QLabel(f"车辆: {car.get('display_name', '-') if car else '-'}"))
        sf.addWidget(QLabel(f"Build: {build.get('display_name', '-') if build else '-'}"))
        sf.addWidget(QLabel(f"Tune: {tune.get('display_name', '-') if tune else '-'}"))
        if build:
            sf.addWidget(QLabel(f"Build PI/Class: {build.get('pi') or '未设置'} / {build.get('car_class') or '未设置'}"))
        layout.addWidget(summary)

        # PI / Class confirm
        pi_box = QGroupBox("确认 PI / Class")
        pi_row = QHBoxLayout(pi_box)
        pi_row.addWidget(QLabel("PI:"))
        pi_value = (snapshot or {}).get("pi") or ""
        self._pi_edit = QLineEdit(str(pi_value))
        self._pi_edit.setPlaceholderText("手动输入 PI")
        self._pi_edit.setMaximumWidth(120)
        pi_row.addWidget(self._pi_edit)
        pi_row.addWidget(QLabel("Class:"))
        self._class_combo = QComboBox()
        self._class_combo.addItems(["D", "C", "B", "A", "S1", "S2", "X", "unknown"])
        cls = (snapshot or {}).get("car_class") or "unknown"
        if cls in ["D", "C", "B", "A", "S1", "S2", "X", "unknown"]:
            self._class_combo.setCurrentText(cls)
        self._class_combo.setMaximumWidth(120)
        pi_row.addWidget(self._class_combo)
        pi_row.addStretch()
        layout.addWidget(pi_box)

        build_box = QGroupBox("Build 选择项")
        build_layout = QVBoxLayout(build_box)
        selections = self._data.builds.list_upgrade_selections(self._build_id)
        selected_slot_ids = {str(item.get("slot_id") or "") for item in selections if item.get("slot_id")}
        if selections:
            for item in selections:
                build_layout.addWidget(QLabel(
                    f"{item.get('category_label', '')} / {item.get('slot_label_zh', '')}: {item.get('option_label', '未设置')}"
                ))
        else:
            build_layout.addWidget(QLabel("暂无升级选择。"))

        missing_lines: list[str] = []
        missing_by_category: dict[str, int] = {}
        for category in self._data.get_upgrade_categories(self._build_id):
            category_id = str(category.get("upgrade_category_id") or "")
            category_label = category.get("label_zh") or category.get("label_en") or "分类"
            for slot in self._data.get_upgrade_slots_for_category(category_id, self._build_id):
                slot_id = str(slot.get("slot_id") or "")
                option_count = int(slot.get("option_count") or 0)
                if not slot_id or slot_id in selected_slot_ids:
                    continue
                if option_count <= 0:
                    continue
                slot_label = slot.get("label_zh") or slot.get("label_en") or "槽位"
                missing_lines.append(f"{category_label} / {slot_label}")
                missing_by_category[category_label] = missing_by_category.get(category_label, 0) + 1
        if missing_lines:
            build_layout.addWidget(QLabel(f"未选择槽位：共 {len(missing_lines)} 个"))
            for cat, count in sorted(missing_by_category.items(), key=lambda x: x[0]):
                build_layout.addWidget(QLabel(f" - {cat}: {count} 个"))
            build_layout.addWidget(QLabel("未选择槽位明细："))
            for line in missing_lines:
                build_layout.addWidget(QLabel(f" - {line}"))
        layout.addWidget(build_box)

        tune_box = QGroupBox("Tune 参数值")
        tune_layout = QVBoxLayout(tune_box)
        for item in self._data.tune_parameters.list_values(self._tune_id):
            value = item.get("value_real")
            if value is None:
                value = item.get("default_value")
            if value is None:
                value = item.get("min_value")
            tune_layout.addWidget(QLabel(
                f"{item.get('section_label_zh') or item.get('category') or ''} / {item.get('label_zh', '')}: {value} {item.get('unit') or ''}".strip()
            ))
        layout.addWidget(tune_box)

        # Vehicle Data Panel - table layout with fixed unit column
        vd_box = QGroupBox("车辆数据面板 Vehicle Data Panel")
        vd_grid = QGridLayout(vd_box)
        vd_grid.setSpacing(6)
        vd_grid.setContentsMargins(12, 16, 12, 12)
        # Header row
        hdr_style = "font-size: 12px; font-weight: 600; color: #888888;"
        vd_grid.addWidget(QLabel("项目"), 0, 0)
        vd_grid.addWidget(QLabel("数值"), 0, 1)
        vd_grid.addWidget(QLabel("单位"), 0, 2)
        for i, (lbl_zh, unit, dk) in enumerate(VEHICLE_DATA_FIELDS, start=1):
            name_lbl = QLabel(lbl_zh)
            name_lbl.setStyleSheet("font-size: 13px; color: #333333;")
            vd_grid.addWidget(name_lbl, i, 0)
            edit = QLineEdit()
            edit.setStyleSheet(
                "QLineEdit { background: #ffffff; color: #111111; border: 1px solid #cccccc; "
                "border-radius: 4px; padding: 4px 8px; font-size: 13px; min-width: 120px; }"
            )
            self._vehicle_fields[dk] = edit
            vd_grid.addWidget(edit, i, 1)
            unit_lbl = QLabel(unit)
            unit_lbl.setStyleSheet("font-size: 13px; color: #888888;")
            vd_grid.addWidget(unit_lbl, i, 2)
        if self._snapshot_id:
            try:
                for item in self._data._freeze.get_vehicle_data(self._snapshot_id):
                    key = str(item.get("data_key") or "")
                    if key in self._vehicle_fields:
                        self._vehicle_fields[key].setText(str(item.get("value") or ""))
            except Exception:
                pass
        layout.addWidget(vd_box)

        # Notes
        notes_box = QGroupBox("备注")
        notes_form = QVBoxLayout(notes_box)
        self._notes_edit = QLineEdit()
        self._notes_edit.setPlaceholderText("Snapshot 备注（可选）")
        notes_form.addWidget(self._notes_edit)
        layout.addWidget(notes_box)

        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # Fixed bottom button bar (outside scroll)
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background: #fafafa; border-top: 1px solid #e0e0e0;")
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(24, 12, 24, 12)
        btn_layout.addStretch()
        confirm_btn = QPushButton("确认并冻结 Snapshot")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(
            "QPushButton { background: #2f6f65; color: white; border: none; "
            "border-radius: 6px; padding: 10px 28px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #255b53; }"
        )
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)
        if not self._embedded:
            cancel_btn = QPushButton("取消")
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.setStyleSheet(
                "QPushButton { background: #ffffff; color: #555555; border: 1px solid #d5d5d5; "
                "border-radius: 6px; padding: 10px 24px; }"
            )
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)
        root.addWidget(btn_widget)

    def _on_confirm(self) -> None:
        missing_labels = self._missing_vehicle_data_labels()
        if missing_labels:
            preview = "、".join(missing_labels[:8])
            suffix = "..." if len(missing_labels) > 8 else ""
            QMessageBox.warning(
                self,
                "车辆数据未完成",
                f"请补齐车辆数据面板所有字段后再保存。\n缺少 {len(missing_labels)} 项：{preview}{suffix}",
            )
            return

        try:
            pi = int(self._pi_edit.text()) if self._pi_edit.text().strip() else None
        except ValueError:
            pi = None

        if not self._snapshot_id:
            snap = self._data.snapshots.ensure_default_setup_snapshot(
                self._car_id, self._build_id, self._tune_id
            )
            self._snapshot_id = snap["setup_snapshot_id"]

        if pi is not None:
            self._data.snapshots.update_snapshot(self._snapshot_id, {"pi": pi})
        cls_val = self._class_combo.currentText()
        if cls_val:
            self._data.snapshots.update_snapshot(self._snapshot_id, {"car_class": cls_val})
        notes = self._notes_edit.text().strip()
        if notes:
            self._data.snapshots.update_snapshot(self._snapshot_id, {"notes": notes})

        ok = self._data.confirm_setup_snapshot(self._snapshot_id, self._collect_vehicle_data())
        if ok:
            self._confirmed = True
            if self._on_confirmed:
                self._on_confirmed(self._snapshot_id)
            if not self._embedded:
                self.accept()
        else:
            QMessageBox.warning(self, "error", "Snapshot confirm failed")

    def _missing_vehicle_data_labels(self) -> list[str]:
        missing: list[str] = []
        for lbl_zh, _unit, dk in VEHICLE_DATA_FIELDS:
            field = self._vehicle_fields.get(dk)
            if field is None or not field.text().strip():
                missing.append(lbl_zh)
        return missing

    def _collect_vehicle_data(self) -> list[dict[str, str]]:
        vehicle_data: list[dict[str, str]] = []
        for lbl_zh, unit, dk in VEHICLE_DATA_FIELDS:
            val = self._vehicle_fields[dk].text().strip()
            vehicle_data.append({"data_key": dk, "label_zh": lbl_zh, "value": val, "unit": unit})
        return vehicle_data

    @property
    def confirmed_snapshot_id(self) -> str | None:
        return self._snapshot_id if self._confirmed else None
