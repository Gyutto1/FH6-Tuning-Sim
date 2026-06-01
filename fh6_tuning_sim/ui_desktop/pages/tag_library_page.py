from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.pages.tag_edit_dialog import TagEditDialog
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader
from fh6_tuning_sim.ui_desktop.widgets.tag_chip import TagChip


class TagLibraryPage(QWidget):
    """Tag Library page: visual grouped chips, with create/edit support."""

    def __init__(
        self,
        data_service: DesktopDataService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data = data_service
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")

        content = QWidget()
        content.setStyleSheet("background: #ffffff;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Header with new tag button
        header_row = QHBoxLayout()
        header_row.addWidget(SectionHeader("标签库 Tag Library", "按类别可视化展示所有标签"))
        header_row.addStretch()
        new_btn = QPushButton("+ 新建标签")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton { background: #2f6f65; color: white; border: none; "
            "border-radius: 6px; padding: 6px 16px; font-size: 13px; }"
            "QPushButton:hover { background: #255b53; }"
        )
        new_btn.clicked.connect(self._on_new_tag)
        header_row.addWidget(new_btn)
        layout.addLayout(header_row)

        tags_by_cat = self._data.list_tags_by_category()

        if not tags_by_cat:
            empty = QLabel("暂无标签数据。")
            empty.setStyleSheet("font-size: 14px; color: #888888; padding: 24px;")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)
        else:
            for group_key, group_data in tags_by_cat.items():
                layout.addWidget(self._category_section(group_key, group_data))

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _category_section(self, group_key: str, group_data: dict) -> QWidget:
        section = QWidget()
        sl = QVBoxLayout(section)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(8)

        cat_header = QHBoxLayout()
        header = QLabel(group_data.get("name_zh", group_key))
        header.setStyleSheet("font-size: 14px; font-weight: 600; color: #111111;")
        cat_header.addWidget(header)
        cat_header.addStretch()
        add_btn = QPushButton("+")
        add_btn.setFixedSize(26, 26)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton { background: #f5f5f5; color: #555555; border: 1px solid #d5d5d5; "
            "border-radius: 4px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #e8e8e8; }"
        )
        add_btn.clicked.connect(lambda checked=False, cat=group_key: self._on_new_tag_in_category(cat))
        cat_header.addWidget(add_btn)
        sl.addLayout(cat_header)

        items = group_data.get("items", [])
        if not items:
            empty = QLabel("（无标签）")
            empty.setStyleSheet("font-size: 12px; color: #888888;")
            sl.addWidget(empty)
            return section

        chips_per_row = 8
        for i in range(0, len(items), chips_per_row):
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            batch = items[i:i + chips_per_row]
            for item in batch:
                chip_wrap = QWidget()
                chip_layout = QHBoxLayout(chip_wrap)
                chip_layout.setContentsMargins(0, 0, 0, 0)
                chip_layout.setSpacing(4)

                active = item.get("is_active", True)
                chip = TagChip(
                    text=item.get("label_zh", item.get("key", "")),
                    category=group_key,
                    active=active,
                )
                chip_layout.addWidget(chip)

                del_btn = QPushButton("×")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setFixedSize(20, 20)
                del_btn.setStyleSheet(
                    "QPushButton { background: #fff5f5; color: #a33; border: 1px solid #e6caca; border-radius: 4px; }"
                    "QPushButton:hover { background: #ffe8e8; }"
                )
                tag_id = str(item.get("tag_id") or "")
                del_btn.clicked.connect(lambda checked=False, tid=tag_id: self._on_delete_tag(tid))
                chip_layout.addWidget(del_btn)
                rl.addWidget(chip_wrap)
            rl.addStretch()
            sl.addWidget(row)

        return section

    def _on_new_tag(self) -> None:
        dialog = TagEditDialog(category="general_tag", parent=self)
        if dialog.exec() == TagEditDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                self._data.add_user_tag(
                    result["category"], result["key"], result["label_zh"]
                )
                self._rebuild()

    def _on_new_tag_in_category(self, category: str) -> None:
        dialog = TagEditDialog(category=category, parent=self)
        if dialog.exec() == TagEditDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                self._data.add_user_tag(
                    result["category"], result["key"], result["label_zh"]
                )
                self._rebuild()

    def _rebuild(self) -> None:
        # Clear layout and rebuild
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._build()

    def _on_delete_tag(self, tag_id: str) -> None:
        if not tag_id:
            return
        ok, reason = self._data.can_archive_tag(tag_id)
        if not ok:
            QMessageBox.warning(self, "无法删除", reason)
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle("确认删除")
        dialog.setText("确认删除该标签？（会归档，不会硬删除）")
        dialog.setIcon(QMessageBox.Icon.Question)
        yes_btn = dialog.addButton("是", QMessageBox.ButtonRole.YesRole)
        no_btn = dialog.addButton("否", QMessageBox.ButtonRole.NoRole)
        dialog.setDefaultButton(no_btn)
        dialog.setStyleSheet(
            "QMessageBox { background: #ffffff; color: #111111; }"
            "QMessageBox QLabel { color: #111111; }"
            "QMessageBox QPushButton { background: #f5f5f5; color: #111111; border: 1px solid #cccccc; padding: 5px 14px; min-width: 64px; }"
            "QMessageBox QPushButton:hover { background: #ebebeb; }"
        )
        yes_btn.setStyleSheet("QPushButton { color: #111111; background: #f5f5f5; }")
        no_btn.setStyleSheet("QPushButton { color: #111111; background: #f5f5f5; }")
        dialog.exec()
        if dialog.clickedButton() is not yes_btn:
            return
        deleted, message = self._data.archive_tag(tag_id)
        if deleted:
            QMessageBox.information(self, "已删除", message)
            self._rebuild()
        else:
            QMessageBox.warning(self, "删除失败", message)
