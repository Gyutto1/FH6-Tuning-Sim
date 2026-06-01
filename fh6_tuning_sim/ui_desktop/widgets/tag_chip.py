from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class TagChip(QFrame):
    """Small tag chip showing a label with optional category color."""

    COLORS = {
        "intent_tag": ("#e3f2fd", "#0d47a1"),
        "behavior_tag": ("#fff3e0", "#bf360c"),
        "run_state_tag": ("#f3e5f5", "#6a1b9a"),
        "dataset_purpose": ("#e8f5e9", "#1b5e20"),
        "data_status": ("#fce4ec", "#b71c1c"),
        "quality_status": ("#e0f2f1", "#004d40"),
        "general_tag": ("#f5f5f5", "#333333"),
        "handling_dimension": ("#ede7f6", "#311b92"),
        "subjective_score": ("#e1f5fe", "#01579b"),
    }

    def __init__(
        self,
        text: str,
        category: str = "general_tag",
        active: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._category = category
        self._active = active
        self._build()

    def _build(self) -> None:
        bg, fg = self.COLORS.get(self._category, ("#f5f5f5", "#333333"))
        opacity = "1.0" if self._active else "0.4"
        self.setStyleSheet(
            f"TagChip {{"
            f"  background: {bg};"
            f"  border-radius: 4px;"
            f"  padding: 3px 10px;"
            f"  opacity: {opacity};"
            f"}}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label = QLabel(self._text)
        label.setStyleSheet(
            f"font-size: 12px; color: {fg}; font-weight: 500;"
        )
        layout.addWidget(label)
