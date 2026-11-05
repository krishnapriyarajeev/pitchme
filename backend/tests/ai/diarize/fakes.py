"""A stand-in for a pyannote pipeline and its annotation."""

from __future__ import annotations

from types import SimpleNamespace


class FakeAnnotation:
    def __init__(self, turns: list[tuple[float, float, str]]) -> None:
        self.turns = turns

    def itertracks(self, yield_label: bool = False):
        assert yield_label
        for i, (start, end, speaker) in enumerate(self.turns):
            yield SimpleNamespace(start=start, end=end), f"T{i}", speaker


class FakePipeline:
    def __init__(self, turns, *, wrapped: bool = False, error: Exception | None = None):
        self.annotation = FakeAnnotation(turns)
        self.wrapped = wrapped
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, path: str, **kwargs):
        self.calls.append((path, kwargs))
        if self.error:
            raise self.error
        if self.wrapped:
            return SimpleNamespace(speaker_diarization=self.annotation)
        return self.annotation
