from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.car_card import CarCard
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


class CarsPage(QWidget):
    """My Cars page: display vehicles as cards (not tables)."""

    def __init__(
        self,
        data_service: DesktopDataService,
        on_enter_car: callable | None = None,
        on_record_car: callable | None = None,
        on_edit_car: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data = data_service
        self._on_enter_car = on_enter_car
        self._on_record_car = on_record_car
        self._on_edit_car = on_edit_car
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

        layout.addWidget(SectionHeader("车辆库 My Cars", "管理你的车辆和记录"))

        cars = self._data.list_cars()
        if not cars:
            empty = QLabel("暂无车辆。请先通过车辆管理或数据工具添加车辆。")
            empty.setStyleSheet("font-size: 14px; color: #888888; padding: 24px;")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)
        else:
            for car in cars:
                car_id = car.get("car_id", "")
                card = CarCard(
                    car,
                    on_enter=lambda checked=False, cid=car_id: self._handle_enter(cid),
                    on_record=lambda checked=False, cid=car_id: self._handle_record(cid),
                    on_edit=lambda checked=False, cid=car_id: self._handle_edit(cid),
                )
                layout.addWidget(card)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _handle_enter(self, car_id: str) -> None:
        if isinstance(car_id, str) and self._on_enter_car:
            self._on_enter_car(car_id)

    def _handle_edit(self, car_id: str) -> None:
        if isinstance(car_id, str) and self._on_edit_car:
            self._on_edit_car(car_id)

    def _handle_record(self, car_id: str) -> None:
        if isinstance(car_id, str) and self._on_record_car:
            self._on_record_car(car_id)
