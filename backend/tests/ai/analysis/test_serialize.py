import enum
import math
from dataclasses import dataclass
from pathlib import Path

from ai.analysis.serialize import jsonable, remap_times


class Color(enum.Enum):
    RED = "red"


@dataclass
class Inner:
    t_start_s: float
    frames: tuple


@dataclass
class Outer:
    inner: Inner
    path: Path
    color: Color
    values: tuple
    missing: float


class Scalar:
    def item(self):
        return 3


def test_jsonable_flattens_and_drops():
    out = jsonable(
        Outer(Inner(1.5, (1, 2)), Path("/a"), Color.RED, (Scalar(), {"k": (1,)}), math.nan),
        drop={"frames"},
    )
    assert out == {
        "inner": {"t_start_s": 1.5},
        "path": "/a",
        "color": "red",
        "values": [3, {"k": [1]}],
        "missing": None,
    }


def test_remap_moves_seller_times_onto_the_recording():
    ranges = [(0, 1000), (3000, 5000)]
    data = {"windows": [{"t_start_ms": 1500, "end_ms": 0, "t_start_s": 1.5, "label": "x"}]}
    assert remap_times(data, ranges) == {
        "windows": [{"t_start_ms": 3500, "end_ms": 0, "t_start_s": 3.5, "label": "x"}]
    }
    assert remap_times(data, []) is data
