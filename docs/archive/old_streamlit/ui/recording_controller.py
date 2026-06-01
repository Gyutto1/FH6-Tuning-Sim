from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import socket
import threading
import time
from typing import Any

import pandas as pd

from fh6_tuning_sim.analysis.feature_engineering import add_features, write_processed
from fh6_tuning_sim.analysis.report_generator import generate_report
from fh6_tuning_sim.config import write_json
from fh6_tuning_sim.data_management.run_index import index_session
from fh6_tuning_sim.receiver.packet_parser import PACKET_SIZE, PacketLengthError, parse_packet
from fh6_tuning_sim.receiver.raw_logger import TelemetryCsvLogger
from fh6_tuning_sim.visualization.plot_timeseries import plot_timeseries


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SESSIONS_DIR = ROOT / "data" / "sessions"
REPORTS_DIR = ROOT / "reports"
DATASETS_DIR = ROOT / "data" / "datasets"


@dataclass
class RecordingState:
    status: str = "Stopped"
    session_id: str | None = None
    packet_count: int = 0
    dropped_count: int = 0
    start_time: float | None = None
    end_time: float | None = None
    csv_path: str | None = None
    error: str | None = None
    latest: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.monotonic()
        return max(end - self.start_time, 0.0)

    @property
    def sample_rate(self) -> float:
        duration = self.duration_seconds
        return self.packet_count / duration if duration > 0 else 0.0


class RecordingController:
    def __init__(self) -> None:
        self.state = RecordingState()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def snapshot(self) -> RecordingState:
        with self._lock:
            return RecordingState(
                status=self.state.status,
                session_id=self.state.session_id,
                packet_count=self.state.packet_count,
                dropped_count=self.state.dropped_count,
                start_time=self.state.start_time,
                end_time=self.state.end_time,
                csv_path=self.state.csv_path,
                error=self.state.error,
                latest=dict(self.state.latest),
            )

    def is_running(self) -> bool:
        return self.snapshot().status in {"Listening", "Recording"}

    def start(self, config: dict[str, Any]) -> None:
        if self.is_running():
            raise RuntimeError("Recording is already running")

        for path in [RAW_DIR, PROCESSED_DIR, SESSIONS_DIR, REPORTS_DIR, DATASETS_DIR]:
            path.mkdir(parents=True, exist_ok=True)

        self._stop_event.clear()
        with self._lock:
            self.state = RecordingState(
                status="Listening",
                session_id=config["session_id"],
                start_time=time.monotonic(),
                csv_path=str(RAW_DIR / f"{config['session_id']}.csv"),
            )

        self._thread = threading.Thread(
            target=self._run_listener,
            args=(dict(config),),
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        with self._lock:
            if self.state.status != "Error":
                self.state.status = "Stopped"
            self.state.end_time = time.monotonic()

    def _run_listener(self, config: dict[str, Any]) -> None:
        session_id = config["session_id"]
        host = config.get("host", "127.0.0.1")
        port = int(config.get("port", 9999))
        metadata = dict(config.get("metadata", {}))
        tune_config = dict(config.get("tune_config", {}))
        tune_input_path = SESSIONS_DIR / f"{session_id}_tune_input.json"
        write_json(tune_input_path, tune_config)

        metadata.update(
            {
                "session_id": session_id,
                "data_out_host": host,
                "data_out_port": port,
                "packet_size_bytes": PACKET_SIZE,
                "started_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind((host, port))
                sock.settimeout(0.25)

                with TelemetryCsvLogger(
                    raw_dir=RAW_DIR,
                    sessions_dir=SESSIONS_DIR,
                    session_id=session_id,
                    metadata=metadata,
                    tune_config_path=tune_input_path,
                    flush_every=120,
                ) as logger:
                    while not self._stop_event.is_set():
                        try:
                            packet, address = sock.recvfrom(2048)
                        except socket.timeout:
                            continue

                        try:
                            telemetry = parse_packet(packet)
                        except PacketLengthError:
                            with self._lock:
                                self.state.dropped_count += 1
                            continue

                        logger.write_row(
                            telemetry,
                            source_ip=address[0],
                            source_port=address[1],
                        )
                        with self._lock:
                            self.state.status = "Recording"
                            self.state.packet_count = logger.rows_written
                            self.state.csv_path = str(logger.csv_path)
                            self.state.latest = telemetry

            with self._lock:
                self.state.status = "Stopped"
                self.state.end_time = time.monotonic()

            if (RAW_DIR / f"{session_id}.csv").exists():
                index_session(session_id)

        except Exception as exc:
            with self._lock:
                self.state.status = "Error"
                self.state.error = str(exc)
                self.state.end_time = time.monotonic()


def process_session(
    session_id: str,
    *,
    run_feature_engineering: bool = True,
    generate_plot: bool = True,
    generate_report: bool = True,
) -> dict[str, str]:
    outputs: dict[str, str] = {}
    raw_path = RAW_DIR / f"{session_id}.csv"
    processed_path = PROCESSED_DIR / f"{session_id}_processed.csv"
    metadata_path = SESSIONS_DIR / f"{session_id}_meta.json"
    tune_path = SESSIONS_DIR / f"{session_id}_tune.json"
    plot_path = REPORTS_DIR / f"{session_id}_timeseries.png"
    report_path = REPORTS_DIR / f"{session_id}_report.md"

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw CSV not found: {raw_path}")

    if run_feature_engineering or not processed_path.exists():
        raw = pd.read_csv(raw_path)
        processed = add_features(raw)
        write_processed(processed, processed_path)
        outputs["processed_csv"] = str(processed_path)

    frame = pd.read_csv(processed_path if processed_path.exists() else raw_path)

    if generate_plot:
        plot_timeseries(frame, plot_path)
        outputs["plot"] = str(plot_path)

    if generate_report:
        from fh6_tuning_sim.config import load_json

        metadata = load_json(metadata_path, required=False)
        tune = load_json(tune_path, required=False)
        report = generate_report(frame, metadata=metadata, tune_config=tune)
        report_path.write_text(report, encoding="utf-8")
        outputs["report"] = str(report_path)

    index_session(session_id)
    return outputs

