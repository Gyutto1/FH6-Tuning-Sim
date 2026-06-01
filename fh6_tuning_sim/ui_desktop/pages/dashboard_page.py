from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.metric_card import MetricCard
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


class DashboardPage(QWidget):
    """Dashboard: platform overview with stats, recent runs, and car previews."""

    def __init__(
        self,
        data_service: DesktopDataService,
        on_navigate: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data = data_service
        self._on_navigate = on_navigate
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

        layout.addWidget(SectionHeader("首页 Dashboard", "车辆数据平台概览"))

        stats = self._data.dashboard_stats()
        metrics = QHBoxLayout()
        metrics.setSpacing(16)
        metrics.addWidget(MetricCard("车辆数", str(stats["car_count"])))
        metrics.addWidget(MetricCard("记录数", str(stats["run_count"])))
        metrics.addWidget(MetricCard("未绑定记录", str(stats["unassigned_run_count"])))
        metrics.addStretch()
        layout.addLayout(metrics)

        cars = stats.get("cars", [])
        if cars:
            layout.addWidget(SectionHeader("车辆预览"))
            for car in cars:
                layout.addWidget(self._car_row(car))
        else:
            empty = QLabel("暂无车辆数据。请在车辆库中添加车辆。")
            empty.setStyleSheet("font-size: 14px; color: #888888; padding: 16px;")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)

        recent = stats.get("recent_runs", [])
        if recent:
            layout.addWidget(SectionHeader("最近记录"))
            for run in recent:
                layout.addWidget(self._run_row(run))

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _car_row(self, car: dict) -> QWidget:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e0e0e0; "
            "border-radius: 8px; padding: 12px 16px; }"
        )
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        name = QLabel(car.get("display_name", "未命名车辆"))
        name.setStyleSheet("font-size: 14px; font-weight: 600; color: #111111;")
        row_layout.addWidget(name)

        pi = car.get("performance_index", 0)
        if pi:
            badge = QLabel(f"PI {pi}  {car.get('drivetrain_label', '')}")
            badge.setStyleSheet(
                "background: #e8f0ea; color: #2f6f65; padding: 2px 8px; "
                "border-radius: 4px; font-size: 11px;"
            )
            row_layout.addWidget(badge)

        row_layout.addStretch()

        detail = QLabel(
            f"记录 {car.get('run_count', 0)}  |  "
            f"数据集组 {car.get('dataset_group_count', 0)}  |  "
            f"建模准备度 {car.get('avg_modeling_readiness', 0):.0f}%"
        )
        detail.setStyleSheet("font-size: 12px; color: #555555;")
        row_layout.addWidget(detail)

        return row

    def _run_row(self, run: dict) -> QWidget:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e0e0e0; "
            "border-radius: 6px; padding: 10px 14px; }"
        )
        rl = QVBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(2)
        title_l = QLabel(self._data.run_display_title(run))
        title_l.setStyleSheet("font-size: 13px; font-weight: 600; color: #111111;")
        rl.addWidget(title_l)
        sub = QLabel(self._data.run_subtitle(run))
        sub.setStyleSheet("font-size: 11px; color: #555555; font-family: monospace;")
        rl.addWidget(sub)
        return row
