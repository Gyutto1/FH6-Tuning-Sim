from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QFormLayout, QMessageBox,
)

from fh6_tuning_sim.ui_desktop.pages.setup_snapshot_confirm_page import SetupSnapshotConfirmPage
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.widgets.section_header import SectionHeader


class RunDetailPage(QWidget):
    """Show full run detail with frozen snapshot data from freeze tables."""

    def __init__(
        self,
        data_service: DesktopDataService,
        on_back: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("runDetailPage")
        self._data = data_service
        self._on_back = on_back
        self._run_id = ""
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
        self._layout.setSpacing(8)
        scroll.setWidget(self._content)
        root.addWidget(scroll)

    def load_run(self, run_id: str) -> None:
        self._run_id = run_id
        self._refresh()

    def _refresh(self) -> None:
        self._clear()

        if self._on_back:
            back = QPushButton("← 返回 Run Library")
            back.setCursor(Qt.PointingHandCursor)
            back.setStyleSheet(
                "QPushButton { background: transparent; color: #2f6f65; border: none; font-size: 13px; }"
                "QPushButton:hover { text-decoration: underline; }"
            )
            back.clicked.connect(lambda: self._on_back())
            self._layout.addWidget(back)

        try:
            run_detail = self._data.get_run_detail(self._run_id)
        except AttributeError:
            run_detail = self._data.runs_repo.get_run(self._run_id)

        if not run_detail:
            self._layout.addWidget(QLabel("Run 未找到"))
            return

        metrics_probe = run_detail.get("metrics_json")
        if self._data.metrics_need_unit_refresh(metrics_probe):
            self._data.recompute_run_metrics(self._run_id)
            refreshed = self._data.get_run_detail(self._run_id)
            if refreshed:
                run_detail = refreshed

        # Run info header
        self._layout.addWidget(SectionHeader(
            self._data.run_display_title(run_detail),
            f"session: {run_detail.get('session_id', '-')}"
        ))

        # Basic info
        basic = QGroupBox("基本信息")
        basic.setStyleSheet(self._group_style())
        bf = QFormLayout(basic)
        bf.setSpacing(4)
        bf.setContentsMargins(10, 8, 10, 8)
        bf.addRow("时长", QLabel(f"{float(run_detail.get('duration_seconds') or 0):.0f}s"))
        bf.addRow("创建时间", QLabel(str(run_detail.get('created_at_utc', '-'))))
        bf.addRow("备注", QLabel(str(run_detail.get('notes', '-'))))
        self._layout.addWidget(basic)

        # Context info
        ctx = QGroupBox("记录上下文")
        ctx.setStyleSheet(self._group_style())
        cf = QFormLayout(ctx)
        cf.setSpacing(4)
        cf.setContentsMargins(10, 8, 10, 8)
        cf.addRow("车辆", QLabel(str(run_detail.get('car_name', '-'))))
        cf.addRow("Build", QLabel(str(run_detail.get('build_name', '-'))))
        cf.addRow("Tune", QLabel(str(run_detail.get('tune_name', '-'))))
        cf.addRow("Snapshot", QLabel(str(run_detail.get('setup_snapshot_name', '-'))))
        cf.addRow("路线", QLabel(str(run_detail.get('route_name', '-'))))
        cf.addRow("路线模式", QLabel(self._data.label_route_mode(run_detail.get('route_mode'))))
        cf.addRow("记录类型", QLabel(self._data.label_record_type(run_detail.get('record_type'))))
        self._layout.addWidget(ctx)

        ownership_lines = self._data.data_ownership_lines() if hasattr(self._data, "data_ownership_lines") else []
        if ownership_lines:
            own_box = QGroupBox("数据归属说明")
            own_box.setStyleSheet(self._group_style())
            own_layout = QVBoxLayout(own_box)
            own_layout.setContentsMargins(10, 8, 10, 8)
            own_layout.setSpacing(4)
            for line in ownership_lines:
                label = QLabel(f"- {line}")
                label.setWordWrap(True)
                own_layout.addWidget(label)
            self._layout.addWidget(own_box)

        # Frozen snapshot data
        snapshot_id = str(run_detail.get('setup_snapshot_id', ''))
        if snapshot_id:
            self._show_frozen_data(snapshot_id)
        metrics_raw = run_detail.get("metrics_json")
        if metrics_raw:
            try:
                metrics = json.loads(metrics_raw) if isinstance(metrics_raw, str) else dict(metrics_raw)
            except Exception:
                metrics = {}
            if metrics:
                box = QGroupBox("性能摘要")
                box.setStyleSheet(self._group_style())
                form = QFormLayout(box)
                form.setSpacing(4)
                form.setContentsMargins(10, 8, 10, 8)
                label_map = {
                    "metrics_units_version": "",
                    "packet_count": "有效包数",
                    "max_speed_kph": "最高速度 km/h",
                    "avg_speed_kph": "平均速度 km/h",
                    "max_rpm": "峰值转速",
                    "avg_rpm": "平均转速",
                    "max_power_ps": "最大功率 PS",
                    "max_torque_nm": "最大扭矩 N·m",
                    "max_longitudinal_g": "最大纵向 G",
                    "max_lateral_g": "最大横向 G",
                    "max_throttle": "最大油门输入",
                    "max_brake": "最大制动输入",
                    "max_tire_slip": "轮胎滑移峰值",
                    "max_tire_temp": "最高轮胎温度",
                    "distance_m": "里程 m",
                }
                hidden_keys = {"metrics_units_version", "max_power_w"}
                known_order = [key for key in label_map if key not in hidden_keys]
                for key in known_order:
                    if key in metrics:
                        form.addRow(label_map[key], QLabel(str(metrics.get(key))))
                for key, value in metrics.items():
                    if key in label_map or key in hidden_keys:
                        continue
                    form.addRow(str(key), QLabel(str(value)))
                self._layout.addWidget(box)

        # Tags
        tag_items = run_detail.get('tag_items', []) or []
        if tag_items:
            tags_box = QGroupBox("意图标签")
            tags_layout = QHBoxLayout(tags_box)
            for item in tag_items:
                chip = QLabel(item.get('label_zh', item.get('tag_key', '')))
                chip.setStyleSheet(
                    "background: #e8f0ea; color: #2f6f65; padding: 4px 10px; "
                    "border-radius: 4px; font-size: 12px;"
                )
                tags_layout.addWidget(chip)
            tags_layout.addStretch()
            self._layout.addWidget(tags_box)

        self._layout.addStretch()

    def _show_frozen_data(self, snapshot_id: str) -> None:
        """Display frozen build, tune, and vehicle data from snapshot."""
        try:
            freeze = self._data._freeze
        except AttributeError:
            return

        build_items = freeze.get_build_items(snapshot_id)
        if build_items:
            box = QGroupBox("冻结的 Build 选择")
            box.setStyleSheet(self._group_style())
            form = QFormLayout(box)
            form.setSpacing(3)
            form.setContentsMargins(10, 8, 10, 8)
            for item in build_items:
                label = f"{item.get('category_label_zh', '')} / {item.get('slot_label_zh', '')}"
                val = item.get('option_label_zh', '-')
                if item.get('pi_delta'):
                    val += f"  (PI {item['pi_delta']})"
                form.addRow(label, QLabel(val))
            self._layout.addWidget(box)

        tune_values = freeze.get_tune_values(snapshot_id)
        if tune_values:
            box = QGroupBox("冻结的 Tune 参数")
            box.setStyleSheet(self._group_style())
            form = QFormLayout(box)
            form.setSpacing(3)
            form.setContentsMargins(10, 8, 10, 8)
            for val in tune_values:
                label = f"{val.get('section_label_zh', '')} / {val.get('parameter_label_zh', '')}"
                v = val.get('value')
                u = val.get('unit', '')
                display = f"{v} {u}".strip() if v is not None else '-'
                form.addRow(label, QLabel(display))
            self._layout.addWidget(box)

        vehicle_data = freeze.get_vehicle_data(snapshot_id)
        if vehicle_data:
            box = QGroupBox("冻结的车辆数据")
            box.setStyleSheet(self._group_style())
            form = QFormLayout(box)
            form.setSpacing(3)
            form.setContentsMargins(10, 8, 10, 8)
            for vd in vehicle_data:
                val = vd.get('value', '-')
                unit = vd.get('unit', '')
                display = f"{val} {unit}".strip()
                form.addRow(vd.get('label_zh', vd.get('data_key', '')), QLabel(display))
            self._layout.addWidget(box)
        else:
            box = QGroupBox("冻结的车辆数据")
            box.setStyleSheet(self._group_style())
            layout = QVBoxLayout(box)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(8)
            note = QLabel("该 Snapshot 尚未冻结车辆数据面板。")
            note.setStyleSheet("font-size: 12px; color: #8a3a3a;")
            layout.addWidget(note)
            self._layout.addWidget(box)

        status = self._data.snapshot_vehicle_data_status(snapshot_id)
        if not status.get("is_complete"):
            note = QLabel(
                f"车辆数据面板未补齐：缺少 {len(status.get('missing_keys') or [])}/{status.get('required_count', 0)} 项。"
            )
            note.setWordWrap(True)
            note.setStyleSheet("font-size: 12px; color: #8a3a3a; padding: 4px;")
            self._layout.addWidget(note)
        fix_btn = QPushButton("进入 Snapshot 补录")
        fix_btn.setCursor(Qt.PointingHandCursor)
        fix_btn.setStyleSheet(
            "QPushButton { background: #f5f5f5; color: #111111; border: 1px solid #cccccc; border-radius: 6px; padding: 6px 12px; }"
            "QPushButton:hover { background: #ebebeb; }"
        )
        fix_btn.clicked.connect(lambda checked=False, sid=snapshot_id: self._open_snapshot_confirm(sid))
        self._layout.addWidget(fix_btn)

    def _open_snapshot_confirm(self, snapshot_id: str) -> None:
        run = self._data.get_run_detail(self._run_id)
        if not run:
            return
        snapshot_run_count = self._data.count_runs_for_snapshot(snapshot_id, include_archived=False)
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
        car_id = str(run.get("car_id") or "")
        build_id = str(run.get("build_id") or "")
        tune_id = str(run.get("tune_id") or "")
        if not (car_id and build_id and tune_id):
            return
        dialog = SetupSnapshotConfirmPage(
            self._data,
            car_id,
            build_id,
            tune_id,
            snapshot_id=snapshot_id or None,
            on_confirmed=lambda sid: self._refresh(),
            parent=self,
            embedded=False,
        )
        dialog.exec()

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _group_style() -> str:
        return (
            "QGroupBox { border: 1px solid #e0e0e0; border-radius: 6px; margin-top: 8px; padding-top: 8px; font-size: 13px; font-weight: 600; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
            "QLabel { font-size: 12px; color: #222222; }"
        )
