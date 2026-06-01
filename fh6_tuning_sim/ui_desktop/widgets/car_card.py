from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CarCard(QFrame):
    """Vehicle card widget showing car summary with action buttons."""

    def __init__(
        self,
        car_data: dict,
        on_enter: callable | None = None,
        on_record: callable | None = None,
        on_edit: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._car_data = car_data
        self._on_enter = on_enter
        self._on_record = on_record
        self._on_edit = on_edit
        self._build()

    def _build(self) -> None:
        self.setObjectName("carCard")
        self.setStyleSheet(self._style())
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Top row: name + PI badge
        top = QHBoxLayout()
        name = QLabel(self._car_data.get("display_name", "未命名车辆"))
        name.setObjectName("carCardName")
        name.setStyleSheet("font-size: 16px; font-weight: 600; color: #111111;")
        top.addWidget(name)
        top.addStretch()

        drivetrain_label = self._car_data.get("drivetrain_label", "")
        if drivetrain_label:
            dt_badge = QLabel(drivetrain_label)
            dt_badge.setStyleSheet(
                "background: #e8f0ea; color: #2f6f65; padding: 2px 10px; "
                "border-radius: 4px; font-size: 12px; font-weight: 500;"
            )
            top.addWidget(dt_badge)
        layout.addLayout(top)

        # Stats row
        stats = QHBoxLayout()
        stats.setSpacing(20)
        run_count = self._car_data.get("run_count", 0)
        group_count = self._car_data.get("dataset_group_count", 0)
        readiness = self._car_data.get("avg_modeling_readiness", 0.0)
        quality = self._car_data.get("avg_quality_score", 0.0)

        for label_text in [
            f"记录 {run_count}",
            f"数据集组 {group_count}",
            f"建模准备度 {readiness:.0f}%",
            f"质量 {quality:.0f}%",
        ]:
            stat_label = QLabel(label_text)
            stat_label.setStyleSheet("font-size: 12px; color: #555555;")
            stats.addWidget(stat_label)
        stats.addStretch()
        layout.addLayout(stats)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(8)

        enter_btn = QPushButton("进入车辆")
        enter_btn.setObjectName("carCardEnterBtn")
        enter_btn.setCursor(Qt.PointingHandCursor)
        enter_btn.setStyleSheet(
            "QPushButton { background: #2f6f65; color: white; border: none; "
            "border-radius: 6px; padding: 6px 18px; font-size: 13px; }"
            "QPushButton:hover { background: #255b53; }"
        )
        if self._on_enter:
            enter_btn.clicked.connect(self._on_enter)
        actions.addWidget(enter_btn)

        record_btn = QPushButton("开始记录")
        record_btn.setObjectName("carCardRecordBtn")
        record_btn.setCursor(Qt.PointingHandCursor)
        record_btn.setStyleSheet(
            "QPushButton { background: #f5f5f5; color: #111111; border: 1px solid #d5d5d5; "
            "border-radius: 6px; padding: 6px 18px; font-size: 13px; }"
            "QPushButton:hover { background: #e8e8e8; }"
        )
        if self._on_record:
            record_btn.clicked.connect(self._on_record)
        actions.addWidget(record_btn)


        edit_btn = QPushButton("编辑")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(
            "QPushButton { background: #ffffff; color: #555555; border: 1px solid #d5d5d5; "
            "border-radius: 6px; padding: 6px 18px; font-size: 13px; }"
            "QPushButton:hover { background: #f0f0f0; }"
        )
        if self._on_edit:
            edit_btn.clicked.connect(self._on_edit)
        actions.addWidget(edit_btn)

        actions.addStretch()
        layout.addLayout(actions)

    @staticmethod
    def _style() -> str:
        return (
            "#carCard {"
            "  background: #ffffff;"
            "  border: 1px solid #e0e0e0;"
            "  border-radius: 8px;"
            "}"
        )
