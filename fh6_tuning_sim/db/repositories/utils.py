from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fh6_tuning_sim.data_management.session_naming import sanitize_filename


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_key(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return sanitize_filename(text if text else default)


def require_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def active_flag(is_active: bool | int | None = True) -> int:
    return 0 if is_active is False or is_active == 0 else 1
