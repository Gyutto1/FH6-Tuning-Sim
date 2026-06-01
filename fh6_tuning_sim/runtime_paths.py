from __future__ import annotations

from pathlib import Path
import shutil
import sys


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    if is_frozen_app():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def runtime_mode_label() -> str:
    return "EXE" if is_frozen_app() else "开发"


def data_path(*parts: str) -> Path:
    return app_root().joinpath("data", *parts)


def config_path(*parts: str) -> Path:
    return app_root().joinpath("configs", *parts)


def reports_path(*parts: str) -> Path:
    return app_root().joinpath("reports", *parts)


def ensure_runtime_dirs() -> None:
    for path in [
        data_path(),
        data_path("raw"),
        data_path("processed"),
        data_path("sessions"),
        data_path("index"),
        data_path("platform"),
        reports_path(),
        config_path(),
    ]:
        path.mkdir(parents=True, exist_ok=True)


def ensure_database_from_seed(db_path: str | Path) -> bool:
    target = Path(db_path)
    if target.exists():
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    for candidate in [
        data_path("fh6_tuning_sim.default.db"),
        data_path("demo", "fh6_demo.db"),
    ]:
        if candidate.exists():
            shutil.copy2(candidate, target)
            return True
    return False
