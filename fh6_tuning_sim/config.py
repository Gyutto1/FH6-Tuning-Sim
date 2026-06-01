from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path, *, required: bool = True) -> dict[str, Any]:
    json_path = Path(path)
    if not json_path.exists():
        if required:
            raise FileNotFoundError(f"Config file not found: {json_path}")
        return {}

    # Be tolerant of UTF-8 files with or without BOM.
    with json_path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {json_path}")
    return data


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def tune_summary(tune_config: dict[str, Any]) -> dict[str, Any]:
    return {
        "car_name": tune_config.get("car_name", "unknown"),
        "car_ordinal": tune_config.get("car_ordinal"),
        "car_class": tune_config.get("car_class"),
        "performance_index": tune_config.get("performance_index"),
        "drivetrain": tune_config.get("drivetrain"),
        "use_case": tune_config.get("use_case", "unknown"),
        "tune_name": tune_config.get("tune_name", "unknown"),
    }
