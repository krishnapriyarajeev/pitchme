"""Pipeline reports as plain JSON, for the session's analysis data."""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ai.diarize.filter_speaker import original_time

_MS_KEYS = frozenset({"start_ms", "end_ms", "t_start_ms", "t_end_ms"})
_S_KEYS = frozenset({"start_s", "end_s", "t_start_s", "t_end_s"})


def jsonable(value: Any, drop: frozenset[str] | set[str] = frozenset()) -> Any:
    """Dataclasses, tuples, enums and numpy numbers as JSON types. Fields
    named in `drop` are left out at any depth (per-frame data, findings
    stored elsewhere)."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            f.name: jsonable(getattr(value, f.name), drop)
            for f in dataclasses.fields(value)
            if f.name not in drop
        }
    if isinstance(value, Mapping):
        return {str(k): jsonable(v, drop) for k, v in value.items() if k not in drop}
    if isinstance(value, list | tuple | set | frozenset):
        return [jsonable(v, drop) for v in value]
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item") and callable(value.item):  # numpy scalar
        return value.item()
    if isinstance(value, float) and value != value:  # NaN is not JSON
        return None
    return value


def remap_times(data: Any, ranges: list[tuple[int, int]]) -> Any:
    """Times measured on the seller-only audio, moved onto the recording."""
    if not ranges:
        return data
    if isinstance(data, dict):
        out = {}
        for key, value in data.items():
            if key in _MS_KEYS and isinstance(value, int | float):
                out[key] = original_time(round(value), ranges)
            elif key in _S_KEYS and isinstance(value, int | float):
                out[key] = original_time(round(value * 1000), ranges) / 1000
            else:
                out[key] = remap_times(value, ranges)
        return out
    if isinstance(data, list):
        return [remap_times(v, ranges) for v in data]
    return data
