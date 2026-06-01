from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget

from fh6_tuning_sim.ui_desktop.pages.car_upgrade_catalog_dialog import CarUpgradeCatalogDialog
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.metric_card import MetricCard
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


class CarDetailPage(QWidget):
    """Car detail as the entry point for Build -> Tune -> Setup Snapshot -> Run."""

    def __init__(
        self,
        data_service: DesktopDataService,
        on_record: callable | None = None,
        on_enter_build: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("carDetailPage")
        self._data = data_service
        self._on_record = on_record
        self._on_enter_build = on_enter_build
        self._car_id = ""
        self._car: dict | None = None
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
        self._layout.setSpacing(16)
        scroll.setWidget(self._content)
        root.addWidget(scroll)

    def load_car(self, car_id: str) -> None:
        self._car_id = car_id
        self._car = self._data.get_car(car_id)
        self._refresh()

    def _refresh(self) -> None:
        self._clear()
        if not self._car:
            self._layout.addWidget(self._empty("车辆数据未找到。"))
            return

        car = self._car
        self._layout.addWidget(
            SectionHeader(
                car.get("display_name", "未命名车辆"),
                f"{car.get('drivetrain_label', '')} | car_ordinal: {car.get('car_ordinal', 'N/A')}",
            )
        )

        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        metrics.addWidget(MetricCard("Runs", str(car.get("run_count", 0))))
        metrics.addWidget(MetricCard("Tunes", str(car.get("tune_count", 0))))
        metrics.addWidget(MetricCard("Dataset Groups", str(car.get("dataset_group_count", 0))))
        metrics.addStretch()
        self._layout.addLayout(metrics)

        actions = QHBoxLayout()
        if self._on_record:
            record = QPushButton("开始新记录")
            record.setObjectName("carDetailRecordButton")
            record.setCursor(Qt.PointingHandCursor)
            record.setStyleSheet(self._button_style("#2f6f65", "#ffffff"))
            record.clicked.connect(lambda checked=False, cid=self._car_id: self._on_record(cid, "", None, None, "new"))
            actions.addWidget(record)
        manage_catalog = QPushButton("管理车型升级目录")
        manage_catalog.setCursor(Qt.PointingHandCursor)
        manage_catalog.setStyleSheet(self._button_style("#f5f5f5", "#555555"))
        manage_catalog.clicked.connect(self._open_upgrade_catalog_dialog)
        actions.addWidget(manage_catalog)
        actions.addStretch()
        self._layout.addLayout(actions)

        builds = car.get("builds", [])
        self._layout.addWidget(SectionHeader("Build Cards", f"{len(builds)} 个 Build"))
        if builds:
            for build in builds:
                self._layout.addWidget(self._build_card(build))
        else:
            self._layout.addWidget(self._empty("暂无 Build。"))

        runs = self._data.list_runs_for_car(self._car_id)
        self._layout.addWidget(SectionHeader("Recent Runs", f"{len(runs)} 条记录"))
        for run in runs[:8]:
            self._layout.addWidget(self._run_card(run))
        if not runs:
            self._layout.addWidget(self._empty("暂无记录。"))
        self._layout.addStretch()

    def _build_card(self, build: dict) -> QWidget:
        card = QFrame()
        card.setObjectName(f"carDetailBuildCard_{build.get('build_id', '')}")
        card.setStyleSheet("QFrame { background: #f8fbfa; border: 1px solid #cfded9; border-radius: 8px; padding: 12px 16px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel(build.get("display_name", "未命名 Build"))
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #111111;")
        top.addWidget(title, 1)
        status = QLabel(build.get("status", "active"))
        status.setStyleSheet("font-size: 12px; color: #2f6f65;")
        top.addWidget(status)
        layout.addLayout(top)

        tunes = self._data.list_tunes_for_build(str(build.get("build_id")))
        runs = self._data.list_runs_for_build(str(build.get("build_id")))
        meta = QLabel(f"{len(tunes)} Tune | {len(runs)} Runs | {build.get('build_key', '')}")
        meta.setStyleSheet("font-size: 12px; color: #555555;")
        layout.addWidget(meta)

        actions = QHBoxLayout()
        enter = QPushButton("进入 Build")
        enter.setCursor(Qt.PointingHandCursor)
        enter.setStyleSheet(self._button_style("#ffffff", "#2f6f65"))
        if self._on_enter_build:
            enter.clicked.connect(lambda checked=False, bid=build.get("build_id", ""): self._on_enter_build(bid))
        actions.addWidget(enter)
        if self._on_record:
            record = QPushButton("开始记录")
            record.setCursor(Qt.PointingHandCursor)
            record.setStyleSheet(self._button_style("#2f6f65", "#ffffff"))
            record.clicked.connect(
                lambda checked=False, cid=self._car_id, bid=str(build.get("build_id") or ""): self._on_record(cid, bid, None, None, "existing")
            )
            actions.addWidget(record)
        delete_btn = QPushButton("删除 Build")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(self._button_style("#f5f5f5", "#8a3a3a"))
        delete_btn.clicked.connect(
            lambda checked=False, bid=str(build.get("build_id") or ""): self._delete_build_card(bid)
        )
        actions.addWidget(delete_btn)
        actions.addStretch()
        layout.addLayout(actions)
        return card

    def _run_card(self, run: dict) -> QWidget:
        card = QFrame()
        card.setObjectName(f"carDetailRunRow_{run.get('session_id', '')}")
        card.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px 14px; }")
        layout = QVBoxLayout(card)
        title = QLabel(self._data.run_display_title(run))
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #111111;")
        layout.addWidget(title)
        subtitle = QLabel(self._data.run_subtitle(run))
        subtitle.setStyleSheet("font-size: 11px; color: #555555; font-family: monospace;")
        layout.addWidget(subtitle)
        return card

    def _open_upgrade_catalog_dialog(self) -> None:
        if not self._car_id:
            return
        dialog = CarUpgradeCatalogDialog(self._data, self._car_id, self)
        dialog.exec()
        self.load_car(self._car_id)

    def _delete_build_card(self, build_id: str) -> None:
        if not build_id:
            return
        if QMessageBox.question(self, "确认删除", "删除该 Build？将归档关联 Run/Tune/Snapshot。") != QMessageBox.StandardButton.Yes:
            return
        ok, reason = self._data.archive_build_with_related(build_id)
        if not ok:
            QMessageBox.warning(self, "删除失败", reason)
        self.load_car(self._car_id)

    def _empty(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 13px; color: #888888; padding: 8px 4px;")
        return label

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _button_style(bg: str, fg: str) -> str:
        return f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid #d5d5d5; border-radius: 6px; padding: 7px 14px; font-size: 13px; }}"
