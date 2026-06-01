from __future__ import annotations

import argparse
from datetime import datetime, timezone
import socket
import time
from pathlib import Path
from typing import Any

from fh6_tuning_sim.config import load_json, tune_summary
from fh6_tuning_sim.receiver.packet_parser import (
    OFFICIAL_DOC_URL,
    PACKET_SIZE,
    PacketLengthError,
    parse_packet,
)
from fh6_tuning_sim.receiver.raw_logger import TelemetryCsvLogger, make_session_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Receive FH6 Data Out UDP packets.")
    parser.add_argument("--host", default="127.0.0.1", help="IP address to bind.")
    parser.add_argument("--port", type=int, default=9999, help="UDP port to bind.")
    parser.add_argument("--raw-dir", default="data/raw", help="CSV output directory.")
    parser.add_argument(
        "--sessions-dir",
        default="data/sessions",
        help="Session metadata output directory.",
    )
    parser.add_argument("--session-id", help="Override generated session id.")
    parser.add_argument(
        "--session-prefix",
        default=None,
        help="Optional suffix added to generated session id.",
    )
    parser.add_argument(
        "--tune-config",
        default="configs/tune_config.json",
        help="Tune config JSON to snapshot with the run.",
    )
    parser.add_argument("--car-name", default=None, help="Override metadata car name.")
    parser.add_argument("--use-case", default=None, help="Override metadata use case.")
    parser.add_argument("--notes", default="", help="Free-form run notes.")
    parser.add_argument(
        "--max-packets",
        type=int,
        default=None,
        help="Stop after receiving this many valid packets.",
    )
    parser.add_argument(
        "--duration-sec",
        type=float,
        default=None,
        help="Stop after this many seconds.",
    )
    parser.add_argument(
        "--status-every",
        type=int,
        default=300,
        help="Print progress every N valid packets.",
    )
    parser.add_argument(
        "--accept-extra-bytes",
        action="store_true",
        help="Parse the first 324 bytes even if a packet is longer.",
    )
    return parser


def build_metadata(args: argparse.Namespace, tune_config: dict[str, Any]) -> dict[str, Any]:
    summary = tune_summary(tune_config) if tune_config else {}
    if args.car_name:
        summary["car_name"] = args.car_name
    if args.use_case:
        summary["use_case"] = args.use_case

    return {
        "session_id": args.session_id,
        "game": "Forza Horizon 6",
        "data_out_host": args.host,
        "data_out_port": args.port,
        "packet_size_bytes": PACKET_SIZE,
        "official_doc_url": OFFICIAL_DOC_URL,
        "notes": args.notes,
        **summary,
    }


def listen(args: argparse.Namespace) -> int:
    tune_path = Path(args.tune_config) if args.tune_config else None
    tune_config = load_json(tune_path, required=False) if tune_path else {}
    session_id = args.session_id or make_session_id(args.session_prefix)
    args.session_id = session_id
    metadata = build_metadata(args, tune_config)

    valid_packets = 0
    dropped_packets = 0
    start = time.monotonic()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.host, args.port))
        sock.settimeout(1.0)
        print(
            f"Listening for FH6 Data Out on {args.host}:{args.port} "
            f"(session {session_id})"
        )
        print("Stop with Ctrl+C.")

        with TelemetryCsvLogger(
            raw_dir=args.raw_dir,
            sessions_dir=args.sessions_dir,
            session_id=session_id,
            metadata=metadata,
            tune_config_path=tune_path,
        ) as logger:
            while True:
                if args.duration_sec and time.monotonic() - start >= args.duration_sec:
                    break
                if args.max_packets and valid_packets >= args.max_packets:
                    break

                try:
                    packet, address = sock.recvfrom(2048)
                except socket.timeout:
                    continue
                except KeyboardInterrupt:
                    print("\nStopping listener...")
                    break

                try:
                    telemetry = parse_packet(
                        packet,
                        strict_size=not args.accept_extra_bytes,
                    )
                except PacketLengthError as exc:
                    dropped_packets += 1
                    if dropped_packets <= 5:
                        print(f"Dropped packet from {address}: {exc}")
                    continue

                logger.write_row(
                    telemetry,
                    source_ip=address[0],
                    source_port=address[1],
                )
                valid_packets += 1

                if args.status_every and valid_packets % args.status_every == 0:
                    elapsed = max(time.monotonic() - start, 0.001)
                    rate = valid_packets / elapsed
                    print(
                        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} "
                        f"valid={valid_packets} dropped={dropped_packets} "
                        f"rate={rate:.1f}/s -> {logger.csv_path}"
                    )

    print(f"Finished. valid={valid_packets}, dropped={dropped_packets}")
    print(f"Raw CSV: {Path(args.raw_dir) / f'{session_id}.csv'}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return listen(args)


if __name__ == "__main__":
    raise SystemExit(main())

