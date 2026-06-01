from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from fh6_tuning_sim.ui_desktop.pages.setup_snapshot_confirm_page import SetupSnapshotConfirmPage
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


CLASS_OPTIONS = ["D", "C", "B", "A", "S1", "S2", "X", "unknown"]


class BuildDetailPage(QWidget):
    def __init__(
        self,
        data_service: DesktopDataService,
        on_enter_tune: callable | None = None,
        on_record: callable | None = None,
        on_enter_upgrade_store: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("buildDetailPage")
        self._data = data_service
        self._on_enter_tune = on_enter_tune
        self._on_record = on_record
        self._on_enter_upgrade_store = on_enter_upgrade_store
        self._build_id = ""
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
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(10)
        scroll.setWidget(self._content)
        root.addWidget(scroll)

    def load_build(self, build_id: str) -> None:
        self._build_id = build_id
        self._refresh()

    def _refresh(self) -> None:
        self._clear()
        detail = self._data.get_build_detail(self._build_id)
        if not detail:
            self._layout.addWidget(self._empty("Build 未找到"))
            return

        # Header
        self._layout.addWidget(SectionHeader(
            detail.get("display_name", "Build"),
            f"{detail.get('car_name', '')} / {detail.get('status', '')}",
        ))

        # PI / Class read-only row (Build page is view-only)
        pi_row = QHBoxLayout()
        pi_row.setSpacing(12)
        pi_label = QLabel("PI:")
        pi_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #111111;")
        pi_row.addWidget(pi_label)
        self._pi_spin = QSpinBox()
        self._pi_spin.setRange(100, 999)
        self._pi_spin.setValue(int(detail.get("pi") or 0))
        self._pi_spin.setStyleSheet(self._input_style())
        self._pi_spin.setReadOnly(True)
        self._pi_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        pi_row.addWidget(self._pi_spin)

        class_label = QLabel("Class:")
        class_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #111111;")
        pi_row.addWidget(class_label)
        self._class_combo = QComboBox()
        self._class_combo.addItems(CLASS_OPTIONS)
        current_class = detail.get("car_class") or "unknown"
        if current_class in CLASS_OPTIONS:
            self._class_combo.setCurrentText(current_class)
        self._class_combo.setStyleSheet(self._combo_style())
        self._class_combo.setEnabled(False)
        pi_row.addWidget(self._class_combo)

        pi_row.addStretch()
        self._layout.addLayout(pi_row)

        hint = QLabel("Build 页面仅查看。若需创建或调整新 Build，请在开始记录前完成。")
        hint.setStyleSheet("font-size: 12px; color: #666666;")
        self._layout.addWidget(hint)

        latest_snapshot_id = ""
        if detail.get("runs"):
            latest_snapshot_id = str((detail.get("runs") or [])[0].get("setup_snapshot_id") or "")
        show_live_build_selection = not latest_snapshot_id
        if show_live_build_selection:
            self._layout.addWidget(SectionHeader("已选升级", "Selected Upgrades"))
            upgrades = detail.get("upgrade_selections") or []
            if upgrades:
                rows = [
                    (
                        f"{item.get('category_label', '')} / {item.get('slot_label_zh', '')}",
                        item.get("option_label", "未设置"),
                    )
                    for item in upgrades
                ]
                self._layout.addWidget(self._compact_group("升级选择", rows))
            else:
                self._layout.addWidget(self._empty("暂无升级选择。进入升级商店选择零件。"))

        # Tunes
        self._layout.addWidget(SectionHeader("Tunes", f"{detail.get('tune_count', 0)} 个 Tune"))
        for tune in detail.get("tunes", []):
            self._layout.addWidget(self._tune_card(tune))
        if not detail.get("tunes"):
            self._layout.addWidget(self._empty("暂无 Tune。"))

        # Runs
        self._layout.addWidget(SectionHeader("Runs", f"{detail.get('run_count', 0)} 条记录"))
        for run in detail.get("runs", [])[:8]:
            self._layout.addWidget(self._info_card([f"{run.get('display_title', '')}  ({run.get('session_id', '')})"]))
        if not detail.get("runs"):
            self._layout.addWidget(self._empty("暂无记录。"))
        else:
            latest_run = detail.get("runs", [])[0]
            snapshot_id = str(latest_run.get("setup_snapshot_id") or "")
            latest_run_tune_id = str(latest_run.get("tune_id") or "")
            if snapshot_id:
                self._layout.addWidget(SectionHeader("Snapshot 只读视图", "来自最近 Run 冻结数据"))
                self._render_snapshot_freeze(snapshot_id)
                status = self._data.snapshot_vehicle_data_status(snapshot_id)
                if not status.get("is_complete"):
                    self._layout.addWidget(self._empty(
                        f"车辆数据面板未补齐：缺少 {len(status.get('missing_keys') or [])}/{status.get('required_count', 0)} 项。"
                    ))
                patch_btn = QPushButton("进入 Snapshot 补录")
                patch_btn.setCursor(Qt.PointingHandCursor)
                patch_btn.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
                patch_btn.clicked.connect(
                    lambda checked=False, sid=snapshot_id, tid=latest_run_tune_id: self._open_snapshot_confirm(sid, tid)
                )
                self._layout.addWidget(patch_btn)
        if self._on_record:
            car_id = str(detail.get("car_id") or "")
            record = QPushButton("从该 Build 开始记录")
            record.setCursor(Qt.PointingHandCursor)
            record.setStyleSheet(self._button_style("#2f6f65", "#ffffff"))
            record.clicked.connect(lambda checked=False, cid=car_id, bid=self._build_id: self._on_record(cid, bid, None, None, "existing"))
            self._layout.addWidget(record)
        self._layout.addStretch()

    def _render_snapshot_freeze(self, snapshot_id: str) -> None:
        build_items = self._data._freeze.get_build_items(snapshot_id)
        if build_items:
            rows = [
                (
                    f"{item.get('category_label_zh','')} / {item.get('slot_label_zh','')}",
                    f"{item.get('option_label_zh','-')}",
                )
                for item in build_items
            ]
            self._layout.addWidget(self._compact_group("冻结 Build 选择", rows))
        tune_values = self._data._freeze.get_tune_values(snapshot_id)
        if tune_values:
            rows = [
                (
                    f"{item.get('section_label_zh','')} / {item.get('parameter_label_zh','')}",
                    f"{item.get('value')} {item.get('unit') or ''}".strip(),
                )
                for item in tune_values
            ]
            self._layout.addWidget(self._compact_group("冻结 Tune 参数", rows))
        vehicle_data = self._data._freeze.get_vehicle_data(snapshot_id)
        if vehicle_data:
            rows = [
                (
                    item.get("label_zh") or item.get("data_key") or "",
                    f"{item.get('value')} {item.get('unit') or ''}".strip(),
                )
                for item in vehicle_data
            ]
            self._layout.addWidget(self._compact_group("冻结车辆数据面板", rows))
        else:
            self._layout.addWidget(self._empty("该 Snapshot 尚未冻结车辆数据面板。"))

    def _open_snapshot_confirm(self, snapshot_id: str, tune_id: str = "") -> None:
        detail = self._data.get_build_detail(self._build_id) or {}
        car_id = str(detail.get("car_id") or "")
        if not car_id:
            return
        snapshot_run_count = self._data.count_runs_for_snapshot(snapshot_id, include_archived=False) if snapshot_id else 0
        if snapshot_run_count > 0:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("二次补录警告")
            dialog.setText(
                "该 Snapshot 已绑定历史 Run。二次补录会影响后续记录的数据基准，通常不建议重复补录。\n是否继续？"
            )
            continue_btn = dialog.addButton("继续补录", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
            dialog.setDefaultButton(cancel_btn)
            dialog.exec()
            if dialog.clickedButton() is not continue_btn:
                return
        resolved_tune_id = tune_id
        if not resolved_tune_id and detail.get("tunes"):
            resolved_tune_id = str((detail.get("tunes") or [])[0].get("tune_id") or "")
        if not resolved_tune_id:
            tune = self._data.tunes.ensure_baseline_tune(self._build_id)
            resolved_tune_id = str(tune.get("tune_id") or "")
        if not resolved_tune_id:
            return
        dialog = SetupSnapshotConfirmPage(
            self._data,
            car_id,
            self._build_id,
            resolved_tune_id,
            snapshot_id=snapshot_id or None,
            on_confirmed=lambda sid: self.load_build(self._build_id),
            parent=self,
            embedded=False,
        )
        dialog.exec()

    def _category_card(self, cat: dict) -> QWidget:
        card = QPushButton()
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(
            "QPushButton { background: #f9f9f9; border: 1px solid #e0e0e0; "
            "border-radius: 10px; padding: 16px; min-height: 100px; text-align: left; }"
            "QPushButton:hover { border-color: #2f6f65; background: #f0f6f3; }"
        )
        cid = cat.get("upgrade_category_id", "")
        card.clicked.connect(lambda checked=False, c=cid: (
            self._on_enter_upgrade_store(self._build_id, c) if self._on_enter_upgrade_store else None
        ))
        # Build inner layout using a child widget
        inner = QWidget()
        inner.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title = QLabel(cat.get("label_zh", ""))
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #111111;")
        layout.addWidget(title)
        subtitle = QLabel(cat.get("label_en", ""))
        subtitle.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(subtitle)
        layout.addStretch()
        # Put inner inside button
        btn_layout = QVBoxLayout(card)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addWidget(inner)
        return card

    def _tune_card(self, tune: dict) -> QWidget:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 8px; }")
        layout = QHBoxLayout(card)
        title = QLabel(f"{tune.get('display_name') or tune.get('name')} {tune.get('version') or ''}".strip())
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #111111;")
        layout.addWidget(title, 1)
        readonly = QLabel("只读")
        readonly.setStyleSheet("font-size: 12px; color: #666666;")
        layout.addWidget(readonly)
        return card

    def _on_pi_changed(self) -> None:
        pass

    def _info_card(self, lines: list[str]) -> QWidget:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        for line in lines:
            label = QLabel(str(line))
            label.setStyleSheet("font-size: 12px; color: #333333;")
            label.setWordWrap(True)
            layout.addWidget(label)
        return card

    def _compact_group(self, title: str, rows: list[tuple[str, str]]) -> QWidget:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 6px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        head = QLabel(title)
        head.setStyleSheet("font-size: 12px; font-weight: 700; color: #111111;")
        layout.addWidget(head)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(2)
        for idx, (k, v) in enumerate(rows):
            k_label = QLabel(str(k))
            k_label.setStyleSheet("font-size: 12px; color: #555555;")
            k_label.setWordWrap(True)
            v_label = QLabel(str(v))
            v_label.setStyleSheet("font-size: 12px; color: #111111;")
            v_label.setWordWrap(True)
            grid.addWidget(k_label, idx, 0)
            grid.addWidget(v_label, idx, 1)
        layout.addLayout(grid)
        return card

    def _empty(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 13px; color: #888888; padding: 8px;")
        return label

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _button_style(bg: str, fg: str) -> str:
        return f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid #d5d5d5; border-radius: 6px; padding: 6px 14px; }}"

    @staticmethod
    def _input_style() -> str:
        return "QSpinBox { background: #ffffff; color: #111111; border: 1px solid #cccccc; border-radius: 6px; padding: 6px 10px; font-size: 14px; }"

    @staticmethod
    def _combo_style() -> str:
        return "QComboBox { background: #ffffff; color: #111111; border: 1px solid #cccccc; border-radius: 6px; padding: 6px 12px; font-size: 14px; }"
