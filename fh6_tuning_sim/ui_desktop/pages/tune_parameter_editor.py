from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService


class TuneParameterEditor(QWidget):
    def __init__(
        self,
        data_service: DesktopDataService,
        tune_id: str,
        section_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data = data_service
        self._tune_id = tune_id
        self._section_id = section_id
        self._edits: dict[str, QDoubleSpinBox] = {}
        self._status = QLabel("")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        grouped = self._data.tune_parameters.list_by_section(self._tune_id)
        sections = self._data.tune_parameters.get_sections()
        if self._section_id:
            sections = [section for section in sections if section.get("section_id") == self._section_id]

        rendered = False
        for section in sections:
            section_id = str(section.get("section_id") or "")
            for item in grouped.get(section_id, []):
                layout.addWidget(self._param_widget(item))
                rendered = True

        if not rendered:
            hint = QLabel("该 section 暂无 Tune 参数定义。")
            hint.setStyleSheet("font-size: 13px; color: #888888; padding: 12px;")
            layout.addWidget(hint)
            return

        save = QPushButton("保存 Tune 参数")
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(
            "QPushButton { background: #2f6f65; color: white; border: none; "
            "border-radius: 6px; padding: 8px 18px; font-size: 14px; }"
        )
        save.clicked.connect(self._save)
        layout.addWidget(save)
        self._status.setStyleSheet("font-size: 12px; color: #555555;")
        layout.addWidget(self._status)

    def _param_widget(self, item: dict) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e0e0e0; "
            "border-radius: 6px; padding: 8px; }"
        )
        layout = QHBoxLayout(frame)
        layout.setSpacing(8)

        label = QLabel(item.get("label_zh") or item.get("parameter_key") or "")
        label.setMinimumWidth(130)
        label.setStyleSheet("font-size: 13px; font-weight: 600; color: #111111;")
        layout.addWidget(label)

        min_v = float(item.get("min_value") if item.get("min_value") is not None else 0)
        max_v = float(item.get("max_value") if item.get("max_value") is not None else 100)
        step = float(item.get("step") if item.get("step") is not None else 1)
        current = item.get("value_real")
        if current is None:
            current = item.get("default_value")
        if current is None:
            current = min_v

        spin = QDoubleSpinBox()
        spin.setRange(min_v, max_v)
        spin.setSingleStep(step)
        spin.setDecimals(self._decimals_for_step(step))
        spin.setValue(float(current))
        spin.setMaximumWidth(120)
        spin.setStyleSheet(
            "QDoubleSpinBox { background: #ffffff; color: #111111; "
            "border: 1px solid #cccccc; border-radius: 4px; padding: 4px; }"
        )
        param_id = str(item.get("tune_parameter_id"))
        self._edits[param_id] = spin
        layout.addWidget(spin)

        unit = QLabel(item.get("unit") or "-")
        unit.setMinimumWidth(48)
        unit.setStyleSheet("font-size: 12px; color: #555555;")
        layout.addWidget(unit)

        bounds = QLabel(f"min {min_v:g} / max {max_v:g} / step {step:g}")
        bounds.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(bounds, 1)
        return frame

    def _save(self) -> None:
        values = []
        for parameter_id, widget in self._edits.items():
            value_real = widget.value()
            values.append({
                "tune_parameter_id": parameter_id,
                "value_text": str(value_real),
                "value_real": value_real,
            })
        self._data.save_tune_parameter_values(self._tune_id, values)
        self._status.setText("已保存。")

    @staticmethod
    def _decimals_for_step(step: float) -> int:
        text = f"{step:.6f}".rstrip("0").rstrip(".")
        return len(text.split(".")[-1]) if "." in text else 0
