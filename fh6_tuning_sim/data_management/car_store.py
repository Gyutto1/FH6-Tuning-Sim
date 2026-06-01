from __future__ import annotations

from pathlib import Path
from typing import Any

from fh6_tuning_sim.data_management.platform_store import (
    PLATFORM_INDEX_PATH,
    find_car,
    read_platform,
    utc_now,
    write_platform,
)


def list_cars(*, path: str | Path = PLATFORM_INDEX_PATH, include_archived: bool = True) -> list[dict[str, Any]]:
    cars = read_platform(path).get("cars", [])
    if not isinstance(cars, list):
        return []
    if include_archived:
        return cars
    return [car for car in cars if car.get("status") != "archived"]


def get_car(car_id: str, *, path: str | Path = PLATFORM_INDEX_PATH) -> dict[str, Any] | None:
    return find_car(read_platform(path), car_id)


def update_car(car_id: str, data: dict[str, Any], *, path: str | Path = PLATFORM_INDEX_PATH) -> dict[str, Any] | None:
    platform = read_platform(path)
    car = find_car(platform, car_id)
    if car is None:
        return None
    car.update(data)
    car["updated_at_utc"] = utc_now()
    write_platform(platform, path)
    return car


def archive_car(car_id: str, *, path: str | Path = PLATFORM_INDEX_PATH) -> dict[str, Any] | None:
    return update_car(car_id, {"status": "archived"}, path=path)
