from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.pages.car_detail_page import CarDetailPage
from fh6_tuning_sim.ui_desktop.pages.car_edit_dialog import CarEditDialog
from fh6_tuning_sim.ui_desktop.pages.cars_page import CarsPage
from fh6_tuning_sim.ui_desktop.pages.build_detail_page import BuildDetailPage
from fh6_tuning_sim.ui_desktop.pages.dashboard_page import DashboardPage
from fh6_tuning_sim.ui_desktop.pages.run_detail_page import RunDetailPage
from fh6_tuning_sim.ui_desktop.pages.record_run_page import RecordRunPage
from fh6_tuning_sim.ui_desktop.pages.run_library_page import RunLibraryPage
from fh6_tuning_sim.ui_desktop.pages.settings_page import SettingsPage
from fh6_tuning_sim.ui_desktop.pages.tag_library_page import TagLibraryPage
from fh6_tuning_sim.ui_desktop.pages.tune_detail_page import TuneDetailPage
from fh6_tuning_sim.ui_desktop.pages.upgrade_store_page import UpgradeStorePage
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService

NAV_ITEMS = [
    ("dashboard", "首页"),
    ("cars", "车辆库"),
    ("runs", "数据总库"),
    ("tags", "标签库"),
    ("settings", "设置"),
]

NAV_STYLE = """
QPushButton {
    text-align: left;
    padding: 10px 18px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    color: #333333;
    background: transparent;
}
QPushButton:hover {
    background: #f0f0f0;
}
QPushButton[active="true"] {
    background: #2f6f65;
    color: #ffffff;
    font-weight: 600;
}
"""


class MainWindow(QMainWindow):
    """Main window for the PySide6 Desktop MVP."""

    def __init__(self) -> None:
        super().__init__()
        self._data = DesktopDataService()
        self._current_car_id: str = ""
        self._current_build_id: str = ""
        self._current_tune_id: str = ""
        self._current_setup_snapshot_id: str = ""
        self._current_page_key: str = ""
        self._upgrade_store_source: str = "build_detail"
        self._setup_ui()
        self._navigate("dashboard")

    def _setup_ui(self) -> None:
        self.setWindowTitle("FH6 车辆数据平台")
        self.resize(960, 680)
        self.setMinimumSize(800, 560)
        self.setStyleSheet("QMainWindow { background: #ffffff; }")

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet(
            "#sidebar { background: #ffffff; border-right: 1px solid #e0e0e0; }"
        )
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 16, 12, 16)
        sb_layout.setSpacing(4)

        title = QLabel("FH6 平台")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #111111; padding: 4px 8px 12px 8px;")
        sb_layout.addWidget(title)

        self._nav_buttons: dict[str, QPushButton] = {}
        for key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setObjectName(f"nav_{key}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(NAV_STYLE)
            btn.setProperty("active", False)
            btn.clicked.connect(lambda checked, k=key: self._navigate(k))
            self._nav_buttons[key] = btn
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        version = QLabel("v0.99.1")
        version.setStyleSheet("font-size: 11px; color: #aaaaaa; padding: 4px 12px;")
        sb_layout.addWidget(version)

        root_layout.addWidget(sidebar)

        # Right content
        right = QWidget()
        right.setStyleSheet("background: #ffffff;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._back_bar = QWidget()
        self._back_bar.setFixedHeight(40)
        self._back_bar.setStyleSheet("background: #f8f8f8; border-bottom: 1px solid #e0e0e0;")
        back_layout = QHBoxLayout(self._back_bar)
        back_layout.setContentsMargins(16, 0, 16, 0)
        self._back_btn = QPushButton("← 返回")
        self._back_btn.setObjectName("backButton")
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #555555; font-size: 13px; }"
            "QPushButton:hover { color: #111111; }"
        )
        self._back_btn.clicked.connect(self._go_back)
        back_layout.addWidget(self._back_btn)
        back_layout.addStretch()
        self._back_title = QLabel("")
        self._back_title.setObjectName("backTitle")
        self._back_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #111111;")
        back_layout.addWidget(self._back_title)
        back_layout.addStretch()
        self._back_bar.hide()

        right_layout.addWidget(self._back_bar)

        self._stack = QStackedWidget()
        self._stack.setObjectName("mainStack")
        self._stack.setStyleSheet("background: #ffffff;")

        self._dashboard_page = DashboardPage(self._data, on_navigate=self._navigate)
        self._cars_page = CarsPage(
            self._data, on_enter_car=self._enter_car,
            on_record_car=self._enter_record, on_edit_car=self._edit_car,
        )
        self._car_detail_page = CarDetailPage(self._data, on_record=self._enter_record, on_enter_build=self._enter_build)
        self._build_detail_page = BuildDetailPage(self._data, on_enter_tune=self._enter_tune, on_record=self._enter_record, on_enter_upgrade_store=self._enter_upgrade_store)
        self._upgrade_store_page = UpgradeStorePage(self._data, on_back=self._go_back, on_saved=self._on_upgrade_saved)
        self._tune_detail_page = TuneDetailPage(self._data, on_record=self._enter_record)
        self._record_run_page = RecordRunPage(self._data)
        self._run_detail_page = RunDetailPage(self._data, on_back=self._go_back)
        self._run_library_page = RunLibraryPage(self._data, on_enter_run=self._enter_run)
        self._tag_library_page = TagLibraryPage(self._data)
        self._settings_page = SettingsPage(data_service=self._data)

        self._page_widgets = {
            "dashboard": self._dashboard_page,
            "cars": self._cars_page,
            "car_detail": self._car_detail_page,
            "build_detail": self._build_detail_page,
            "tune_detail": self._tune_detail_page,
            "record": self._record_run_page,
            "runs": self._run_library_page,
            "tags": self._tag_library_page,
            "settings": self._settings_page,
            "upgrade_store": self._upgrade_store_page,
            "run_detail": self._run_detail_page,
        }
        for key in [
            "dashboard", "cars", "car_detail", "build_detail", "tune_detail",
            "record", "runs", "tags", "settings", "upgrade_store", "run_detail",
        ]:
            self._stack.addWidget(self._page_widgets[key])

        right_layout.addWidget(self._stack)
        root_layout.addWidget(right, 1)

    def _navigate(self, page_key: str) -> None:
        page_key = page_key if page_key in self._page_widgets else "dashboard"
        if self._current_page_key == "record" and page_key != "record":
            if hasattr(self._record_run_page, "confirm_leave_with_unsaved"):
                if not self._record_run_page.confirm_leave_with_unsaved():
                    return
        self._current_page_key = page_key
        self._stack.setCurrentWidget(self._page_widgets[page_key])

        for key, btn in self._nav_buttons.items():
            btn.setProperty("active", key == page_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if page_key in ("car_detail", "build_detail", "tune_detail", "record", "upgrade_store", "run_detail"):
            self._back_bar.show()
        else:
            self._back_bar.hide()

    def _edit_car(self, car_id: str) -> None:
        if not isinstance(car_id, str) or not car_id:
            return
        car = self._data.get_car(car_id)
        if not car:
            return
        dialog = CarEditDialog(car, self)
        if dialog.exec() == CarEditDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                self._data.update_car(car_id, result)
                self._cars_page._build()

    def _enter_car(self, car_id: str) -> None:
        if not isinstance(car_id, str) or not car_id:
            return
        self._current_car_id = car_id
        car = self._data.get_car(car_id)
        if car:
            self._back_title.setText(car.get("display_name", ""))
        self._car_detail_page.load_car(car_id)
        self._navigate("car_detail")

    def _enter_build(self, build_id: str) -> None:
        if not isinstance(build_id, str) or not build_id:
            return
        self._current_build_id = build_id
        build = self._data.get_build_detail(build_id)
        if build:
            self._current_car_id = str(build.get("car_id") or self._current_car_id)
            self._back_title.setText(f"Build: {build.get('display_name', '')}")
        self._build_detail_page.load_build(build_id)
        self._navigate("build_detail")

    def _enter_tune(self, tune_id: str) -> None:
        if not isinstance(tune_id, str) or not tune_id:
            return
        self._current_tune_id = tune_id
        tune = self._data.get_tune_detail(tune_id)
        if tune:
            build = tune.get("build") or {}
            car = tune.get("car") or {}
            self._current_build_id = str(build.get("build_id") or self._current_build_id)
            self._current_car_id = str(car.get("car_id") or self._current_car_id)
            self._back_title.setText(f"Tune: {tune.get('display_name', '')}")
        self._tune_detail_page.load_tune(tune_id)
        self._navigate("tune_detail")

    def _enter_record(
        self,
        car_id: str,
        build_id: str | None = None,
        tune_id: str | None = None,
        setup_snapshot_id: str | None = None,
        entry_mode: str | None = None,
    ) -> None:
        if not isinstance(car_id, str) or not car_id:
            return
        self._current_car_id = car_id
        resolved_mode = entry_mode or ("existing" if build_id else "new")
        effective_build_id = build_id or ""
        effective_tune_id = tune_id or ""
        effective_setup_snapshot_id = setup_snapshot_id or ""
        if resolved_mode == "existing" and build_id:
            self._current_build_id = build_id
        else:
            self._current_build_id = ""
        if resolved_mode == "existing" and tune_id:
            self._current_tune_id = tune_id
        else:
            self._current_tune_id = ""
        if resolved_mode == "existing" and setup_snapshot_id:
            self._current_setup_snapshot_id = setup_snapshot_id
        else:
            self._current_setup_snapshot_id = ""
        car = self._data.get_car(car_id)
        if car:
            self._back_title.setText(f"记录: {car.get('display_name', '')}")
        self._record_run_page.load_car(
            car_id,
            build_id=effective_build_id,
            tune_id=effective_tune_id,
            setup_snapshot_id=effective_setup_snapshot_id,
        )
        self._navigate("record")


    def _enter_upgrade_store(
        self,
        build_id: str,
        upgrade_category_id: str | None = None,
        source_context: str = "build_detail",
    ) -> None:
        """Navigate to the Upgrade Store for a build's category."""
        if not isinstance(build_id, str) or not build_id:
            return
        self._current_build_id = build_id
        self._upgrade_store_source = source_context
        self._back_title.setText("Upgrade Store")
        if upgrade_category_id:
            self._upgrade_store_page.load_store(build_id, upgrade_category_id, source_context=source_context)
        else:
            self._upgrade_store_page.load_store(build_id, source_context=source_context)
        self._navigate("upgrade_store")

    def _on_upgrade_saved(self, build_id: str) -> None:
        # Keep record wizard summaries in sync when edits happen inside upgrade store.
        if self._current_page_key == "upgrade_store":
            tune_id = self._record_run_page.current_tune_id() if hasattr(self._record_run_page, "current_tune_id") else ""
            if hasattr(self._record_run_page, "ensure_build_selected"):
                self._record_run_page.ensure_build_selected(build_id)
            self._record_run_page._sync_dependent_combos()
            auto_tune_id = ""
            if hasattr(self._record_run_page, "on_upgrade_saved_from_store"):
                auto_tune_id = self._record_run_page.on_upgrade_saved_from_store()
            if tune_id and hasattr(self._record_run_page, "ensure_tune_selected"):
                self._record_run_page.ensure_tune_selected(tune_id)
            if auto_tune_id:
                self._enter_tune(auto_tune_id)


    def _enter_run(self, session_id: str) -> None:
        if not isinstance(session_id, str) or not session_id:
            return
        self._back_title.setText("Run Detail")
        self._run_detail_page.load_run(session_id)
        self._navigate("run_detail")

    def _go_back(self) -> None:
        current = self._current_page_key
        if current == "car_detail":
            self._navigate("cars")
        elif current == "build_detail":
            self._enter_car(self._current_car_id)
        elif current == "tune_detail":
            self._enter_build(self._current_build_id)
        elif current == "record":
            if hasattr(self._record_run_page, "confirm_leave_with_unsaved"):
                if not self._record_run_page.confirm_leave_with_unsaved():
                    return
            self._enter_car(self._current_car_id)
        elif current == "upgrade_store":
            if self._upgrade_store_source == "record":
                self._navigate("record")
            else:
                self._enter_build(self._current_build_id)
        elif current == "run_detail":
            self._navigate("runs")
