from __future__ import annotations

import json
from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SetupSnapshotEditDialog(QDialog):
    def __init__(self, snapshot: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("确认 Setup Snapshot")
        self._snapshot = snapshot
        self._fields: dict[str, QLineEdit] = {}
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        for title, keys in [
            ("基础", ["snapshot_name", "pi", "car_class", "drivetrain"]),
            ("动力", ["power", "torque"]),
            ("重量", ["weight", "front_weight_percent"]),
            ("轮胎", ["tire_compound"]),
        ]:
            layout.addWidget(self._group(title, keys))

        ratings = self._ratings()
        rating_box = QGroupBox("性能评分")
        rating_form = QFormLayout(rating_box)
        for key in ["speed", "handling", "acceleration", "launch", "braking", "offroad"]:
            edit = QLineEdit("" if ratings.get(key) is None else str(ratings.get(key)))
            self._fields[f"rating_{key}"] = edit
            rating_form.addRow(key, edit)
        layout.addWidget(rating_box)

        notes_box = QGroupBox("来源 / 备注")
        notes_form = QFormLayout(notes_box)
        self._fields["source"] = QLineEdit(str(self._snapshot.get("source") or "manual"))
        self._notes = QTextEdit(str(self._snapshot.get("notes") or ""))
        self._notes.setMaximumHeight(90)
        notes_form.addRow("source", self._fields["source"])
        notes_form.addRow("notes", self._notes)
        layout.addWidget(notes_box)

        scroll.setWidget(content)
        root.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.resize(460, 620)

    def _group(self, title: str, keys: list[str]) -> QGroupBox:
        box = QGroupBox(title)
        form = QFormLayout(box)
        labels = {
            "snapshot_name": "名称",
            "pi": "PI",
            "car_class": "Class",
            "drivetrain": "Drivetrain",
            "power": "Power",
            "torque": "Torque",
            "weight": "Weight",
            "front_weight_percent": "Front Weight %",
            "tire_compound": "Tire Compound",
        }
        for key in keys:
            edit = QLineEdit("" if self._snapshot.get(key) is None else str(self._snapshot.get(key)))
            self._fields[key] = edit
            form.addRow(labels.get(key, key), edit)
        return box

    def result_data(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        int_fields = {"pi"}
        float_fields = {"power", "torque", "weight", "front_weight_percent"}
        for key, edit in self._fields.items():
            if key.startswith("rating_"):
                continue
            text = edit.text().strip()
            if key in int_fields:
                result[key] = int(text) if text else None
            elif key in float_fields:
                result[key] = float(text) if text else None
            else:
                result[key] = text
        result["notes"] = self._notes.toPlainText().strip()
        ratings: dict[str, float | None] = {}
        for key in ["speed", "handling", "acceleration", "launch", "braking", "offroad"]:
            text = self._fields[f"rating_{key}"].text().strip()
            ratings[key] = float(text) if text else None
        result["performance_ratings"] = ratings
        return result

    def _ratings(self) -> dict[str, Any]:
        raw = self._snapshot.get("performance_ratings")
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}
