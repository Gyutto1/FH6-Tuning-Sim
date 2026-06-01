from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


class UpgradeStorePage(QWidget):
    """Internal state flow: category_grid -> slot_list -> option_list."""

    def __init__(
        self,
        data_service: DesktopDataService,
        on_back: callable | None = None,
        on_saved: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("upgradeStorePage")
        self._data = data_service
        self._on_back = on_back
        self._on_saved = on_saved
        self._build_id = ""
        self._source_context = "build_detail"
        self._view_state = "category_grid"
        self._current_category_id = ""
        self._current_slot_id = ""
        self._pending_option_id = ""
        self._saved_option_id = ""
        self._status_label: QLabel | None = None
        self._option_buttons: dict[str, tuple[QPushButton, str]] = {}
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._content = QWidget()
        self._content.setStyleSheet("background: #ffffff;")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(28, 24, 28, 24)
        self._layout.setSpacing(12)
        scroll.setWidget(self._content)
        root.addWidget(scroll)

    def load_store(
        self,
        build_id: str,
        upgrade_category_id: str | None = None,
        source_context: str = "build_detail",
    ) -> None:
        self._build_id = build_id
        self._source_context = source_context
        self._current_category_id = upgrade_category_id or ""
        self._current_slot_id = ""
        self._pending_option_id = ""
        self._view_state = "slot_list" if upgrade_category_id else "category_grid"
        self._refresh()

    def _refresh(self) -> None:
        self._clear()
        if self._view_state == "option_list":
            self._render_option_list()
        elif self._view_state == "slot_list":
            self._render_slot_list()
        else:
            self._render_category_grid()
        self._layout.addStretch()

    def _render_category_grid(self) -> None:
        self._layout.addWidget(SectionHeader("升级商店", "选择升级分类"))
        grid = QGridLayout()
        grid.setSpacing(10)
        categories = self._data.get_upgrade_categories(self._build_id)
        for idx, category in enumerate(categories[:6]):
            row, col = divmod(idx, 3)
            button = self._menu_button(
                category.get("label_zh", ""),
                f"{category.get('slot_count', 0)} 个槽位",
            )
            category_id = str(category.get("upgrade_category_id") or "")
            button.clicked.connect(lambda checked=False, cid=category_id: self._enter_category(cid))
            grid.addWidget(button, row, col)
        self._layout.addLayout(grid)
        if self._on_back:
            back_text = "返回记录向导" if self._source_context == "record" else "返回 Build Detail"
            self._layout.addWidget(self._text_button(back_text, self._on_back))

    def _render_slot_list(self) -> None:
        category = self._current_category()
        self._layout.addWidget(SectionHeader(category.get("label_zh", "升级分类"), category.get("label_en", "")))
        self._layout.addWidget(self._text_button("返回升级分类", self._back_to_categories))
        slots = self._data.get_upgrade_slots_for_category(self._current_category_id, self._build_id)
        if not slots:
            self._layout.addWidget(self._empty("该分类暂无升级槽位。"))
            return
        for slot in slots:
            selected = slot.get("selected_option_label") or "未选择"
            subtitle = f"当前: {selected}  |  {slot.get('option_count', 0)} 个选项"
            button = self._menu_button(slot.get("label_zh", ""), subtitle)
            slot_id = str(slot.get("slot_id") or "")
            button.clicked.connect(lambda checked=False, sid=slot_id: self._enter_slot(sid))
            self._layout.addWidget(button)

    def _render_option_list(self) -> None:
        slot = self._current_slot()
        self._layout.addWidget(SectionHeader(slot.get("label_zh", "升级槽位"), slot.get("label_en", "")))
        self._layout.addWidget(self._text_button("返回槽位列表", self._back_to_slots))

        options = self._data.get_upgrade_options_for_slot(self._current_slot_id, self._build_id)
        current = self._data.get_upgrade_selection(self._build_id, self._current_slot_id)
        self._saved_option_id = str((current or {}).get("upgrade_option_id") or "")
        self._pending_option_id = self._saved_option_id
        if not self._pending_option_id:
            stock = next((opt for opt in options if opt.get("is_stock")), None)
            self._pending_option_id = str((stock or {}).get("upgrade_option_id") or "")

        group = QButtonGroup(self)
        group.setExclusive(True)
        self._option_buttons = {}
        for option in options:
            option_id = str(option.get("upgrade_option_id") or "")
            label = self._option_label(option)
            button = QPushButton(("✓ " if option_id == self._pending_option_id else "") + label)
            button.setObjectName(f"upgradeOption_{option_id}")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(54)
            button.setStyleSheet(self._option_button_style())
            button.setChecked(option_id == self._pending_option_id)
            button.toggled.connect(lambda checked, oid=option_id: self._set_pending_option(oid, checked))
            group.addButton(button)
            self._option_buttons[option_id] = (button, label)
            self._layout.addWidget(button)
        if not options:
            self._layout.addWidget(self._empty("该槽位暂无可用选项。"))

        save = QPushButton("保存选择")
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(self._button_style("#2f6f65", "#ffffff"))
        save.clicked.connect(self._save_option)
        self._layout.addWidget(save)
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 12px; color: #555555;")
        self._layout.addWidget(self._status_label)
        self._update_status_text(options)

    def _enter_category(self, category_id: str) -> None:
        self._current_category_id = category_id
        self._current_slot_id = ""
        self._view_state = "slot_list"
        self._refresh()

    def _enter_slot(self, slot_id: str) -> None:
        self._current_slot_id = slot_id
        self._view_state = "option_list"
        self._refresh()

    def _back_to_categories(self) -> None:
        self._current_category_id = ""
        self._current_slot_id = ""
        self._view_state = "category_grid"
        self._refresh()

    def _back_to_slots(self) -> None:
        self._current_slot_id = ""
        self._view_state = "slot_list"
        self._refresh()

    def _set_pending_option(self, option_id: str, checked: bool) -> None:
        if checked:
            self._pending_option_id = option_id
            for oid, (button, label) in self._option_buttons.items():
                button.setText(("✓ " if oid == option_id else "") + label)
            self._update_status_text(self._data.get_upgrade_options_for_slot(self._current_slot_id, self._build_id))

    def _save_option(self) -> None:
        if not self._pending_option_id:
            if self._status_label:
                self._status_label.setText("请选择一个配件选项。")
            return
        try:
            self._data.save_build_upgrade_selection(self._build_id, self._current_slot_id, self._pending_option_id)
        except Exception as exc:
            if self._status_label:
                self._status_label.setText(f"保存失败: {exc}")
            return
        self._saved_option_id = self._pending_option_id
        self._update_status_text(self._data.get_upgrade_options_for_slot(self._current_slot_id, self._build_id), saved=True)
        if self._on_saved:
            self._on_saved(self._build_id)
        self._back_to_slots()

    def _update_status_text(self, options: list[dict], saved: bool = False) -> None:
        if not self._status_label:
            return
        current = next((opt for opt in options if str(opt.get("upgrade_option_id") or "") == self._saved_option_id), None)
        pending = next((opt for opt in options if str(opt.get("upgrade_option_id") or "") == self._pending_option_id), None)
        current_label = self._option_label(current) if current else "未选择"
        pending_label = self._option_label(pending) if pending else "未选择"
        if saved:
            self._status_label.setText(f"已保存: {pending_label}")
        elif self._saved_option_id != self._pending_option_id:
            self._status_label.setText(f"当前: {current_label}    待保存: {pending_label}")
        else:
            self._status_label.setText(f"当前: {current_label}")

    def _current_category(self) -> dict:
        return next(
            (
                cat
                for cat in self._data.get_upgrade_categories(self._build_id)
                if cat.get("upgrade_category_id") == self._current_category_id
            ),
            {},
        )

    def _current_slot(self) -> dict:
        return next(
            (
                slot
                for slot in self._data.get_upgrade_slots_for_category(self._current_category_id, self._build_id)
                if slot.get("slot_id") == self._current_slot_id
            ),
            {},
        )

    @staticmethod
    def _option_label(option: dict) -> str:
        if not option:
            return ""
        label = option.get("display_label_zh") or option.get("label_zh") or ""
        pi_delta = option.get("pi_delta")
        if pi_delta is None:
            return label
        sign = "+" if int(pi_delta) > 0 else ""
        return f"{label}  (PI {sign}{pi_delta})"

    @staticmethod
    def _menu_button(title: str, subtitle: str) -> QPushButton:
        button = QPushButton(f"{title}\n{subtitle}".strip())
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(78)
        button.setStyleSheet(
            "QPushButton { background: #f9f9f9; color: #111111; border: 1px solid #e0e0e0; "
            "border-radius: 8px; padding: 12px; text-align: left; font-size: 13px; }"
            "QPushButton:hover { border-color: #2f6f65; background: #f0f6f3; }"
        )
        return button

    @staticmethod
    def _text_button(text: str, handler: callable) -> QPushButton:
        button = QPushButton(f"← {text}")
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(
            "QPushButton { background: transparent; color: #2f6f65; border: none; font-size: 13px; text-align: left; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        button.clicked.connect(handler)
        return button

    @staticmethod
    def _button_style(bg: str, fg: str) -> str:
        return f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid #d5d5d5; border-radius: 6px; padding: 8px 18px; font-size: 13px; }}"

    @staticmethod
    def _option_button_style() -> str:
        return (
            "QPushButton { background: #ffffff; color: #111111; border: 1px solid #d5d5d5; "
            "border-radius: 8px; padding: 10px 14px; text-align: left; font-size: 13px; }"
            "QPushButton:hover { border-color: #2f6f65; background: #f5fbf8; }"
            "QPushButton:checked { background: #eaf4f1; color: #111111; border: 2px solid #2f6f65; font-weight: 600; }"
        )

    @staticmethod
    def _empty(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 13px; color: #888888; padding: 8px;")
        return label

    def _clear(self) -> None:
        self._clear_layout(self._layout)

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_widget = item.widget()
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)
                child_layout.deleteLater()
            if child_widget:
                child_widget.setParent(None)
                child_widget.deleteLater()
