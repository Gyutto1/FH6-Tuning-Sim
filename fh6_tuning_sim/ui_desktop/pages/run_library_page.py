from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


ROUTE_MODES = [("全部", ""), ("计时赛 / 路线", "timed_route"), ("自由驾驶", "free_drive"), ("未设置", "unset")]
RECORD_TYPES = [
    ("全部", ""),
    ("完整跑圈", "full_lap"),
    ("自由驾驶", "free_drive"),
    ("重刹测试", "heavy_braking"),
    ("普通记录", "normal_recording"),
    ("赛道测量", "track_survey"),
    ("其他", "other"),
]
QUALITY_OPTIONS = [("全部", ""), ("良好", "good"), ("警告", "warning"), ("草稿", "draft"), ("未知", "unknown")]
TAG_CATEGORIES = ["intent_tag", "behavior_tag", "dataset_purpose", "general_tag", "run_state_tag"]


class RunLibraryPage(QWidget):
    """SQLite-backed Run Library with sidebar filters and tag-id based filtering."""

    def __init__(self, data_service: DesktopDataService, on_enter_run: callable | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("runLibraryPage")
        self._data = data_service
        self._on_enter_run = on_enter_run
        self._rebuilding_filters = False
        self._build()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_filter_panel())
        splitter.addWidget(self._build_results_panel())
        splitter.setSizes([280, 700])
        root.addWidget(splitter)

        self._populate_filters()
        self._refresh_results()

    def _build_filter_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("runLibraryFilterPanel")
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(340)
        panel.setStyleSheet("background: #fafafa; border-right: 1px solid #e0e0e0;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        layout.addWidget(SectionHeader("筛选", "按上下文、标签和状态检索 Run"))

        self._car_filter = self._combo("run_library_filter_car")
        self._build_filter = self._combo("run_library_filter_build")
        self._tune_filter = self._combo("run_library_filter_tune")
        self._route_mode_filter = self._combo("run_library_filter_route_mode")
        self._type_filter = self._combo("run_library_filter_record_type")
        self._quality_filter = self._combo("run_library_filter_quality")
        self._tag_filter = self._combo("run_library_filter_tag")
        self._include_archived = QCheckBox("包含已归档")
        self._include_archived.setObjectName("run_library_filter_include_archived")
        self._include_archived.setStyleSheet("QCheckBox { color: #333333; font-size: 13px; }")
        self._include_archived.stateChanged.connect(self._refresh_results)

        self._search_edit = QLineEdit()
        self._search_edit.setObjectName("run_library_search_box")
        self._search_edit.setPlaceholderText("关键词 / session / 备注")
        self._search_edit.setStyleSheet(self._input_style())
        self._search_edit.textChanged.connect(self._refresh_results)

        for label, widget in [
            ("车辆", self._car_filter),
            ("Build", self._build_filter),
            ("Tune", self._tune_filter),
            ("路线模式", self._route_mode_filter),
            ("记录类型", self._type_filter),
            ("质量", self._quality_filter),
            ("标签", self._tag_filter),
            ("搜索", self._search_edit),
        ]:
            layout.addWidget(self._field(label, widget))

        layout.addWidget(self._include_archived)

        clear_btn = QPushButton("清空筛选")
        clear_btn.setObjectName("run_library_clear_filters")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
        clear_btn.clicked.connect(self._clear_filters)
        layout.addWidget(clear_btn)
        layout.addStretch()
        return panel

    def _build_results_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #ffffff;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(SectionHeader("Run Library", "SQLite 数据总库"))
        self._result_count = QLabel("")
        self._result_count.setStyleSheet("font-size: 12px; color: #555555;")
        layout.addWidget(self._result_count)

        self._result_scroll = QScrollArea()
        self._result_scroll.setWidgetResizable(True)
        self._result_scroll.setFrameShape(QFrame.NoFrame)
        self._result_scroll.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")
        self._result_content = QWidget()
        self._result_layout = QVBoxLayout(self._result_content)
        self._result_layout.setContentsMargins(0, 0, 0, 0)
        self._result_layout.setSpacing(10)
        self._result_scroll.setWidget(self._result_content)
        layout.addWidget(self._result_scroll, 1)
        return panel

    def _populate_filters(self) -> None:
        self._rebuilding_filters = True
        car_id = self._data_from_combo(self._car_filter)
        build_id = self._data_from_combo(self._build_filter)
        tune_id = self._data_from_combo(self._tune_filter)
        setup_id = ""
        tag_id = self._data_from_combo(self._tag_filter)

        self._fill_combo(self._car_filter, [("全部车辆", "")] + [(c.get("display_name", ""), c.get("car_id", "")) for c in self._data.list_cars()], car_id)

        cars = self._data.list_cars()
        build_rows = []
        for car in cars:
            if car_id and car.get("car_id") != car_id:
                continue
            build_rows.extend(self._data.list_builds_for_car(str(car.get("car_id"))))
        self._fill_combo(self._build_filter, [("全部 Build", "")] + [(b.get("display_name", ""), b.get("build_id", "")) for b in build_rows], build_id)

        tune_rows = []
        current_build = self._data_from_combo(self._build_filter)
        for build in build_rows:
            if current_build and build.get("build_id") != current_build:
                continue
            tune_rows.extend(self._data.list_tunes_for_build(str(build.get("build_id"))))
        self._fill_combo(
            self._tune_filter,
            [("全部 Tune", "")] + [(f"{t.get('display_name') or t.get('name') or ''} {t.get('version') or ''}".strip(), t.get("tune_id", "")) for t in tune_rows],
            tune_id,
        )

        current_tune = self._data_from_combo(self._tune_filter)
        for tune in tune_rows:
            if current_tune and tune.get("tune_id") != current_tune:
                continue

        self._fill_combo(self._route_mode_filter, ROUTE_MODES, self._data_from_combo(self._route_mode_filter))
        record_type_items = [("全部", "")]
        for item in self._data.list_record_types():
            record_type_items.append((item.get("label_zh") or item.get("record_type_key"), item.get("record_type_key", "")))
        self._fill_combo(self._type_filter, record_type_items or RECORD_TYPES, self._data_from_combo(self._type_filter))
        self._fill_combo(self._quality_filter, QUALITY_OPTIONS, self._data_from_combo(self._quality_filter))

        tag_items = [("全部标签", "")]
        tags_by_cat = self._data.list_tags_by_category()
        seen: set[str] = set()
        for category in TAG_CATEGORIES:
            for item in tags_by_cat.get(category, {}).get("items", []):
                tid = str(item.get("tag_id") or "")
                if tid and tid not in seen:
                    seen.add(tid)
                    tag_items.append((item.get("label_zh") or item.get("key") or tid, tid))
        self._fill_combo(self._tag_filter, tag_items, tag_id)

        self._rebuilding_filters = False

    def _fill_combo(self, combo: QComboBox, items: list[tuple[str, str]], selected: str = "") -> None:
        combo.blockSignals(True)
        combo.clear()
        for label, value in items:
            combo.addItem(label, value)
        if selected:
            index = combo.findData(selected)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _refresh_results(self) -> None:
        if self._rebuilding_filters:
            return
        while self._result_layout.count():
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        include_archived = self._include_archived.isChecked() if hasattr(self, "_include_archived") else False
        records = self._data.list_run_records(include_archived=include_archived)
        tag_id = self._data_from_combo(self._tag_filter)
        filtered = self._data.filter_run_records(
            records,
            car_id=self._data_from_combo(self._car_filter),
            build_id=self._data_from_combo(self._build_filter),
            tune_id=self._data_from_combo(self._tune_filter),
            route_mode=self._data_from_combo(self._route_mode_filter),
            record_type=self._data_from_combo(self._type_filter),
            tag_ids=[tag_id] if tag_id else None,
            quality_status=self._data_from_combo(self._quality_filter),
            keyword=(self._search_edit.text() or "").strip(),
            include_archived=include_archived,
        )
        self._result_count.setText(f"{len(filtered)} 条记录")
        if not filtered:
            empty = QLabel("没有符合条件的记录。")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("font-size: 14px; color: #888888; padding: 36px;")
            self._result_layout.addWidget(empty)
        else:
            for record in filtered:
                self._result_layout.addWidget(self._record_card(record))
        self._result_layout.addStretch()

    def _record_card(self, rec: dict) -> QWidget:
        card = QFrame()
        card.setObjectName(f"runRecordCard_{rec.get('session_id', '')}")
        card.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px 16px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel(self._data.run_display_title(rec))
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #111111;")
        top.addWidget(title, 1)
        created = QLabel(str(rec.get("created_at") or "")[:10])
        created.setStyleSheet("font-size: 11px; color: #888888;")
        top.addWidget(created)
        layout.addLayout(top)

        subtitle = QLabel(self._data.run_subtitle(rec))
        subtitle.setStyleSheet("font-size: 12px; color: #555555; font-family: monospace;")
        layout.addWidget(subtitle)

        tag_items = rec.get("tag_items") or []
        if tag_items:
            tags = QHBoxLayout()
            tags.setSpacing(4)
            for item in tag_items:
                label = item.get("label_zh") or item.get("tag_key") or item.get("tag_id")
                chip = QLabel(str(label))
                chip.setStyleSheet("background: #f0f0f0; color: #333333; padding: 2px 8px; border-radius: 4px; font-size: 11px;")
                tags.addWidget(chip)
            tags.addStretch()
            layout.addLayout(tags)

        actions = QHBoxLayout()
        for text, handler, color in [
            ("查看详情", lambda checked=False, sid=rec["session_id"]: self._on_enter_run(sid) if self._on_enter_run else None, "#2f6f65"),
            ("编辑备注", lambda checked=False, sid=rec["session_id"]: self._on_edit_notes(sid), "#555555"),
            ("+ 标签", lambda checked=False, sid=rec["session_id"]: self._on_add_tag(sid), "#555555"),
        ]:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._button_style("#f5f5f5", color))
            btn.clicked.connect(handler)
            actions.addWidget(btn)
        if tag_items:
            remove_btn = QPushButton("- 标签")
            remove_btn.setCursor(Qt.PointingHandCursor)
            remove_btn.setStyleSheet(self._button_style("#fff5f5", "#c62828"))
            remove_btn.clicked.connect(lambda checked=False, sid=rec["session_id"]: self._on_remove_tag(sid))
            actions.addWidget(remove_btn)
        actions.addStretch()
        archive_btn = QPushButton("归档")
        archive_btn.setCursor(Qt.PointingHandCursor)
        archive_btn.setStyleSheet(self._button_style("#ffffff", "#888888"))
        archive_btn.clicked.connect(lambda checked=False, sid=rec["session_id"]: self._on_archive(sid))
        actions.addWidget(archive_btn)
        layout.addLayout(actions)
        return card

    def _on_filter_changed(self) -> None:
        if self._rebuilding_filters:
            return
        self._populate_filters()
        self._refresh_results()

    def _on_result_filter_changed(self) -> None:
        if not self._rebuilding_filters:
            self._refresh_results()

    def _clear_filters(self) -> None:
        self._rebuilding_filters = True
        for combo in [self._car_filter, self._build_filter, self._tune_filter, self._route_mode_filter, self._type_filter, self._quality_filter, self._tag_filter]:
            combo.setCurrentIndex(0)
        self._search_edit.clear()
        self._include_archived.setChecked(False)
        self._rebuilding_filters = False
        self._populate_filters()
        self._refresh_results()

    def _on_edit_notes(self, session_id: str) -> None:
        current = ""
        for run in self._data._load_runs():
            if run.get("session_id") == session_id:
                current = run.get("notes", "")
                break
        text, ok = QInputDialog.getMultiLineText(self, "编辑备注", "备注:", current)
        if ok and text is not None:
            self._data.update_run_notes(session_id, text.strip())
            self._refresh_results()

    def _on_add_tag(self, session_id: str) -> None:
        tag_map = self._tag_choice_map()
        if not tag_map:
            QMessageBox.information(self, "提示", "暂无可用标签。请先在标签库中创建标签。")
            return
        item, ok = QInputDialog.getItem(self, "添加标签", "选择标签:", list(tag_map.keys()), 0, False)
        if ok and item:
            self._data.add_tag_id_to_run(session_id, tag_map[item])
            self._populate_filters()
            self._refresh_results()

    def _on_remove_tag(self, session_id: str) -> None:
        run = next((r for r in self._data.list_run_records(include_archived=True) if r.get("session_id") == session_id), None)
        tag_items = run.get("tag_items", []) if run else []
        if not tag_items:
            QMessageBox.information(self, "提示", "该记录没有标签可移除。")
            return
        choices = {f"{item.get('label_zh') or item.get('tag_key')} ({item.get('tag_id')})": item.get("tag_id") for item in tag_items}
        item, ok = QInputDialog.getItem(self, "移除标签", "选择要移除的标签:", list(choices.keys()), 0, False)
        if ok and item:
            self._data.remove_tag_id_from_run(session_id, str(choices[item]))
            self._populate_filters()
            self._refresh_results()

    def _on_archive(self, session_id: str) -> None:
        reply = QMessageBox.question(self, "确认归档", "归档此记录？\n\n归档不会删除原始数据。", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._data.archive_run(session_id)
            self._refresh_results()

    def _tag_choice_map(self) -> dict[str, str]:
        result: dict[str, str] = {}
        tags_by_cat = self._data.list_tags_by_category()
        for category in TAG_CATEGORIES:
            for item in tags_by_cat.get(category, {}).get("items", []):
                tid = item.get("tag_id")
                if tid:
                    label = item.get("label_zh") or item.get("key") or tid
                    result[f"{label} ({tid})"] = str(tid)
        return result

    def _combo(self, object_name: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(object_name)
        combo.setStyleSheet(self._combo_style())
        if object_name in {"run_library_filter_car", "run_library_filter_build", "run_library_filter_tune"}:
            combo.currentIndexChanged.connect(self._on_filter_changed)
        else:
            combo.currentIndexChanged.connect(self._on_result_filter_changed)
        return combo

    def _field(self, label: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        text = QLabel(label)
        text.setStyleSheet("font-size: 12px; color: #555555; font-weight: 600;")
        layout.addWidget(text)
        layout.addWidget(widget)
        return box

    @staticmethod
    def _data_from_combo(combo: QComboBox) -> str:
        index = combo.currentIndex()
        return str(combo.itemData(index) or "") if index >= 0 else ""

    @staticmethod
    def _combo_style() -> str:
        return (
            "QComboBox { background: #ffffff; color: #111111; border: 1px solid #cccccc; "
            "border-radius: 6px; padding: 6px 10px; font-size: 13px; min-width: 160px; }"
            "QComboBox QAbstractItemView { background: #ffffff; color: #111111; selection-background-color: #e8f0ea; }"
        )

    @staticmethod
    def _input_style() -> str:
        return "QLineEdit { background: #ffffff; color: #111111; border: 1px solid #cccccc; border-radius: 6px; padding: 6px 10px; font-size: 13px; }"

    @staticmethod
    def _button_style(bg: str, fg: str) -> str:
        return f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid #d5d5d5; border-radius: 6px; padding: 6px 12px; font-size: 12px; }} QPushButton:hover {{ background: #e8e8e8; }}"
