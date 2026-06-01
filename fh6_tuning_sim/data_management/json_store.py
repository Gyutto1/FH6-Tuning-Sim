from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


def ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def safe_load_json(path: str | Path, default: Any) -> Any:
    json_path = Path(path)
    fallback = deepcopy(default)
    if not json_path.exists():
        return fallback
    try:
        raw = json_path.read_text(encoding="utf-8-sig")
        if not raw.strip():
            return fallback
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return fallback
    if default is not None and not isinstance(data, type(default)):
        return fallback
    return data


def safe_save_json(path: str | Path, data: Any) -> None:
    json_path = Path(path)
    ensure_parent_dir(json_path)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
