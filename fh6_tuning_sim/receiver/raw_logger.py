from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any, TextIO

from fh6_tuning_sim.config import write_json


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_session_id(prefix: str | None = None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not prefix:
        return timestamp
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in prefix)
    return f"{timestamp}_{safe.strip('_')}"


class TelemetryCsvLogger:
    def __init__(
        self,
        *,
        raw_dir: str | Path,
        sessions_dir: str | Path,
        session_id: str,
        metadata: dict[str, Any],
        tune_config_path: str | Path | None = None,
        flush_every: int = 120,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.sessions_dir = Path(sessions_dir)
        self.session_id = session_id
        self.metadata = dict(metadata)
        self.tune_config_path = Path(tune_config_path) if tune_config_path else None
        self.flush_every = max(1, flush_every)

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.csv_path = self.raw_dir / f"{session_id}.csv"
        self.metadata_path = self.sessions_dir / f"{session_id}_meta.json"
        self.tune_snapshot_path = self.sessions_dir / f"{session_id}_tune.json"

        self._handle: TextIO | None = None
        self._writer: csv.DictWriter[str] | None = None
        self.rows_written = 0
        self._last_timestamp_ms: float | None = None
        self._last_race_time_ms: float | None = None
        self._last_current_lap: float | None = None
        self._last_lap_number: float | None = None
        self._session_elapsed_seconds = 0.0
        self._detected_lap_id = 1
        self._lap_start_elapsed_seconds = 0.0

    def __enter__(self) -> "TelemetryCsvLogger":
        self.open()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def open(self) -> None:
        if self._handle is not None:
            return

        self.metadata.setdefault("session_id", self.session_id)
        self.metadata.setdefault("started_at_utc", utc_now_iso())
        self.metadata.setdefault("raw_csv", str(self.csv_path))
        write_json(self.metadata_path, self.metadata)

        if self.tune_config_path and self.tune_config_path.exists():
            shutil.copyfile(self.tune_config_path, self.tune_snapshot_path)

        self._handle = self.csv_path.open("w", encoding="utf-8", newline="")

    def write_row(
        self,
        telemetry: dict[str, Any],
        *,
        source_ip: str | None = None,
        source_port: int | None = None,
    ) -> None:
        if self._handle is None:
            self.open()

        row = {
            "received_at_utc": utc_now_iso(),
            "source_ip": source_ip,
            "source_port": source_port,
            "sample_index": self.rows_written,
            **telemetry,
        }

        if self._writer is None:
            self._writer = csv.DictWriter(self._handle, fieldnames=list(row.keys()))
            self._writer.writeheader()

        self._writer.writerow(row)
        self.rows_written += 1

        if self.rows_written % self.flush_every == 0:
            self._handle.flush()

    @staticmethod
    def _float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _add_platform_timing_fields(self, telemetry: dict[str, Any]) -> dict[str, Any]:
        timestamp_ms = self._float(telemetry.get("timestamp_ms"))
        race_time_ms = None
        current_race_time = self._float(telemetry.get("current_race_time"))
        if current_race_time is not None:
            race_time_ms = current_race_time * 1000.0

        dt_ms = 0.0
        if self.rows_written > 0:
            timestamp_diff = (
                timestamp_ms - self._last_timestamp_ms
                if timestamp_ms is not None and self._last_timestamp_ms is not None
                else None
            )
            race_time_diff = (
                race_time_ms - self._last_race_time_ms
                if race_time_ms is not None and self._last_race_time_ms is not None
                else None
            )
            dt_ms = timestamp_diff if timestamp_diff is not None and 0 <= timestamp_diff <= 5000 else race_time_diff
            if dt_ms is None or dt_ms < 0 or dt_ms > 5000:
                dt_ms = 0.0
            self._session_elapsed_seconds += dt_ms / 1000.0

        current_lap = self._float(telemetry.get("current_lap"))
        lap_number = self._float(telemetry.get("lap_number"))
        lap_reset = (
            self._last_current_lap is not None
            and current_lap is not None
            and self._last_current_lap > 5.0
            and current_lap <= 3.0
            and current_lap - self._last_current_lap < -2.0
        )
        lap_number_increase = (
            self._last_lap_number is not None
            and lap_number is not None
            and lap_number > self._last_lap_number
        )
        detected_lap_reset = self.rows_written > 0 and (lap_reset or lap_number_increase)
        if detected_lap_reset:
            self._detected_lap_id += 1
            self._lap_start_elapsed_seconds = self._session_elapsed_seconds

        speed = self._float(telemetry.get("speed")) or 0.0
        is_race_on = self._float(telemetry.get("is_race_on")) or 0.0
        stopped = speed <= 0.1
        state_tags: list[str] = []
        if stopped and is_race_on > 0:
            state_tags.append("idle")
        if stopped:
            state_tags.append("stopped")
        if dt_ms > 250:
            state_tags.append("recording_gap")
        if is_race_on <= 0 and stopped:
            state_tags.append("possible_pause")
        if is_race_on <= 0:
            state_tags.append("menu_or_no_data")

        self._last_timestamp_ms = timestamp_ms
        self._last_race_time_ms = race_time_ms
        self._last_current_lap = current_lap
        self._last_lap_number = lap_number

        enriched = dict(telemetry)
        enriched.update(
            {
                "sample_index": self.rows_written,
                "timestamp_ms_raw": timestamp_ms,
                "session_elapsed_seconds": round(self._session_elapsed_seconds, 6),
                "current_race_time_raw": current_race_time,
                "current_lap_raw": current_lap,
                "lap_number_raw": lap_number,
                "detected_lap_id": self._detected_lap_id,
                "detected_lap_elapsed_seconds": round(
                    self._session_elapsed_seconds - self._lap_start_elapsed_seconds,
                    6,
                ),
                "detected_lap_reset": detected_lap_reset,
                "state_idle": "idle" in state_tags,
                "state_stopped": "stopped" in state_tags,
                "state_possible_pause": "possible_pause" in state_tags,
                "state_recording_gap": "recording_gap" in state_tags,
                "state_menu_or_no_data": "menu_or_no_data" in state_tags,
                "run_state_tags": ",".join(state_tags),
            }
        )
        return enriched

    def close(self) -> None:
        if self._handle is None:
            return

        self.metadata["ended_at_utc"] = utc_now_iso()
        self.metadata["rows_written"] = self.rows_written
        write_json(self.metadata_path, self.metadata)

        self._handle.flush()
        self._handle.close()
        self._handle = None
