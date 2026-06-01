from __future__ import annotations

from typing import Any

from fh6_tuning_sim.data_management.dictionaries import read_dictionary_items


def list_routes(*, include_inactive: bool = True) -> list[dict[str, Any]]:
    return [
        item
        for item in read_dictionary_items("route", include_inactive=include_inactive)
        if item.get("key") != "unknown"
    ]


def get_route(route_key: str, *, include_inactive: bool = True) -> dict[str, Any] | None:
    for route in list_routes(include_inactive=include_inactive):
        if str(route.get("key")) == str(route_key):
            return route
    return None
