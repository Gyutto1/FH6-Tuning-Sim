from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


TAG_CATEGORIES = [
    ("intent_tag", "记录意图"),
    ("behavior_tag", "驾驶行为"),
    ("run_state_tag", "运行状态"),
    ("dataset_purpose", "数据集用途"),
    ("data_status", "数据状态"),
    ("quality_status", "质量状态"),
    ("general_tag", "通用标签"),
    ("handling_dimension", "操控维度"),
    ("subjective_score", "主观评分"),
]


class TagEditDialog(QDialog):
    """Dialog for creating or editing a user-defined tag."""

    def __init__(
        self,
        category: str = "general_tag",
        existing: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._category = category
        self._existing = existing
        self._result: dict | None = None
        self._build()

    def _build(self) -> None:
        is_new = self._existing is None
        self.setWindowTitle("新建标签" if is_new else "编辑标签")
        self.setMinimumWidth(380)
        self.setStyleSheet("QDialog { background: #ffffff; } QLabel { color: #111111; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        title = QLabel("新建标签" if is_new else f"编辑: {self._existing.get('label_zh', '')}")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #111111;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self._category_combo = QComboBox()
        self._category_combo.addItems([label for _, label in TAG_CATEGORIES])
        for i, (key, _) in enumerate(TAG_CATEGORIES):
            if key == self._category:
                self._category_combo.setCurrentIndex(i)
                break
        if not is_new:
            self._category_combo.setEnabled(False)
        self._category_combo.setStyleSheet(self._combo_style())
        form.addRow("类别", self._category_combo)

        self._name_edit = QLineEdit(self._existing.get("label_zh", "") if self._existing else "")
        self._name_edit.setPlaceholderText("输入标签中文名称...")
        self._name_edit.setStyleSheet(self._input_style())
        form.addRow("中文名", self._name_edit)

        layout.addLayout(form)

        hint = QLabel("标签 key 将自动从中文名生成，无需手动填写。")
        hint.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet(
            "QPushButton { background: #2f6f65; color: white; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; }"
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            return
        idx = self._category_combo.currentIndex()
        category = TAG_CATEGORIES[idx][0] if idx >= 0 else self._category
        import re
        key = re.sub(r'\s+', '_', name.lower())
        key = re.sub(r'[^a-z0-9_]', '', key)
        if not key:
            key = 'tag_' + str(hash(name) % 10000)
        self._result = {
            "key": key,
            "label_zh": name,
            "category": category,
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result

    @staticmethod
    def _input_style() -> str:
        return (
            "QLineEdit { background: #ffffff; color: #111111; "
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
