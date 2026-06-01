from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from fh6_tuning_sim.db.seed_data.demo_seed import seed_demo_database
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService

try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from fh6_tuning_sim.ui_desktop.pages.record_run_page import RecordRunPage
    from fh6_tuning_sim.ui_desktop.pages.setup_snapshot_confirm_page import SetupSnapshotConfirmPage
except Exception:  # pragma: no cover
    QApplication = None
    RecordRunPage = None
    SetupSnapshotConfirmPage = None


@unittest.skipIf(QApplication is None or RecordRunPage is None or SetupSnapshotConfirmPage is None, "PySide6 not available")
class TestRecordRunPageFlow(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "record_flow.db"
        seed_demo_database(self.db_path)
        self.data = DesktopDataService(db_path=self.db_path)
        self.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_new_record_starts_from_preset_step(self) -> None:
        page = RecordRunPage(self.data)
        page.load_car("car_demo_amg")
        self.assertEqual(page._step, 0)
        self.assertEqual(page._stack.count(), 7)
        self.assertFalse(page._lock_setup_steps)

    def test_existing_build_starts_from_route_tags_segment(self) -> None:
        page = RecordRunPage(self.data)
        page.load_car("car_demo_amg", build_id="build_amg_stock")
        self.assertEqual(page._step, 5)
        self.assertTrue(page._lock_setup_steps)
        self.assertEqual(page._stack.count(), 7)

    def test_snapshot_confirm_requires_all_vehicle_data_fields(self) -> None:
        dialog = SetupSnapshotConfirmPage(
            self.data,
            "car_demo_amg",
            "build_amg_stock",
            "tune_amg_stock_baseline",
            snapshot_id="setup_amg_stock_baseline",
            embedded=True,
        )
        for field in dialog._vehicle_fields.values():
            field.setText("")
        first_key = next(iter(dialog._vehicle_fields))
        dialog._vehicle_fields[first_key].setText("1")
        missing = dialog._missing_vehicle_data_labels()
        self.assertGreater(len(missing), 0)
        for field in dialog._vehicle_fields.values():
            field.setText("1")
        self.assertEqual(dialog._missing_vehicle_data_labels(), [])


if __name__ == "__main__":
    unittest.main()
