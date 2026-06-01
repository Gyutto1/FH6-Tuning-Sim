from __future__ import annotations

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.i18n.record_labels import RECORD_TYPES, ROUTE_MODES, STEP_NAMES
from fh6_tuning_sim.ui_desktop.pages.setup_snapshot_confirm_page import SetupSnapshotConfirmPage
from fh6_tuning_sim.ui_desktop.pages.tune_detail_page import TuneDetailPage
from fh6_tuning_sim.ui_desktop.pages.upgrade_store_page import UpgradeStorePage
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.services.recording_worker import RecordingWorker
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


CHIP_UNSELECTED = "QPushButton { background: #f5f5f5; color: #333333; border: 1px solid #d5d5d5; border-radius: 6px; padding: 5px 14px; font-size: 12px; }"
CHIP_SELECTED = "QPushButton { background: #2f6f65; color: #ffffff; border: 1px solid #2f6f65; border-radius: 6px; padding: 5px 14px; font-size: 12px; font-weight: 600; }"


class RecordRunPage(QWidget):
    STEP_NAMES = STEP_NAMES

    def __init__(self, data_service: DesktopDataService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("recordRunPage")
        self._data = data_service
        self._car_id = ""
        self._car: dict | None = None
        self._step = 0
        self._entry_mode = "new"
        self._lock_setup_steps = False

        self._working_build_id = ""
        self._working_tune_id = ""
        self._setup_snapshot_id = ""
        self._session_temp_build_id = ""
        self._session_temp_tune_id = ""

        self._selected_intents: set[str] = set()
        self._intent_buttons: dict[str, QPushButton] = {}
        self._thread: QThread | None = None
        self._worker: RecordingWorker | None = None
        self._recording_context: dict | None = None
        self._packet_count = 0
        self._elapsed_seconds = 0.0
        self._has_record_started = False
        self._has_unsaved_work = False

        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        root.addWidget(SectionHeader("Record Run Wizard", "Upgrade -> Tune -> Snapshot -> Route/Tags -> Run"))

        self._step_label = QLabel("")
        self._step_label.setStyleSheet("font-size: 13px; color: #555555; font-weight: 600;")
        root.addWidget(self._step_label)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        nav = QHBoxLayout()
        self._back_btn = QPushButton("上一步")
        self._next_btn = QPushButton("下一步")
        self._start_btn = QPushButton("开始记录")
        self._stop_btn = QPushButton("停止记录并保存")
        for btn in [self._back_btn, self._next_btn, self._start_btn, self._stop_btn]:
            btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.clicked.connect(self._prev_step)
        self._next_btn.clicked.connect(self._next_step)
        self._start_btn.clicked.connect(self._on_start_recording)
        self._stop_btn.clicked.connect(self._on_stop_recording)
        self._start_btn.setStyleSheet(self._button_style("#2f6f65", "#ffffff"))
        self._stop_btn.setStyleSheet(self._button_style("#8a3a3a", "#ffffff"))
        self._back_btn.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
        self._next_btn.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
        nav.addWidget(self._back_btn)
        nav.addWidget(self._next_btn)
        nav.addStretch()
        nav.addWidget(self._start_btn)
        nav.addWidget(self._stop_btn)
        root.addLayout(nav)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 13px; color: #555555;")
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

    def load_car(
        self,
        car_id: str,
        build_id: str | None = None,
        tune_id: str | None = None,
        setup_snapshot_id: str | None = None,
    ) -> None:
        self._car_id = car_id
        self._data.cleanup_draft_builds_without_runs(car_id)
        self._car = self._data.get_car(car_id)
        self._step = 0
        self._selected_intents.clear()
        self._session_temp_build_id = ""
        self._session_temp_tune_id = ""
        self._setup_snapshot_id = setup_snapshot_id or ""
        self._has_record_started = False
        self._has_unsaved_work = False
        self._entry_mode = "existing" if build_id else "new"
        self._lock_setup_steps = self._entry_mode == "existing"

        if self._entry_mode == "new":
            build = self._data.create_new_recording_build(car_id)
            self._working_build_id = str(build.get("build_id") or "")
            self._session_temp_build_id = self._working_build_id
            tune = self._data.tunes.ensure_baseline_tune(self._working_build_id)
            self._working_tune_id = str(tune.get("tune_id") or "")
            self._has_unsaved_work = True
        else:
            self._working_build_id = str(build_id or "")
            self._working_tune_id = str(tune_id or "")
            if not self._working_tune_id:
                tunes = self._data.list_tunes_for_build(self._working_build_id)
                if tunes:
                    self._working_tune_id = str(tunes[0].get("tune_id") or "")
            if not self._working_tune_id:
                tune = self._data.tunes.ensure_baseline_tune(self._working_build_id)
                self._working_tune_id = str(tune.get("tune_id") or "")
            if not self._setup_snapshot_id:
                runs = self._data.list_runs_for_build(self._working_build_id)
                if runs:
                    self._setup_snapshot_id = str(runs[0].get("setup_snapshot_id") or "")
            if not self._setup_snapshot_id:
                snaps = self._data.list_setup_snapshots_for_tune(self._working_tune_id)
                if snaps:
                    self._setup_snapshot_id = str(snaps[0].get("setup_snapshot_id") or "")
            if not self._setup_snapshot_id:
                snap = self._data.snapshots.ensure_default_setup_snapshot(
                    self._car_id, self._working_build_id, self._working_tune_id
                )
                self._setup_snapshot_id = str(snap.get("setup_snapshot_id") or "")

        self._rebuild_steps()
        if self._lock_setup_steps:
            self._step = 5
            self._update_step_state()

    def _rebuild_steps(self) -> None:
        while self._stack.count():
            widget = self._stack.widget(0)
            self._stack.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        if not self._car or not self._working_build_id or not self._working_tune_id:
            self._stack.addWidget(self._empty_page("请先从车辆库进入记录流程。"))
        else:
            self._stack.addWidget(self._preset_step())
            self._stack.addWidget(self._upgrade_step())
            self._stack.addWidget(self._tune_step())
            self._stack.addWidget(self._snapshot_step())
            self._stack.addWidget(self._naming_step())
            self._stack.addWidget(self._route_tag_step())
            self._stack.addWidget(self._ready_step())
        self._update_step_state()

    def _preset_step(self) -> QWidget:
        page, layout = self._page("Step 0: Optional Preset")
        self._preset_combo = self._combo("presetBuildCombo")
        self._preset_combo.addItem("不使用预设", "")
        recent = []
        for run in self._data.list_runs_for_car(self._car_id):
            bid = str(run.get("build_id") or "")
            if bid and bid not in recent:
                recent.append(bid)
        for bid in recent:
            build = self._data.builds.get_build(bid)
            if build:
                self._preset_combo.addItem(f"[Run] {build.get('display_name') or bid}", bid)
        for b in self._data.list_builds_for_car(self._car_id):
            bid = str(b.get("build_id") or "")
            if bid and self._preset_combo.findData(bid) < 0 and bid != self._working_build_id:
                self._preset_combo.addItem(b.get("display_name") or bid, bid)
        apply_btn = QPushButton("应用预设到本次记录")
        apply_btn.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
        apply_btn.clicked.connect(self._apply_preset_build)
        layout.addWidget(self._field("Preset Build", self._preset_combo))
        layout.addWidget(apply_btn)
        layout.addStretch()
        return page

    def _upgrade_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._upgrade_page = UpgradeStorePage(self._data, on_back=None, on_saved=lambda build_id: self._on_upgrade_saved(), parent=page)
        self._upgrade_page.load_store(self._working_build_id, source_context="record_embedded")
        layout.addWidget(self._upgrade_page)
        return page

    def _tune_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._tune_page = TuneDetailPage(self._data, on_record=None, parent=page, record_flow=True)
        self._tune_page.load_tune(self._working_tune_id)
        layout.addWidget(self._tune_page)
        return page

    def _snapshot_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._snapshot_page = SetupSnapshotConfirmPage(
            self._data,
            self._car_id,
            self._working_build_id,
            self._working_tune_id,
            snapshot_id=self._setup_snapshot_id or None,
            on_confirmed=self._on_snapshot_confirmed,
            parent=page,
            embedded=True,
        )
        layout.addWidget(self._snapshot_page)
        return page

    def _naming_step(self) -> QWidget:
        page, layout = self._page("Step 4: Name Build/Tune")
        build = self._data.builds.get_build(self._working_build_id) or {}
        tune = self._data.tunes.get_tune(self._working_tune_id) or {}
        self._build_name_edit = QLineEdit(build.get("display_name") or "")
        self._tune_name_edit = QLineEdit(tune.get("display_name") or "")
        layout.addWidget(self._field("Build Name", self._build_name_edit))
        layout.addWidget(self._field("Tune Name", self._tune_name_edit))
        layout.addStretch()
        return page

    def _route_tag_step(self) -> QWidget:
        page, layout = self._page("Step 5: Route / Record Type / Intent Tags")
        self._intent_buttons.clear()
        self._route_mode_combo = self._combo("combo_route_mode")
        for label, key in ROUTE_MODES:
            self._route_mode_combo.addItem(label, key)
        self._route_mode_combo.currentIndexChanged.connect(lambda index: self._on_route_mode_changed())
        layout.addWidget(self._field("Route Mode", self._route_mode_combo))

        route_row = QFrame()
        route_row.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; }")
        route_layout = QHBoxLayout(route_row)
        route_layout.addWidget(QLabel("路线"))
        self._route_combo = self._combo("routeCombo")
        self._route_combo.currentIndexChanged.connect(lambda index: self._update_step_state())
        self._new_route_btn = QPushButton("新建路线")
        self._new_route_btn.clicked.connect(self._create_route_from_dialog)
        self._new_route_btn.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
        route_layout.addWidget(self._route_combo, 1)
        route_layout.addWidget(self._new_route_btn)
        layout.addWidget(route_row)
        self._reload_routes()

        self._type_combo = self._combo("recordTypeCombo")
        record_types = self._data.list_record_types() if hasattr(self._data, "list_record_types") else []
        if record_types:
            for item in record_types:
                self._type_combo.addItem(item.get("label_zh") or item.get("record_type_key"), item.get("record_type_key"))
        else:
            for label, key in RECORD_TYPES:
                self._type_combo.addItem(label, key)
        self._type_combo.currentIndexChanged.connect(lambda index: self._update_step_state())
        layout.addWidget(self._field("Record Type", self._type_combo))

        tag_frame = QFrame()
        tag_layout = QGridLayout(tag_frame)
        tag_layout.setHorizontalSpacing(8)
        tag_layout.setVerticalSpacing(8)
        tag_layout.setContentsMargins(8, 8, 8, 8)
        col, row = 0, 0
        for item in self._data.list_tags_by_category().get("intent_tag", {}).get("items", []):
            key = str(item.get("key") or "")
            if not key:
                continue
            btn = QPushButton(item.get("label_zh") or key)
            btn.setCheckable(True)
            btn.setStyleSheet(CHIP_UNSELECTED)
            btn.toggled.connect(lambda checked, k=key: self._on_intent_toggled(k, checked))
            self._intent_buttons[key] = btn
            tag_layout.addWidget(btn, row, col)
            col += 1
            if col >= 4:
                col, row = 0, row + 1
        layout.addWidget(tag_frame)

        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText("可选备注")
        self._notes_edit.setMaximumHeight(90)
        layout.addWidget(self._notes_edit)

        data_lines = self._data.data_ownership_lines() if hasattr(self._data, "data_ownership_lines") else []
        if data_lines:
            ownership = QLabel("数据归属说明\n" + "\n".join(f"- {line}" for line in data_lines))
            ownership.setWordWrap(True)
            ownership.setStyleSheet(
                "font-size: 12px; color: #444444; background: #fafafa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px;"
            )
            layout.addWidget(ownership)
        layout.addStretch()
        return page

    def _ready_step(self) -> QWidget:
        page, layout = self._page("Step 6: Ready / Start Recording")
        self._ready_summary = QLabel("")
        self._ready_summary.setWordWrap(True)
        self._ready_summary.setStyleSheet("font-size: 13px; color: #333333; padding: 12px; background: #fafafa; border: 1px solid #e0e0e0; border-radius: 8px;")
        layout.addWidget(self._ready_summary)
        layout.addStretch()
        return page

    def _on_upgrade_saved(self) -> None:
        self._has_unsaved_work = True
        self._update_step_state()

    def _on_snapshot_confirmed(self, snapshot_id: str) -> None:
        self._setup_snapshot_id = snapshot_id
        self._has_unsaved_work = True
        if self._step == 3:
            self._step = 4
        self._update_step_state()

    def _apply_preset_build(self) -> None:
        source_build_id = self._preset_combo.currentData() if hasattr(self, "_preset_combo") else ""
        if not source_build_id:
            return
        cloned = self._data.clone_build_with_selections(str(source_build_id))
        self._working_build_id = str(cloned.get("build_id") or self._working_build_id)
        self._session_temp_build_id = self._working_build_id
        source_tunes = self._data.list_tunes_for_build(str(source_build_id))
        if source_tunes:
            cloned_tune = self._data.clone_tune_with_values(str(source_tunes[0].get("tune_id") or ""), self._working_build_id)
            self._working_tune_id = str(cloned_tune.get("tune_id") or self._working_tune_id)
            self._session_temp_tune_id = self._working_tune_id
        new_snap = self._data.snapshots.ensure_default_setup_snapshot(self._car_id, self._working_build_id, self._working_tune_id)
        self._setup_snapshot_id = str(new_snap.get("setup_snapshot_id") or "")
        source_runs = self._data.list_runs_for_build(str(source_build_id))
        if source_runs:
            source_snap_id = str(source_runs[0].get("setup_snapshot_id") or "")
            if source_snap_id:
                self._data.copy_snapshot_context(source_snap_id, self._setup_snapshot_id)
        self._has_unsaved_work = True
        self._rebuild_steps()

    def _on_intent_toggled(self, key: str, checked: bool) -> None:
        if checked:
            self._selected_intents.add(key)
        else:
            self._selected_intents.discard(key)
        btn = self._intent_buttons.get(key)
        if btn:
            btn.setStyleSheet(CHIP_SELECTED if checked else CHIP_UNSELECTED)
        self._update_step_state()

    def _on_route_mode_changed(self) -> None:
        self._reload_routes()
        self._update_step_state()

    def _next_step(self) -> None:
        if self._thread is not None:
            return
        if self._step == 2:
            self._refresh_snapshot_step()
        if self._step == 3 and not self._setup_snapshot_id:
            self._status_label.setText("请先确认并冻结 Setup Snapshot。")
            return
        if self._step == 4:
            self._apply_names()
        if self._step < self._stack.count() - 1:
            self._step += 1
            self._update_step_state()

    def _prev_step(self) -> None:
        if self._thread is not None:
            return
        if self._lock_setup_steps and self._step <= 5:
            return
        if self._step > 0:
            self._step -= 1
            self._update_step_state()

    def _refresh_snapshot_step(self) -> None:
        if self._stack.count() <= 3:
            return
        old = self._stack.widget(3)
        self._stack.removeWidget(old)
        old.setParent(None)
        old.deleteLater()
        self._stack.insertWidget(3, self._snapshot_step())

    def _apply_names(self) -> None:
        if hasattr(self, "_build_name_edit"):
            name = self._build_name_edit.text().strip()
            if name:
                self._data.builds.update_build(self._working_build_id, {"display_name": name})
        if hasattr(self, "_tune_name_edit"):
            name = self._tune_name_edit.text().strip()
            if name:
                self._data.update_tune(self._working_tune_id, {"display_name": name})

    def _update_step_state(self) -> None:
        if not hasattr(self, "_stack"):
            return
        self._stack.setCurrentIndex(self._step)
        step_name = self.STEP_NAMES[self._step] if self._step < len(self.STEP_NAMES) else ""
        self._step_label.setText(f"Step {self._step + 1} / {self._stack.count()}  {step_name}")
        is_recording = self._thread is not None
        validation = self._data.validate_recording_context(self._current_recording_context())
        snapshot_ready, missing_count, required_count = self._snapshot_vehicle_data_ready()
        route_ok = True
        if hasattr(self, "_route_mode_combo") and hasattr(self, "_route_combo"):
            route_ok = not (self._route_mode_combo.currentData() == "timed_route" and not str(self._route_combo.currentData() or "").strip())
        can_start = bool(self._car) and self._step == self._stack.count() - 1 and validation.get("is_valid", False) and route_ok and not is_recording

        self._back_btn.setVisible(not is_recording and self._step > 0)
        self._back_btn.setEnabled(not is_recording and self._step > 0)
        if self._lock_setup_steps and self._step <= 5:
            self._back_btn.setVisible(False)
            self._back_btn.setEnabled(False)
        self._next_btn.setVisible(not is_recording and self._step < self._stack.count() - 1)
        self._next_btn.setEnabled(not is_recording and self._step < self._stack.count() - 1)
        if self._step == 3 and not self._setup_snapshot_id:
            self._next_btn.setEnabled(False)
        self._start_btn.setVisible(not is_recording and self._step == self._stack.count() - 1)
        self._start_btn.setEnabled(can_start)
        self._stop_btn.setVisible(is_recording)
        self._stop_btn.setEnabled(is_recording)
        if hasattr(self, "_ready_summary"):
            self._ready_summary.setText(self._ready_text())

        if is_recording:
            return
        if can_start:
            if snapshot_ready:
                self._status_label.setText("上下文完整，可以开始记录。")
            else:
                self._status_label.setText(
                    f"当前 Snapshot 车辆数据未补录完整（缺少 {missing_count}/{required_count} 项）。点击开始记录后会先要求补录。"
                )
        elif self._step == self._stack.count() - 1 and not snapshot_ready:
            self._status_label.setText(
                f"当前 Snapshot 车辆数据未补录完整（缺少 {missing_count}/{required_count} 项）。"
            )
        elif self._step == 3 and not self._setup_snapshot_id:
            self._status_label.setText("请确认并冻结 Setup Snapshot 后进入下一步。")
        elif self._step == self._stack.count() - 1:
            missing = list(validation.get("missing", []))
            if not route_ok:
                missing.append("route_id")
            self._status_label.setText("上下文未完整，缺少：" + ", ".join(missing))
        else:
            self._status_label.setText("")

    def _ready_text(self) -> str:
        ctx = self._current_recording_context()
        car = self._data.get_car(ctx.get("car_id", ""))
        build = self._data.builds.get_build(str(ctx.get("build_id", ""))) if ctx.get("build_id") else None
        tune = self._data.tunes.get_tune(str(ctx.get("tune_id", ""))) if ctx.get("tune_id") else None
        snap = self._data.snapshots.get_snapshot(str(ctx.get("setup_snapshot_id", ""))) if ctx.get("setup_snapshot_id") else None
        route_mode = self._data.label_route_mode(ctx.get("route_mode", "-"))
        type_label = self._data.label_record_type(ctx.get("record_type", "-"))
        tag_items = self._data.tags.list_by_category("intent_tag") if hasattr(self._data, "tags") else []
        tag_labels = [t.get("label_zh") or t.get("tag_key") for t in tag_items if t.get("tag_key") in (ctx.get("intent_tags") or [])]
        lines = [
            f"车辆: {car.get('display_name', '-') if car else '-'}",
            f"Build: {build.get('display_name', '-') if build else '-'}",
            f"Tune: {tune.get('display_name', '-') if tune else '-'}",
            f"Snapshot: {snap.get('snapshot_name', '-') if snap else '-'}",
            f"路线: {route_mode}  |  记录类型: {type_label}",
            f"意图标签: {', '.join(tag_labels) or '未分类'}",
        ]
        notes = ctx.get("notes", "")
        if notes:
            lines.append(f"备注: {notes}")
        return "\n".join(lines)

    def _reload_routes(self) -> None:
        if not hasattr(self, "_route_combo"):
            return
        selected = self._route_combo.currentData() if self._route_combo.count() else ""
        self._route_combo.clear()
        self._route_combo.addItem("未选择", "")
        mode = self._route_mode_combo.currentData() if hasattr(self, "_route_mode_combo") else ""
        for route in self._data.list_routes():
            route_mode = str(route.get("route_mode") or "")
            if mode == "timed_route" and route_mode not in ("timed_route", "unset"):
                continue
            self._route_combo.addItem(route.get("display_name") or route.get("route_key") or "", route.get("route_id"))
        if selected:
            idx = self._route_combo.findData(selected)
            if idx >= 0:
                self._route_combo.setCurrentIndex(idx)

    def _create_route_from_dialog(self) -> None:
        mode = self._route_mode_combo.currentData() if hasattr(self, "_route_mode_combo") else "timed_route"
        name, ok = QInputDialog.getText(self, "新建路线", "路线中文名称")
        if not ok or not name.strip():
            return
        self._data.create_route(name.strip(), str(mode or "timed_route"), route_type="road")
        self._reload_routes()
        idx = self._route_combo.findText(name.strip())
        if idx >= 0:
            self._route_combo.setCurrentIndex(idx)
        self._update_step_state()

    def _current_recording_context(self) -> dict:
        return {
            "car_id": self._car_id,
            "build_id": self._working_build_id,
            "tune_id": self._working_tune_id,
            "setup_snapshot_id": self._setup_snapshot_id,
            "route_id": self._route_combo.currentData() if hasattr(self, "_route_combo") else "",
            "route_mode": self._route_mode_combo.currentData() if hasattr(self, "_route_mode_combo") else "",
            "record_type": self._type_combo.currentData() if hasattr(self, "_type_combo") else "",
            "intent_tags": sorted(self._selected_intents),
            "notes": self._notes_edit.toPlainText().strip() if hasattr(self, "_notes_edit") else "",
        }

    def _on_start_recording(self) -> None:
        if not self._ensure_snapshot_ready_before_recording():
            self._update_step_state()
            return
        validation = self._data.validate_recording_context(self._current_recording_context())
        if not validation.get("is_valid", False) or self._thread is not None:
            self._update_step_state()
            return
        self._recording_context = validation["context"]
        self._has_record_started = True
        self._has_unsaved_work = False
        self._packet_count = 0
        self._elapsed_seconds = 0.0
        self._thread = QThread(self)
        self._worker = RecordingWorker(metadata=dict(self._recording_context))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start_recording)
        self._worker.status_changed.connect(self._on_worker_status)
        self._worker.packet_count_changed.connect(self._on_worker_packet_count)
        self._worker.elapsed_changed.connect(self._on_worker_elapsed)
        self._worker.session_ready.connect(self._on_session_ready)
        self._worker.error_occurred.connect(self._on_worker_error)
        self._worker.session_ready.connect(self._thread.quit)
        self._worker.error_occurred.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_recording_thread)
        self._thread.start()
        self._update_step_state()

    def _on_stop_recording(self) -> None:
        if self._worker is not None:
            self._worker.stop_recording()
        self._status_label.setText("正在停止记录并保存 run...")

    def _on_worker_status(self, status: str) -> None:
        self._status_label.setText(status)

    def _on_worker_packet_count(self, count: int) -> None:
        self._packet_count = count
        self._status_label.setText(f"已接收 {count} 个 packet，已记录 {self._elapsed_seconds:.1f}s。")

    def _on_worker_elapsed(self, elapsed: float) -> None:
        self._elapsed_seconds = elapsed

    def _on_worker_error(self, message: str) -> None:
        self._status_label.setText(message)
        self._update_step_state()

    def _on_session_ready(self, session_id: str, csv_path: str) -> None:
        try:
            if not self._recording_context:
                raise ValueError("missing recording context")
            self._data.create_run_from_recording(
                session_id=session_id,
                csv_path=csv_path,
                context=self._recording_context,
                packet_count=self._packet_count,
                duration_seconds=self._elapsed_seconds,
            )
            self._session_temp_build_id = ""
            self._session_temp_tune_id = ""
            self._status_label.setText(f"已保存 run: {session_id}，packet: {self._packet_count}")
        except Exception as exc:
            self._status_label.setText(f"记录已停止，但 run 保存失败: {exc}")

    def _snapshot_vehicle_data_ready(self) -> tuple[bool, int, int]:
        if not self._setup_snapshot_id:
            return False, 0, 0
        status = self._data.snapshot_vehicle_data_status(self._setup_snapshot_id)
        missing = list(status.get("missing_keys") or [])
        required_count = int(status.get("required_count") or 0)
        return bool(status.get("is_complete")), len(missing), required_count

    def _ensure_snapshot_ready_before_recording(self) -> bool:
        ready, missing_count, required_count = self._snapshot_vehicle_data_ready()
        if ready:
            return True
        dialog = QMessageBox(self)
        dialog.setWindowTitle("需要先补录 Snapshot")
        dialog.setText(
            f"当前 Snapshot 车辆数据未完成（缺少 {missing_count}/{required_count} 项）。\n开始记录前必须先补录。"
        )
        patch_btn = dialog.addButton("去补录", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(patch_btn)
        dialog.exec()
        if dialog.clickedButton() is not patch_btn:
            return False
        self._on_open_snapshot_supplement()
        ready_after, _, _ = self._snapshot_vehicle_data_ready()
        return ready_after

    def _on_open_snapshot_supplement(self, checked: bool = False, force_open: bool = False) -> bool:
        if not self._setup_snapshot_id:
            self._status_label.setText("未找到可补录的 Snapshot。请先完成快照步骤。")
            return False
        run_count = self._data.count_runs_for_snapshot(self._setup_snapshot_id, include_archived=False)
        if run_count > 0:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("二次补录警告")
            dialog.setText(
                "该 Snapshot 已经关联历史 Run。二次补录会改变后续记录的数据基准，"
                "通常不建议在已有数据集上重复补录。\n是否继续？"
            )
            continue_btn = dialog.addButton("继续补录", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
            dialog.setDefaultButton(cancel_btn)
            dialog.exec()
            if dialog.clickedButton() is not continue_btn:
                return False

        dialog = SetupSnapshotConfirmPage(
            self._data,
            self._car_id,
            self._working_build_id,
            self._working_tune_id,
            snapshot_id=self._setup_snapshot_id,
            on_confirmed=self._on_snapshot_confirmed,
            parent=self,
            embedded=False,
        )
        dialog.exec()
        if dialog.confirmed_snapshot_id:
            self._setup_snapshot_id = dialog.confirmed_snapshot_id
            self._has_unsaved_work = True
            self._status_label.setText("Snapshot 补录已保存。")
            self._update_step_state()
            return True
        return False

    def confirm_leave_with_unsaved(self) -> bool:
        if self._has_record_started or not self._has_unsaved_work:
            return True
        dialog = QMessageBox(self)
        dialog.setWindowTitle("未保存内容")
        dialog.setText("你还没有开始 Run。现在退出将放弃本次 Build/Tune/Snapshot 变更。")
        leave_btn = dialog.addButton("放弃并退出", QMessageBox.ButtonRole.DestructiveRole)
        stay_btn = dialog.addButton("继续编辑", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(stay_btn)
        dialog.exec()
        if dialog.clickedButton() is not leave_btn:
            return False
        self.discard_unrecorded_work()
        return True

    def discard_unrecorded_work(self) -> None:
        if self._session_temp_tune_id:
            self._data.archive_tune(self._session_temp_tune_id)
        if self._session_temp_build_id:
            self._data.delete_build_if_no_runs(self._session_temp_build_id)
        self._session_temp_tune_id = ""
        self._session_temp_build_id = ""
        self._has_unsaved_work = False

    def _cleanup_recording_thread(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        self._recording_context = None
        self._update_step_state()

    def _page(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(SectionHeader(title))
        return page, layout

    def _empty_page(self, text: str) -> QWidget:
        page, layout = self._page("Record Run")
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        layout.addStretch()
        return page

    def _combo(self, object_name: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(object_name)
        combo.setStyleSheet("QComboBox { background: #ffffff; color: #111111; border: 1px solid #cccccc; border-radius: 6px; padding: 6px 10px; min-width: 260px; }")
        return combo

    def _field(self, label: str, widget: QWidget) -> QWidget:
        row = QFrame()
        row.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; }")
        layout = QHBoxLayout(row)
        text = QLabel(label)
        text.setMinimumWidth(130)
        layout.addWidget(text)
        layout.addWidget(widget)
        layout.addStretch()
        return row

    def current_build_id(self) -> str:
        return self._working_build_id

    def current_tune_id(self) -> str:
        return self._working_tune_id

    def begin_new_record_flow(self) -> None:
        return

    def on_upgrade_saved_from_store(self) -> str:
        return ""

    def ensure_build_selected(self, build_id: str) -> None:
        return

    def ensure_tune_selected(self, tune_id: str) -> None:
        return

    def _sync_dependent_combos(self) -> None:
        return

    @staticmethod
    def _button_style(bg: str, fg: str) -> str:
        return f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid #d5d5d5; border-radius: 6px; padding: 8px 18px; font-size: 13px; }}"
