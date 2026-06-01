from __future__ import annotations

import socket
import time
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from fh6_tuning_sim.receiver.packet_parser import (
    PACKET_SIZE,
    PacketLengthError,
    parse_packet,
)
from fh6_tuning_sim.receiver.raw_logger import TelemetryCsvLogger, make_session_id
from fh6_tuning_sim.runtime_paths import data_path

DEFAULT_RAW_DIR = str(data_path("raw"))
DEFAULT_SESSIONS_DIR = str(data_path("sessions"))


class RecordingWorker(QObject):
    """Worker object for UDP recording, designed to run in a QThread.

    Reuses TelemetryCsvLogger and packet_parser from the existing pipeline.
    Does NOT rewrite the UDP listener. Emits signals for UI updates.
    """

    status_changed = Signal(str)
    packet_count_changed = Signal(int)
    elapsed_changed = Signal(float)
    session_ready = Signal(str, str)  # session_id, csv_path
    error_occurred = Signal(str)

    _STATUS_IDLE = "未开始"
    _STATUS_WAITING = "等待数据"
    _STATUS_RECORDING = "记录中"
    _STATUS_STOPPED = "已停止"
    _STATUS_ERROR = "错误"

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 9999,
        session_prefix: str | None = None,
        session_id: str | None = None,
        raw_dir: str = DEFAULT_RAW_DIR,
        sessions_dir: str = DEFAULT_SESSIONS_DIR,
        metadata: dict | None = None,
        tune_config_path: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._host = host
        self._port = port
        self._session_prefix = session_prefix
        self._session_id = session_id
        self._raw_dir = raw_dir
        self._sessions_dir = sessions_dir
        self._metadata = dict(metadata or {})
        self._tune_config_path = tune_config_path

        self._stop_flag = False
        self._packet_count = 0
        self._dropped_count = 0
        self._start_time = 0.0
        self._logger: TelemetryCsvLogger | None = None
        self._sock: socket.socket | None = None

    @Slot()
    def start_recording(self) -> None:
        self._stop_flag = False
        self._packet_count = 0
        self._dropped_count = 0

        sid = self._session_id or make_session_id(self._session_prefix)
        self._session_id = sid

        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.bind((self._host, self._port))
            self._sock.settimeout(1.0)
        except OSError as exc:
            self.error_occurred.emit(f"无法绑定 {self._host}:{self._port}: {exc}")
            self.status_changed.emit(self._STATUS_ERROR)
            return

        metadata = dict(self._metadata)
        metadata.setdefault("session_id", sid)
        metadata.setdefault("started_at_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        metadata.setdefault("data_out_host", self._host)
        metadata.setdefault("data_out_port", self._port)
        metadata.setdefault("packet_size_bytes", PACKET_SIZE)

        self._logger = TelemetryCsvLogger(
            raw_dir=self._raw_dir,
            sessions_dir=self._sessions_dir,
            session_id=sid,
            metadata=metadata,
            tune_config_path=Path(self._tune_config_path) if self._tune_config_path else None,
        )
        self._logger.open()

        self._start_time = time.monotonic()
        self.status_changed.emit(self._STATUS_WAITING)

        # Main receive loop
        while not self._stop_flag:
            try:
                packet, address = self._sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError as exc:
                self.error_occurred.emit(f"Socket 错误: {exc}")
                break

            try:
                telemetry = parse_packet(packet, strict_size=True)
            except PacketLengthError:
                self._dropped_count += 1
                continue

            self._logger.write_row(
                telemetry,
                source_ip=address[0],
                source_port=address[1],
            )
            self._packet_count += 1

            if self._packet_count == 1:
                self.status_changed.emit(self._STATUS_RECORDING)

            # Emit updates every 30 packets to avoid flooding the UI
            if self._packet_count % 30 == 0:
                self.packet_count_changed.emit(self._packet_count)
                elapsed = max(time.monotonic() - self._start_time, 0.001)
                self.elapsed_changed.emit(elapsed)

        # Finishing
        self._finalize()

    def _finalize(self) -> None:
        had_packets = self._packet_count > 0

        if self._logger is not None:
            self._logger.close()
            self._logger = None

        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

        # Emit final counts
        self.packet_count_changed.emit(self._packet_count)
        elapsed = max(time.monotonic() - self._start_time, 0.0)
        self.elapsed_changed.emit(elapsed)

        if not had_packets and not self._stop_flag:
            self.status_changed.emit(self._STATUS_WAITING)
            return

        self.status_changed.emit(self._STATUS_STOPPED)

        sid = self._session_id or ""
        csv_path = str(Path(self._raw_dir) / f"{sid}.csv") if sid else ""
        self.session_ready.emit(sid, csv_path)

    @Slot()
    def stop_recording(self) -> None:
        self._stop_flag = True
