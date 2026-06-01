from __future__ import annotations

import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from fh6_tuning_sim.db.connection import transaction
from fh6_tuning_sim.receiver.packet_parser import FIELD_NAMES, FIELD_SPECS, PACKET_STRUCT, parse_packet
from fh6_tuning_sim.receiver.raw_logger import TelemetryCsvLogger
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService

try:
    from fh6_tuning_sim.ui_desktop.services.recording_worker import RecordingWorker
except ImportError as exc:  # pragma: no cover - environment gate
    if "PySide6" not in str(exc) and "QtCore" not in str(exc):
        raise
    RecordingWorker = None


class V101RecordingFlowDemoTests(unittest.TestCase):
    def test_udp_recording_flow_promotes_build_card_after_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = DesktopDataService(root=root, db_path=root / "demo.db")
            self._seed_minimum_catalog(service)

            car = service.cars.create_car(
                {
                    "car_id": "car_v101_demo",
                    "display_name": "V101 Demo Car",
                    "default_car_class": "S2",
                    "stock_pi": 900,
                    "default_drivetrain": "awd",
                }
            )
            build = service.create_new_recording_build(str(car["car_id"]))
            build_id = str(build["build_id"])
            tune = service.tunes.ensure_baseline_tune(build_id)
            tune_id = str(tune["tune_id"])

            category_id = str(service.get_upgrade_categories(build_id)[0]["upgrade_category_id"])
            slots = service.get_upgrade_slots_for_category(category_id, build_id)
            self.assertTrue(slots)
            slot_id = str(slots[0]["slot_id"])
            options = service.get_upgrade_options_for_slot(slot_id, build_id)
            sport = next(item for item in options if item.get("option_key") == "sport_intake")
            service.save_build_upgrade_selection(build_id, slot_id, str(sport["upgrade_option_id"]))

            params = service.tune_parameters.list_values(tune_id)
            self.assertTrue(params)
            first = params[0]
            service.save_tune_parameter_values(
                tune_id,
                [
                    {
                        "tune_parameter_id": first["tune_parameter_id"],
                        "value_text": "1.5",
                        "value_real": 1.5,
                    }
                ],
            )

            snapshot = service.snapshots.ensure_default_setup_snapshot(str(car["car_id"]), build_id, tune_id)
            snapshot_id = str(snapshot["setup_snapshot_id"])
            self.assertTrue(service.confirm_setup_snapshot(snapshot_id, [{"data_key": "horsepower", "label_zh": "马力", "value": "500", "unit": "PS"}]))

            packet_count = self._record_udp_packets(root, "v101_demo_session")
            self.assertGreater(packet_count, 0)
            csv_path = root / "raw" / "v101_demo_session.csv"
            self.assertTrue(csv_path.exists())

            run = service.create_run_from_recording(
                session_id="v101_demo_session",
                csv_path=str(csv_path),
                context={
                    "car_id": str(car["car_id"]),
                    "build_id": build_id,
                    "tune_id": tune_id,
                    "setup_snapshot_id": snapshot_id,
                    "route_mode": "free_drive",
                    "record_type": "normal_recording",
                    "intent_tags": [],
                },
                packet_count=packet_count,
                duration_seconds=1.0,
            )
            self.assertEqual(run["build_id"], build_id)
            self.assertEqual(run["tune_id"], tune_id)
            self.assertEqual(run["setup_snapshot_id"], snapshot_id)

            visible_build_ids = {item["build_id"] for item in service.list_builds_for_car(str(car["car_id"]))}
            self.assertIn(build_id, visible_build_ids)
            self.assertEqual(service.list_runs_for_build(build_id)[0]["session_id"], "v101_demo_session")

            service.cleanup_draft_builds_without_runs(str(car["car_id"]))
            visible_after_cleanup = {item["build_id"] for item in service.list_builds_for_car(str(car["car_id"]))}
            self.assertIn(build_id, visible_after_cleanup)

    def _seed_minimum_catalog(self, service: DesktopDataService) -> None:
        service.routes_repo.create_route(
            {
                "route_id": "route_free_drive",
                "route_key": "free_drive",
                "display_name": "自由驾驶",
                "route_mode": "free_drive",
            }
        )
        category = service.add_upgrade_category("demo_engine", "引擎", display_order=1)
        category_id = str(category["upgrade_category_id"])
        slot = service.add_upgrade_slot(category_id, "intake", "进气系统", sort_order=1)
        slot_id = str(slot["slot_id"])
        service.add_upgrade_option(category_id, slot_id, "stock_intake", "原厂进气", is_stock=True)
        service.add_upgrade_option(category_id, slot_id, "sport_intake", "运动进气", default_pi_delta=3, tier=1)
        with transaction(service.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tune_sections (section_id, section_key, label_zh, label_en, sort_order, is_active)
                VALUES ('section_tires', 'tires', '轮胎', 'Tires', 1, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO tune_parameter_definitions (
                    tune_parameter_id, parameter_key, category, label_zh, label_en, unit,
                    min_value, max_value, step, value_type, is_enabled, display_order, section_id
                ) VALUES (
                    'param_front_pressure', 'front_pressure', 'tires', '前侧胎压', 'Front Tire Pressure', 'atm',
                    1.0, 3.8, 0.1, 'float', 1, 1, 'section_tires'
                )
                """
            )

    def _record_udp_packets(self, root: Path, session_id: str) -> int:
        if RecordingWorker is None:
            return self._record_udp_packets_without_qt(root, session_id)
        packet_count = 8
        port_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        port_sock.bind(("127.0.0.1", 0))
        port = port_sock.getsockname()[1]
        port_sock.close()

        worker = RecordingWorker(
            host="127.0.0.1",
            port=port,
            session_id=session_id,
            raw_dir=str(root / "raw"),
            sessions_dir=str(root / "sessions"),
        )
        thread = threading.Thread(target=worker.start_recording, daemon=True)
        thread.start()
        time.sleep(0.2)

        packet = self._demo_packet()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            for _ in range(packet_count):
                sender.sendto(packet, ("127.0.0.1", port))
                time.sleep(0.01)
        time.sleep(0.1)
        worker.stop_recording()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        return packet_count

    def _record_udp_packets_without_qt(self, root: Path, session_id: str) -> int:
        packet_count = 8
        received = 0
        ready = threading.Event()
        done = threading.Event()
        port_holder: list[int] = []

        def receiver() -> None:
            nonlocal received
            logger = TelemetryCsvLogger(
                raw_dir=root / "raw",
                sessions_dir=root / "sessions",
                session_id=session_id,
                metadata={"session_id": session_id, "demo": "v1.0.1"},
            )
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(("127.0.0.1", 0))
                sock.settimeout(2.0)
                port_holder.append(sock.getsockname()[1])
                ready.set()
                logger.open()
                while received < packet_count:
                    packet, address = sock.recvfrom(2048)
                    logger.write_row(parse_packet(packet), source_ip=address[0], source_port=address[1])
                    received += 1
                logger.close()
                done.set()

        thread = threading.Thread(target=receiver, daemon=True)
        thread.start()
        self.assertTrue(ready.wait(timeout=3))
        packet = self._demo_packet()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            for _ in range(packet_count):
                sender.sendto(packet, ("127.0.0.1", port_holder[0]))
                time.sleep(0.01)
        self.assertTrue(done.wait(timeout=5))
        thread.join(timeout=5)
        self.assertEqual(received, packet_count)
        return received

    def _demo_packet(self) -> bytes:
        values = []
        for field in FIELD_SPECS:
            if field.type_code == "F32":
                values.append(0.0)
            elif field.type_code == "U32":
                values.append(1)
            else:
                values.append(0)
        values[FIELD_NAMES.index("is_race_on")] = 1
        values[FIELD_NAMES.index("speed")] = 42.5
        values[FIELD_NAMES.index("current_engine_rpm")] = 6500.0
        return PACKET_STRUCT.pack(*values)


if __name__ == "__main__":
    unittest.main()
