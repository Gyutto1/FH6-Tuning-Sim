from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CarEditDialog(QDialog):
    """Dialog for editing car basic info: name, PI, drivetrain, status, notes."""

    DRIVETRAIN_OPTIONS = ["FWD", "RWD", "AWD", "unknown"]
    STATUS_OPTIONS = ["active", "archived"]

    def __init__(
        self,
        car_data: dict,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._car_data = dict(car_data)
        self._result: dict | None = None
        self._build()

    def _build(self) -> None:
        self.setWindowTitle("编辑车辆")
        self.setMinimumWidth(420)
        self.setStyleSheet("QDialog { background: #ffffff; } QLabel { color: #111111; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        title = QLabel(f"编辑: {self._car_data.get('display_name', '未命名车辆')}")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #111111;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit(self._car_data.get("display_name", ""))
        self._name_edit.setStyleSheet(self._input_style())
        form.addRow("车辆名称", self._name_edit)


        self._drivetrain_combo = QComboBox()
        self._drivetrain_combo.addItems(self.DRIVETRAIN_OPTIONS)
        current_dt = self._car_data.get("drivetrain", "unknown")
        if current_dt in self.DRIVETRAIN_OPTIONS:
            self._drivetrain_combo.setCurrentText(current_dt)
        self._drivetrain_combo.setStyleSheet(self._combo_style())
        form.addRow("驱动形式", self._drivetrain_combo)

        self._status_combo = QComboBox()
        self._status_combo.addItems(self.STATUS_OPTIONS)
        current_st = self._car_data.get("status", "active")
        if current_st in self.STATUS_OPTIONS:
            self._status_combo.setCurrentText(current_st)
        self._status_combo.setStyleSheet(self._combo_style())
        form.addRow("状态", self._status_combo)

        layout.addLayout(form)

        notes_label = QLabel("备注")
        notes_label.setStyleSheet("font-size: 13px; color: #111111; margin-top: 4px;")
        layout.addWidget(notes_label)

        self._notes_edit = QTextEdit(self._car_data.get("notes", ""))
        self._notes_edit.setMaximumHeight(80)
        self._notes_edit.setStyleSheet(
            "QTextEdit { background: #ffffff; color: #111111; border: 1px solid #cccccc; "
            "border-radius: 6px; padding: 6px 10px; font-size: 13px; }"
        )
        layout.addWidget(self._notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet(
            "QPushButton { background: #2f6f65; color: white; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; }"
            "QPushButton:hover { background: #255b53; }"
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        self._result = {
            "display_name": self._name_edit.text().strip(),
            "drivetrain": self._drivetrain_combo.currentText(),
            "status": self._status_combo.currentText(),
            "notes": self._notes_edit.toPlainText().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result

    @staticmethod
    def _input_style() -> str:
        return (
            "QLineEdit, QSpinBox { background: #ffffff; color: #111111; "
            "border: 1px solid #cccccc; border-radius: 6px; "
            "padding: 6px 10px; font-size: 13px; }"
        )

    @staticmethod
    def _combo_style() -> str:
        return (
            "QComboBox { background: #ffffff; color: #111111; "
            "border: 1px solid #cccccc; border-radius: 6px; "
            "padding: 6px 12px; font-size: 13px; }"
            "QComboBox QAbstractItemView { background: #ffffff; color: #111111; "
            "selection-background-color: #e8f0ea; selection-color: #111111; "
            "border: 1px solid #cccccc; outline: none; }"
        )
