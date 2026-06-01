from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import unicodedata


SAFE_EMPTY = "unknown"


def sanitize_filename(value: object, *, max_length: int = 48) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = SAFE_EMPTY
    return text[:max_length].strip("_") or SAFE_EMPTY


def class_pi(car_class: object, performance_index: object) -> str:
    car_class_text = sanitize_filename(car_class)
    pi_text = sanitize_filename(performance_index)
    if car_class_text == SAFE_EMPTY and pi_text == SAFE_EMPTY:
        return SAFE_EMPTY
    if pi_text == SAFE_EMPTY:
        return car_class_text
    if car_class_text == SAFE_EMPTY:
        return pi_text
    return f"{car_class_text}_{pi_text}"


def build_session_id(
    *,
    car_name: object,
    car_class: object = None,
    performance_index: object = None,
    use_case: object = None,
    route_name: object = None,
    test_scenario: object = None,
    tune_name: object = None,
    run_number: int | None = None,
    timestamp: datetime | None = None,
) -> str:
    timestamp = timestamp or datetime.now()
    run_text = f"run{run_number:02d}" if run_number is not None else "run01"
    parts = [
        timestamp.strftime("%Y%m%d_%H%M%S"),
        sanitize_filename(car_name),
        class_pi(car_class, performance_index),
        sanitize_filename(use_case),
        sanitize_filename(route_name),
        sanitize_filename(test_scenario),
        sanitize_filename(tune_name),
        run_text,
    ]
    return "__".join(parts)


def next_run_number(raw_dir: str | Path, session_prefix: str) -> int:
    raw_path = Path(raw_dir)
    existing = sorted(raw_path.glob(f"{session_prefix}__run*.csv"))
    if not existing:
        return 1

    highest = 0
    for path in existing:
        match = re.search(r"__run(\d+)$", path.stem)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1

