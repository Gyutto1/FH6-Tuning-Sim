from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import socket
import sys
import threading
import time
from typing import Callable


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SESSIONS_DIR = ROOT / "data" / "sessions"
REPORTS_DIR = ROOT / "reports"
TUNE_CONFIG = ROOT / "configs" / "tune_config.json"

ANSI = os.environ.get("NO_COLOR") is None


def color(text: str, code: str) -> str:
    if not ANSI:
        return text
    return f"\033[{code}m{text}\033[0m"


def muted(text: str) -> str:
    return color(text, "90")


def cyan(text: str) -> str:
    return color(text, "36")


def green(text: str) -> str:
    return color(text, "32")


def yellow(text: str) -> str:
    return color(text, "33")


def red(text: str) -> str:
    return color(text, "31")


def bold(text: str) -> str:
    return color(text, "1")


def ensure_dirs() -> None:
    for path in [RAW_DIR, PROCESSED_DIR, SESSIONS_DIR, REPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def pause() -> None:
    input("\nPress Enter to return to the menu...")


def input_default(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def optional_int(prompt: str) -> int | None:
    value = input(f"{prompt} [empty = no limit]: ").strip()
    if not value:
        return None
    return int(value)


def optional_float(prompt: str) -> float | None:
    value = input(f"{prompt} [empty = no limit]: ").strip()
    if not value:
        return None
    return float(value)


def format_bytes(size: int | float) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"


def count_csv_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def write_json_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def print_box(title: str, lines: list[str]) -> None:
    width = max([len(title), *(len(line) for line in lines), 24])
    print(cyan("+" + "-" * (width + 2) + "+"))
    print(cyan("| ") + bold(title).ljust(width) + cyan(" |"))
    print(cyan("+" + "-" * (width + 2) + "+"))
    for line in lines:
        print(cyan("| ") + line.ljust(width) + cyan(" |"))
    print(cyan("+" + "-" * (width + 2) + "+"))


def print_kv_table(rows: list[tuple[str, str]]) -> None:
    if not rows:
        return
    key_width = max(len(key) for key, _ in rows)
    for key, value in rows:
        print(f"  {muted(key.ljust(key_width))}  {value}")


def prompt_host_port() -> tuple[str, int]:
    print("\nNetwork binding")
    print("- Bind host is the local IP to listen on. For this project, keep 127.0.0.1.")
    print("- UDP port must match FH6 Data Out Port. Default is 9999.")

    host = input_default("Bind host / local IP", "127.0.0.1")
    port = 9999

    if host.isdigit():
        print(f"Input '{host}' looks like a port, so using it as UDP port.")
        port = int(host)
        host = "127.0.0.1"
    else:
        port = int(input_default("UDP port", "9999"))

    return host, port


def latest_file(directory: Path, pattern: str) -> Path | None:
    files = [path for path in directory.glob(pattern) if path.is_file()]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def latest_real_raw_file() -> Path | None:
    files = [
        path
        for path in RAW_DIR.glob("*.csv")
        if path.is_file() and not path.name.startswith("demo_")
    ]
    if not files:
        return latest_file(RAW_DIR, "*.csv")
    return max(files, key=lambda path: path.stat().st_mtime)


def session_id_from_raw(path: Path) -> str:
    return path.stem


def estimate_recording_stats(raw_path: Path | None) -> list[tuple[str, str]]:
    if raw_path is None:
        return [("Latest raw", "none")]

    rows = count_csv_rows(raw_path)
    size = raw_path.stat().st_size
    session_id = session_id_from_raw(raw_path)
    metadata = load_json_file(metadata_path_for(session_id))
    duration = None
    if metadata.get("rows_written"):
        duration = None

    # Use row count and observed file size for practical storage estimates.
    bytes_per_row = size / max(rows, 1)
    fps_guess = 60.0
    mb_per_min = bytes_per_row * fps_guess * 60.0 / (1024 * 1024)

    rows_line = str(rows)
    if metadata.get("rows_written") and metadata["rows_written"] != rows:
        rows_line += f" metadata={metadata['rows_written']}"

    return [
        ("Latest raw", raw_path.name),
        ("Rows", rows_line),
        ("Raw size", format_bytes(size)),
        ("Approx raw/min", f"{mb_per_min:.1f} MB at 60 fps"),
        ("Approx raw/hour", f"{mb_per_min * 60.0:.0f} MB at 60 fps"),
    ]


def base_session_id(path: Path) -> str:
    stem = path.stem
    if stem.endswith("_processed"):
        return stem[: -len("_processed")]
    return stem


def processed_path_for(raw_path: Path) -> Path:
    return PROCESSED_DIR / f"{raw_path.stem}_processed.csv"


def report_path_for(processed_path: Path) -> Path:
    return REPORTS_DIR / f"{base_session_id(processed_path)}_report.md"


def plot_path_for(processed_path: Path) -> Path:
    return REPORTS_DIR / f"{base_session_id(processed_path)}_timeseries.png"


def metadata_path_for(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}_meta.json"


def tune_snapshot_path_for(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}_tune.json"


def require_dependency(action: Callable[[], None]) -> None:
    try:
        action()
    except ModuleNotFoundError as exc:
        print(f"\nMissing dependency: {exc.name}")
        print("Run setup_windows.bat, or run:")
        print("  pip install -r requirements.txt")


def print_header() -> None:
    print()
    print(cyan("=" * 72))
    print(bold("FH6 Tuning Sim Launcher").center(72))
    print(cyan("=" * 72))
    print_kv_table(
        [
            ("Project", str(ROOT)),
            ("Tune config", str(TUNE_CONFIG)),
        ]
    )


def print_status() -> None:
    ensure_dirs()
    raw_count = len(list(RAW_DIR.glob("*.csv")))
    processed_count = len(list(PROCESSED_DIR.glob("*.csv")))
    report_count = len(list(REPORTS_DIR.glob("*.md")))
    latest_raw = latest_file(RAW_DIR, "*.csv")
    latest_processed = latest_file(PROCESSED_DIR, "*.csv")
    tune = load_json_file(TUNE_CONFIG)

    print("\n" + bold("Current Status"))
    print_kv_table(
        [
            ("Raw CSV files", str(raw_count)),
            ("Processed CSV files", str(processed_count)),
            ("Reports", str(report_count)),
            ("Latest raw", latest_raw.name if latest_raw else "none"),
            ("Latest processed", latest_processed.name if latest_processed else "none"),
            ("Car", str(tune.get("car_name", "unknown"))),
            ("Tune", str(tune.get("tune_name", "unknown"))),
            ("Use case", str(tune.get("use_case", "unknown"))),
        ]
    )


def record_telemetry() -> None:
    from fh6_tuning_sim.receiver.udp_listener import listen

    host, port = prompt_host_port()
    session_prefix = input_default("Session name suffix", "road_test")
    notes = input_default("Notes", "baseline run")
    duration_sec = optional_float("Duration seconds")
    max_packets = optional_int("Max valid packets")

    args = argparse.Namespace(
        host=host,
        port=port,
        raw_dir=str(RAW_DIR),
        sessions_dir=str(SESSIONS_DIR),
        session_id=None,
        session_prefix=session_prefix,
        tune_config=str(TUNE_CONFIG),
        car_name=None,
        use_case=None,
        notes=notes,
        max_packets=max_packets,
        duration_sec=duration_sec,
        status_every=300,
        accept_extra_bytes=False,
    )

    print("\nIn FH6 set Data Out IP to 127.0.0.1 and port to 9999 unless changed.")
    print(f"Current listener target: {host}:{port}")
    print("Start driving after this listener says it is listening.")
    print("Stop recording with Ctrl+C.\n")
    listen(args)


def build_demo_packet(frame_index: int, total_frames: int) -> bytes:
    from fh6_tuning_sim.receiver.packet_parser import FIELD_NAMES, FIELD_SPECS, PACKET_STRUCT

    values: list[float | int] = []
    for field in FIELD_SPECS:
        values.append(0.0 if field.type_code == "F32" else 0)

    by_name = {name: index for index, name in enumerate(FIELD_NAMES)}

    def set_value(name: str, value: float | int) -> None:
        if name in by_name:
            values[by_name[name]] = value

    t = frame_index / 60.0
    steer = int(max(-90, min(90, math.sin(t * 2.2) * 85)))
    throttle = int(170 + 70 * max(0.0, math.sin(t * 1.1)))
    brake = int(120 if 1.8 < t % 6.0 < 2.2 else 0)
    speed = 28.0 + frame_index * 0.05 + 5.0 * math.sin(t * 0.8)
    yaw_rate = 0.25 * math.sin(t * 2.2)
    front_slip = 0.45 + 0.45 * abs(steer) / 90.0
    rear_slip = 0.35 + 0.30 * throttle / 255.0
    suspension = 0.45 + 0.08 * math.sin(t * 3.0)

    set_value("is_race_on", 1)
    set_value("timestamp_ms", frame_index * 16)
    set_value("engine_max_rpm", 8000.0)
    set_value("engine_idle_rpm", 900.0)
    set_value("current_engine_rpm", 2500.0 + throttle * 18.0)
    set_value("acceleration_x", 5.5 * math.sin(t * 2.2))
    set_value("acceleration_y", 0.0)
    set_value("acceleration_z", 1.2 if brake == 0 else -4.0)
    set_value("velocity_x", 0.0)
    set_value("velocity_y", 0.0)
    set_value("velocity_z", speed)
    set_value("angular_velocity_x", 0.0)
    set_value("angular_velocity_y", yaw_rate)
    set_value("angular_velocity_z", 0.0)
    set_value("yaw", t * 0.1)
    set_value("pitch", 0.0)
    set_value("roll", 0.05 * math.sin(t * 2.2))
    set_value("normalized_suspension_travel_front_left", suspension)
    set_value("normalized_suspension_travel_front_right", suspension + 0.03)
    set_value("normalized_suspension_travel_rear_left", suspension + 0.04)
    set_value("normalized_suspension_travel_rear_right", suspension + 0.02)
    set_value("tire_slip_ratio_front_left", 0.08)
    set_value("tire_slip_ratio_front_right", 0.08)
    set_value("tire_slip_ratio_rear_left", 0.10 + throttle / 900.0)
    set_value("tire_slip_ratio_rear_right", 0.10 + throttle / 900.0)
    set_value("tire_slip_angle_front_left", front_slip * 0.30)
    set_value("tire_slip_angle_front_right", front_slip * 0.30)
    set_value("tire_slip_angle_rear_left", rear_slip * 0.25)
    set_value("tire_slip_angle_rear_right", rear_slip * 0.25)
    set_value("tire_combined_slip_front_left", front_slip)
    set_value("tire_combined_slip_front_right", front_slip)
    set_value("tire_combined_slip_rear_left", rear_slip)
    set_value("tire_combined_slip_rear_right", rear_slip)
    set_value("position_x", math.sin(t * 0.4) * 20.0)
    set_value("position_y", 0.0)
    set_value("position_z", frame_index * 0.4)
    set_value("speed", speed)
    set_value("power", throttle * 1200.0)
    set_value("torque", throttle * 3.5)
    set_value("tire_temp_front_left", 82.0)
    set_value("tire_temp_front_right", 83.0)
    set_value("tire_temp_rear_left", 86.0)
    set_value("tire_temp_rear_right", 86.0)
    set_value("distance_traveled", frame_index * speed / 60.0)
    set_value("current_lap", t)
    set_value("current_race_time", t)
    set_value("lap_number", 1)
    set_value("race_position", 1)
    set_value("accel", throttle)
    set_value("brake", brake)
    set_value("clutch", 0)
    set_value("hand_brake", 0)
    set_value("gear", 3)
    set_value("steer", steer)
    set_value("normalized_driving_line", 0)
    set_value("normalized_ai_brake_difference", 0)

    return PACKET_STRUCT.pack(*values)


def send_demo_udp_packets(host: str, port: int, packet_count: int) -> None:
    time.sleep(0.35)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for index in range(packet_count):
            sock.sendto(build_demo_packet(index, packet_count), (host, port))
            time.sleep(0.004)


def run_udp_demo() -> None:
    from fh6_tuning_sim.receiver.udp_listener import listen

    host = "127.0.0.1"
    port = int(input_default("Demo UDP port", "9999"))
    packet_count = int(input_default("Demo packet count", "240"))
    session_id = input_default("Demo session id", "demo_udp")

    args = argparse.Namespace(
        host=host,
        port=port,
        raw_dir=str(RAW_DIR),
        sessions_dir=str(SESSIONS_DIR),
        session_id=session_id,
        session_prefix=None,
        tune_config=str(TUNE_CONFIG),
        car_name="demo car",
        use_case="udp_demo",
        notes="local UDP demo generated by fh6_launcher",
        max_packets=packet_count,
        duration_sec=10.0,
        status_every=60,
        accept_extra_bytes=False,
    )

    print("\nStarting local UDP demo.")
    print(f"Receiver: {host}:{port}")
    print("The launcher will send simulated FH6 packets to itself.\n")

    sender = threading.Thread(
        target=send_demo_udp_packets,
        args=(host, port, packet_count),
        daemon=True,
    )
    sender.start()
    listen(args)
    sender.join(timeout=1.0)

    print("\nUDP demo received packets. Running analysis on the demo data.")
    process_latest_raw()
    generate_latest_report()
    plot_latest_processed()
    print("\nDemo complete. Choose menu option 6 to open the reports folder.")


def process_latest_raw() -> Path | None:
    def action() -> None:
        import pandas as pd

        from fh6_tuning_sim.analysis.feature_engineering import add_features, write_processed

        raw_path = latest_file(RAW_DIR, "*.csv")
        if raw_path is None:
            print("\nNo raw CSV found. Record telemetry first.")
            return

        output = processed_path_for(raw_path)
        frame = pd.read_csv(raw_path)
        processed = add_features(frame)
        write_processed(processed, output)
        print(f"\nProcessed latest raw data:")
        print(f"  Input:  {raw_path}")
        print(f"  Output: {output}")

    result: Path | None = None

    def wrapped() -> None:
        nonlocal result
        raw_path = latest_file(RAW_DIR, "*.csv")
        if raw_path is not None:
            result = processed_path_for(raw_path)
        action()

    require_dependency(wrapped)
    return result if result and result.exists() else None


def generate_latest_report() -> Path | None:
    def action() -> None:
        import pandas as pd

        from fh6_tuning_sim.analysis.report_generator import generate_report
        from fh6_tuning_sim.config import load_json

        processed_path = latest_file(PROCESSED_DIR, "*.csv")
        if processed_path is None:
            print("\nNo processed CSV found. Processing latest raw CSV first.")
            process_latest_raw()
            processed_path = latest_file(PROCESSED_DIR, "*.csv")

        if processed_path is None:
            print("\nNo telemetry data available.")
            return

        session_id = base_session_id(processed_path)
        metadata_path = metadata_path_for(session_id)
        tune_path = tune_snapshot_path_for(session_id)
        output = report_path_for(processed_path)

        frame = pd.read_csv(processed_path)
        metadata = load_json(metadata_path, required=False)
        tune_config = load_json(tune_path, required=False)
        report = generate_report(frame, metadata=metadata, tune_config=tune_config)
        output.write_text(report, encoding="utf-8")

        print("\nGenerated report:")
        print(f"  Input:  {processed_path}")
        print(f"  Output: {output}")

    require_dependency(action)
    latest_report = latest_file(REPORTS_DIR, "*.md")
    return latest_report


def plot_latest_processed() -> Path | None:
    def action() -> None:
        import pandas as pd

        from fh6_tuning_sim.visualization.plot_timeseries import plot_timeseries

        processed_path = latest_file(PROCESSED_DIR, "*.csv")
        if processed_path is None:
            print("\nNo processed CSV found. Processing latest raw CSV first.")
            process_latest_raw()
            processed_path = latest_file(PROCESSED_DIR, "*.csv")

        if processed_path is None:
            print("\nNo telemetry data available.")
            return

        output = plot_path_for(processed_path)
        frame = pd.read_csv(processed_path)
        plot_timeseries(frame, output)
        print("\nGenerated plot:")
        print(f"  Input:  {processed_path}")
        print(f"  Output: {output}")

    require_dependency(action)
    latest_plot = latest_file(REPORTS_DIR, "*.png")
    return latest_plot


def full_latest_analysis() -> None:
    processed = process_latest_raw()
    if processed is None:
        return
    generate_latest_report()
    plot_latest_processed()


def configure_tune() -> None:
    tune = load_json_file(TUNE_CONFIG)
    tune.setdefault("tune", {})

    print("\n" + bold("Current Car / Tune Config"))
    print("Press Enter to keep the current value.")

    car_name = input_default("Car name", str(tune.get("car_name") or "Mercedes-AMG GT"))
    drivetrain = input_default("Drivetrain FWD/RWD/AWD", str(tune.get("drivetrain") or "RWD")).upper()
    if drivetrain not in {"FWD", "RWD", "AWD"}:
        print(yellow("Unknown drivetrain; keeping AWD for analysis safety."))
        drivetrain = "AWD"
    use_case = input_default("Use case", str(tune.get("use_case") or "road_grip"))
    tune_name = input_default("Tune name", str(tune.get("tune_name") or "stock_default"))
    car_class = input_default("Car class", str(tune.get("car_class") or "unknown"))
    performance_index = input_default(
        "Performance index",
        "" if tune.get("performance_index") is None else str(tune.get("performance_index")),
    )

    tune["car_name"] = car_name
    tune["drivetrain"] = drivetrain
    tune["use_case"] = use_case
    tune["tune_name"] = tune_name
    tune["car_class"] = car_class
    tune["performance_index"] = int(performance_index) if performance_index.isdigit() else None

    write_json_file(TUNE_CONFIG, tune)
    print(green(f"\nSaved: {TUNE_CONFIG}"))


def show_storage_estimate() -> None:
    latest_raw = latest_real_raw_file()
    print("\n" + bold("Data Size Estimate"))
    print_kv_table(estimate_recording_stats(latest_raw))
    print()
    print("Practical guidance:")
    print("- A clean one-lap test is usually fine as CSV.")
    print("- For long sessions, analyze and keep selected runs instead of recording everything.")
    print("- Parquet export is already supported by feature_engineering if you use a .parquet output path.")
    print("- Road slope/banking is not directly available; position and acceleration still allow useful behavior analysis.")


def open_file(path: Path | None, label: str) -> None:
    if path is None or not path.exists():
        print(f"\nNo {label} found.")
        return
    print(f"\nOpening {label}: {path}")
    os.startfile(path)  # type: ignore[attr-defined]


def open_latest_report() -> None:
    open_file(latest_file(REPORTS_DIR, "*.md"), "report")


def open_latest_plot() -> None:
    open_file(latest_file(REPORTS_DIR, "*.png"), "plot")


def open_path(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(path)  # type: ignore[attr-defined]


def open_reports_folder() -> None:
    open_path(REPORTS_DIR)


def open_data_folder() -> None:
    open_path(ROOT / "data")


def show_setup_help() -> None:
    print("\nBeginner Setup")
    print("-" * 14)
    print("1. Install Python 3.10+ and make sure 'python --version' works.")
    print("2. Run setup_windows.bat once to create .venv and install dependencies.")
    print("3. In FH6 set Data Out to:")
    print("   IP:   127.0.0.1")
    print("   Port: 9999")
    print("4. Run start_fh6_tool.bat and choose menu option 1 for UDP demo.")
    print("5. Choose menu option 2 to set car/tune metadata.")
    print("6. Choose menu option 3 to record real FH6 telemetry.")
    print("\nManual setup commands:")
    print("  python -m venv .venv")
    print("  .\\.venv\\Scripts\\Activate.ps1")
    print("  pip install -r requirements.txt")


def run_menu() -> int:
    ensure_dirs()
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Run UDP demo self-test", run_udp_demo),
        "2": ("Configure current car / tune", configure_tune),
        "3": ("Record real FH6 telemetry", record_telemetry),
        "4": ("Run full latest analysis", full_latest_analysis),
        "5": ("Process latest raw CSV only", lambda: process_latest_raw()),
        "6": ("Generate report only", lambda: generate_latest_report()),
        "7": ("Generate plot only", lambda: plot_latest_processed()),
        "8": ("Open latest report", open_latest_report),
        "9": ("Open latest plot", open_latest_plot),
        "10": ("Open reports folder", open_reports_folder),
        "11": ("Open data folder", open_data_folder),
        "12": ("Show data size estimate", show_storage_estimate),
        "13": ("Show setup help", show_setup_help),
        "14": ("Show current status", print_status),
    }

    while True:
        print_header()
        print_status()
        print("\n" + bold("Menu"))
        for key, (label, _) in actions.items():
            print(f"  {cyan(key.rjust(2))}  {label}")
        print(f"  {cyan('0'.rjust(2))}  Exit")

        choice = input("\nChoose an option: ").strip()
        if choice == "0":
            return 0

        action = actions.get(choice)
        if action is None:
            print("\nInvalid option.")
            pause()
            continue

        try:
            action[1]()
        except KeyboardInterrupt:
            print("\nInterrupted.")
        except Exception as exc:
            print(f"\nError: {exc}")
        pause()


if __name__ == "__main__":
    try:
        raise SystemExit(run_menu())
    except KeyboardInterrupt:
        print("\nExiting.")
        raise SystemExit(130)
