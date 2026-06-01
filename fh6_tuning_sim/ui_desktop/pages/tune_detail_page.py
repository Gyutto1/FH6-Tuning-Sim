from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget, QLayout

from fh6_tuning_sim.ui_desktop.pages.setup_snapshot_confirm_page import SetupSnapshotConfirmPage
from fh6_tuning_sim.ui_desktop.pages.tune_parameter_editor import TuneParameterEditor
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


class TuneDetailPage(QWidget):
    def __init__(
        self,
        data_service: DesktopDataService,
        on_record: callable | None = None,
        parent: QWidget | None = None,
        record_flow: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tuneDetailPage")
        self._data = data_service
        self._on_record = on_record
        self._record_flow = record_flow
        self._tune_id = ""
        self._current_section_id = ""
        self._detail: dict | None = None
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
        self._layout.setSpacing(14)
        scroll.setWidget(self._content)
        root.addWidget(scroll)

    def load_tune(self, tune_id: str) -> None:
        self._tune_id = tune_id
        self._current_section_id = ""
        self._refresh()

    def _refresh(self) -> None:
        self._clear()
        self._detail = self._data.get_tune_detail(self._tune_id)
        if not self._detail:
            self._layout.addWidget(self._empty("Tune 未找到。"))
            return
        if self._current_section_id:
            self._render_parameter_page()
        else:
            self._render_section_list()
        self._layout.addStretch()

    def _render_section_list(self) -> None:
        detail = self._detail or {}
        car = detail.get("car") or {}
        build = detail.get("build") or {}
        self._layout.addWidget(
            SectionHeader(
                detail.get("display_name", "Tune"),
                f"{car.get('display_name', '')} / {build.get('display_name', '')} / {detail.get('version', '')}",
            )
        )

        if not self._record_flow:
            actions = QHBoxLayout()
            confirm_snap_btn = QPushButton("确认 Setup Snapshot")
            confirm_snap_btn.setCursor(Qt.PointingHandCursor)
            confirm_snap_btn.setStyleSheet(self._button_style("#2f6f65", "#ffffff"))
            confirm_snap_btn.clicked.connect(lambda checked=False: self._open_snapshot_confirm())
            actions.addWidget(confirm_snap_btn)
            if self._on_record and car.get("car_id"):
                record = QPushButton("从该 Tune 开始记录")
                record.setCursor(Qt.PointingHandCursor)
                record.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
                record.clicked.connect(
                    lambda checked=False, cid=car.get("car_id", ""), bid=build.get("build_id", ""), tid=self._tune_id: self._on_record(cid, bid, tid, None, "existing")
                )
                actions.addWidget(record)
            actions.addStretch()
            self._layout.addLayout(actions)

        self._layout.addWidget(SectionHeader("Tune", "选择调校 section"))
        grouped = self._data.tune_parameters.list_by_section(self._tune_id)
        for section in self._data.tune_parameters.get_sections():
            section_id = str(section.get("section_id") or "")
            params = grouped.get(section_id, [])
            filled = sum(1 for item in params if item.get("value_real") is not None)
            button = self._section_button(
                section.get("label_zh", section_id),
                f"{filled}/{len(params)} 个参数已设置",
            )
            button.clicked.connect(lambda checked=False, sid=section_id: self._enter_section(sid))
            self._layout.addWidget(button)

        if not self._record_flow:
            snapshots = detail.get("setup_snapshots", [])
            self._layout.addWidget(SectionHeader("Setup Snapshots", f"{len(snapshots)} 个快照"))
            for snapshot in snapshots:
                self._layout.addWidget(self._snapshot_card(snapshot))
            if not snapshots:
                self._layout.addWidget(self._empty("暂无 Setup Snapshot。"))

    def _render_parameter_page(self) -> None:
        section = next(
            (item for item in self._data.tune_parameters.get_sections() if item.get("section_id") == self._current_section_id),
            {},
        )
        self._layout.addWidget(self._text_button("返回 Tune section", self._back_to_sections))
        self._layout.addWidget(SectionHeader(section.get("label_zh", "Tune 参数"), section.get("label_en", "")))
        self._layout.addWidget(TuneParameterEditor(self._data, self._tune_id, self._current_section_id))

    def _snapshot_card(self, snapshot: dict) -> QWidget:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; }")
        layout = QHBoxLayout(card)
        title = QLabel(f"{snapshot.get('snapshot_name') or '未命名快照'}  PI {snapshot.get('pi') or '-'}  {snapshot.get('car_class') or '-'}")
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #111111;")
        layout.addWidget(title, 1)
        edit = QPushButton("编辑 / 确认")
        edit.setCursor(Qt.PointingHandCursor)
        edit.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
        edit.clicked.connect(lambda checked=False, sid=snapshot.get("setup_snapshot_id"): self._open_snapshot_confirm(str(sid or "")))
        layout.addWidget(edit)
        return card

    def _open_snapshot_confirm(self, setup_snapshot_id: str | None = None) -> None:
        detail = self._detail or {}
        car = detail.get("car") or {}
        build = detail.get("build") or {}
        car_id = str(car.get("car_id") or "")
        build_id = str(build.get("build_id") or "")
        if not car_id or not build_id:
            return
        dialog = SetupSnapshotConfirmPage(
            self._data,
            car_id,
            build_id,
            self._tune_id,
            snapshot_id=setup_snapshot_id or None,
            on_confirmed=lambda sid: self._refresh(),
            parent=self,
        )
        dialog.exec()

    def _enter_section(self, section_id: str) -> None:
        self._current_section_id = section_id
        self._refresh()

    def _back_to_sections(self) -> None:
        self._current_section_id = ""
        self._refresh()

    @staticmethod
    def _section_button(title: str, subtitle: str) -> QPushButton:
        button = QPushButton(f"{title}\n{subtitle}")
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(70)
        button.setStyleSheet(
            "QPushButton { background: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 8px; "
            "padding: 12px; text-align: left; font-size: 13px; color: #111111; }"
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

    @staticmethod
    def _button_style(bg: str, fg: str) -> str:
        return f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid #d5d5d5; border-radius: 6px; padding: 7px 14px; font-size: 13px; }}"
