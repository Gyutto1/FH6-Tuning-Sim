from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


class MetricCard(QFrame):
    """Simple metric display card with label, value and optional subtitle."""

    def __init__(
        self,
        label: str,
        value: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._value = value
        self._subtitle = subtitle
        self._build()

    def _build(self) -> None:
        self.setObjectName("metricCard")
        self.setStyleSheet(
            "#metricCard {"
            "  background: #ffffff;"
            "  border: 1px solid #e0e0e0;"
            "  border-radius: 8px;"
            "}"
        )
        self.setMinimumSize(140, 90)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        label_w = QLabel(self._label)
        label_w.setStyleSheet("font-size: 12px; color: #666666; font-weight: 500;")
        layout.addWidget(label_w)

        value_w = QLabel(str(self._value))
        value_w.setStyleSheet("font-size: 22px; font-weight: 700; color: #111111;")
        layout.addWidget(value_w)

        if self._subtitle:
            sub = QLabel(self._subtitle)
            sub.setStyleSheet("font-size: 11px; color: #888888;")
            layout.addWidget(sub)
