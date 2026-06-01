from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.pages.car_upgrade_catalog_dialog import CarUpgradeCatalogDialog
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


class SettingsPage(QWidget):
    """Settings and Database Manager with entity-type search."""

    def __init__(self, data_service: DesktopDataService | None = None, parent: QWidget | None = None) -> None:
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
        layout.setSpacing(14)

        layout.addWidget(SectionHeader("设置 Settings", "项目信息和路径"))

        paths = self._data.runtime_paths() if self._data else {}
        path_rows = [
            ("运行模式", paths.get("mode", "-")),
            ("应用根目录", paths.get("app_root", "-")),
            ("SQLite DB", paths.get("db", "-")),
            ("Raw Telemetry", paths.get("raw", "-")),
            ("Processed Data", paths.get("processed", "-")),
            ("Sessions Metadata", paths.get("sessions", "-")),
            ("Reports", paths.get("reports", "-")),
            ("Configs", paths.get("configs", "-")),
            ("Dictionaries", paths.get("dictionaries", "-")),
            ("UDP 默认监听", f"{paths.get('udp_host', '127.0.0.1')}:{paths.get('udp_port', '9999')}"),
        ]
        for label, value in path_rows:
            layout.addWidget(self._info_card(label, value))

        layout.addWidget(SectionHeader("依赖", "运行时依赖"))
        deps = QLabel(
            "pandas  matplotlib  numpy  pyarrow  PySide6\n\n"
            "PySide6 桌面客户端是当前主线。"
        )
        deps.setStyleSheet(
            "font-size: 13px; color: #111111; background: #ffffff; "
            "border: 1px solid #e0e0e0; border-radius: 8px; "
            "padding: 14px 18px;"
        )
        deps.setWordWrap(True)
        layout.addWidget(deps)

        layout.addWidget(SectionHeader("CLI 工具", "命令行保持独立"))
        cli_info = QLabel(
            "python -m fh6_tuning_sim.receiver.udp_listener\n"
            "python -m fh6_tuning_sim.analysis.feature_engineering\n"
            "python -m fh6_tuning_sim.analysis.report_generator\n"
            "python -m fh6_tuning_sim.analysis.tune_compare\n"
            "python -m fh6_tuning_sim.models.dataset"
        )
        cli_info.setStyleSheet(
            "font-size: 12px; color: #555555; background: #f5f5f5; "
            "border-radius: 6px; padding: 10px 14px; font-family: monospace;"
        )
        layout.addWidget(cli_info)

        layout.addWidget(SectionHeader("车型升级目录", "按车型维护分类/槽位/选项"))
        upgrade_row = QFrame()
        upgrade_row.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; }"
        )
        up_layout = QHBoxLayout(upgrade_row)
        up_layout.setContentsMargins(0, 0, 0, 0)
        up_layout.addWidget(QLabel("车型"))
        self._car_combo = QComboBox()
        if self._data:
            for car in self._data.list_cars():
                self._car_combo.addItem(car.get("display_name", "未命名车辆"), car.get("car_id"))
        up_layout.addWidget(self._car_combo, 1)
        open_btn = QPushButton("打开目录管理")
        open_btn.clicked.connect(self._open_car_upgrade_catalog)
        up_layout.addWidget(open_btn)
        layout.addWidget(upgrade_row)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _open_car_upgrade_catalog(self) -> None:
        if not self._data or not hasattr(self, "_car_combo"):
            return
        car_id = str(self._car_combo.currentData() or "")
        if not car_id:
            return
        dialog = CarUpgradeCatalogDialog(self._data, car_id, self)
        dialog.exec()

    def _info_card(self, label: str, value: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e0e0e0; "
            "border-radius: 6px; padding: 10px 14px; }"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 12px; color: #666666; font-weight: 500;")
        cl.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet("font-size: 12px; color: #555555; font-family: monospace;")
        val.setWordWrap(True)
        cl.addWidget(val)
        return card
