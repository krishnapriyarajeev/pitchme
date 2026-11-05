"""Speaker diarization: which voice was talking when.

Diarization does not know who anyone is. Labels such as "SPEAKER_00" are
anonymous and only stable within one call; identify.py matches a label to
a known voice.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


class DiarizeError(RuntimeError):
    """The audio could not be diarized, or the model could not be loaded."""


@dataclass(frozen=True)
class DiarizedSegment:
    speaker: str
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class DiarizeClient(ABC):
    @abstractmethod
    def diarize(
        self, audio_path: str | Path, min_speakers: int = 1, max_speakers: int = 2
    ) -> tuple[DiarizedSegment, ...]:
        """Speaker segments in start order. Segments may overlap where two
        people talk at once.

        A rehearsal is the user alone or with one buyer, so the speaker
        count is bounded to 1-2 by default. Without a bound, clustering
        can split one voice into two labels on short audio."""


def speaking_time(segments: tuple[DiarizedSegment, ...]) -> dict[str, int]:
    """Total milliseconds each speaker talked, longest first."""
    totals: dict[str, int] = {}
    for segment in segments:
        totals[segment.speaker] = totals.get(segment.speaker, 0) + segment.duration_ms
    return dict(sorted(totals.items(), key=lambda kv: -kv[1]))
