"""Which diarized speaker is the user?

Diarization gives anonymous labels. The user recorded a voice sample at
onboarding, so each label's voice is compared with that sample: both become
speaker embeddings (fixed-length voice fingerprints) and the closest by
cosine similarity wins.

Short clips give unreliable embeddings, so clips under MIN_CLIP_MS are
skipped and the rest are averaged weighted by length.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from .base import DiarizedSegment, DiarizeError

MIN_CLIP_MS = 500
# Below this similarity the best match is reported as unsure.
MIN_CONFIDENT_SIMILARITY = 0.3


class Embedder(Protocol):
    def embed_file(self, path: str | Path) -> np.ndarray: ...

    def embed_span(self, path: str | Path, start_ms: int, end_ms: int) -> np.ndarray: ...


@dataclass(frozen=True)
class Identification:
    speaker: str
    # Cosine similarity of each speaker to the reference voice, from -1 to 1.
    scores: dict[str, float]

    @property
    def confident(self) -> bool:
        return self.scores[self.speaker] >= MIN_CONFIDENT_SIMILARITY

    @property
    def margin(self) -> float:
        """How far the winner is ahead of the runner-up."""
        ranked = sorted(self.scores.values(), reverse=True)
        return round(ranked[0] - ranked[1], 3) if len(ranked) > 1 else ranked[0]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.ravel(a), np.ravel(b)
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b)) / norm if norm else 0.0


def _speaker_embedding(
    embedder: Embedder, audio: str | Path, segments: list[DiarizedSegment]
) -> np.ndarray | None:
    clips = [s for s in segments if s.duration_ms >= MIN_CLIP_MS]
    if not clips:
        return None
    vectors = [np.ravel(embedder.embed_span(audio, s.start_ms, s.end_ms)) for s in clips]
    return np.average(vectors, axis=0, weights=[s.duration_ms for s in clips])


def identify_speaker(
    embedder: Embedder,
    mixed_audio: str | Path,
    segments: tuple[DiarizedSegment, ...],
    reference_audio: str | Path,
) -> Identification:
    """The speaker in `segments` whose voice best matches `reference_audio`."""
    by_speaker: dict[str, list[DiarizedSegment]] = {}
    for segment in segments:
        by_speaker.setdefault(segment.speaker, []).append(segment)
    if not by_speaker:
        raise DiarizeError("No speaker segments to compare with the voice sample")

    reference = embedder.embed_file(reference_audio)
    scores = {}
    for speaker, spans in sorted(by_speaker.items()):
        vector = _speaker_embedding(embedder, mixed_audio, spans)
        if vector is not None:
            scores[speaker] = round(cosine(reference, vector), 4)
    if not scores:
        raise DiarizeError(
            f"Every speaker segment is shorter than {MIN_CLIP_MS} ms, too short to compare"
        )
    return Identification(max(scores, key=scores.get), scores)
