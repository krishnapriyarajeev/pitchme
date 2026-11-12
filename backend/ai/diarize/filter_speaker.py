"""Cut a two-person recording down to one speaker, for speech and voice.

Both pipelines score one person. Deleting the other speaker's words
would leave holes in the timeline: fluency would read each of the buyer's
turns as a long hesitation by the user, and the rate windows would count
them as silence. So every removed stretch is closed up: later words and
samples move back by its exact length, and the kept speaker's material
becomes continuous, as if the other person never spoke. The pipelines then
need no change at all.

A stretch is removed only where another speaker talks and the kept speaker
does not. Where both talk at once, the overlap is kept. Silence that no
segment covers is kept too: there is no evidence it belongs to anyone else.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from ai.core.transcript import Segment, Transcript, Word

from .align import TaggedTranscript
from .base import DiarizedSegment


def _merge(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        elif end > start:
            merged.append((start, end))
    return merged


def _subtract(ranges: list[tuple[int, int]], holes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out = []
    for start, end in ranges:
        cursor = start
        for h_start, h_end in holes:
            if h_end <= cursor or h_start >= end:
                continue
            if h_start > cursor:
                out.append((cursor, h_start))
            cursor = max(cursor, h_end)
        if cursor < end:
            out.append((cursor, end))
    return out


def kept_ranges(
    segments: tuple[DiarizedSegment, ...], speaker: str, total_ms: int
) -> list[tuple[int, int]]:
    """The parts of [0, total_ms) to keep for `speaker`, in order."""
    others = _merge([(s.start_ms, s.end_ms) for s in segments if s.speaker != speaker])
    own = _merge([(s.start_ms, s.end_ms) for s in segments if s.speaker == speaker])
    cuts = _subtract(others, own)
    return _subtract([(0, total_ms)], cuts)


def _shift(t_ms: int, ranges: list[tuple[int, int]]) -> int | None:
    """Where `t_ms` lands once the cuts are closed up; None inside a cut."""
    offset = 0
    for start, end in ranges:
        if start <= t_ms <= end:
            return offset + t_ms - start
        offset += end - start
    return None


def original_time(t_ms: int, ranges: list[tuple[int, int]]) -> int:
    """The reverse of closing up: where a time in the cut audio was in the
    original. Findings from the cut audio use it to point at the recording."""
    offset = 0
    for start, end in ranges:
        if t_ms <= offset + end - start:
            return start + t_ms - offset
        offset += end - start
    return ranges[-1][1] if ranges else t_ms


def filter_transcript(
    tagged: TaggedTranscript, speaker: str, segments: tuple[DiarizedSegment, ...]
) -> Transcript:
    """Only `speaker`'s words (and unassigned ones), with the timeline
    closed up. `segments` must be the ones `tagged` was built from."""
    original = tagged.transcript
    ranges = kept_ranges(segments, speaker, original.duration_ms)
    keep = {w.index for w in tagged.words if w.speaker in (None, speaker)}

    out_segments = []
    position = 0
    for segment in original.segments:
        words = []
        for word in segment.words:
            if position in keep:
                start, end = _shift(word.start_ms, ranges), _shift(word.end_ms, ranges)
                if start is not None and end is not None:
                    words.append(Word(word.text, start, end, word.logprob))
            position += 1
        if words:
            out_segments.append(
                Segment(
                    text=" ".join(w.text for w in words),
                    start_ms=words[0].start_ms,
                    end_ms=words[-1].end_ms,
                    words=tuple(words),
                    confidence=segment.confidence,
                )
            )
    return Transcript(segments=tuple(out_segments), language=original.language)


def filter_audio(signal: Any, segments: tuple[DiarizedSegment, ...], speaker: str) -> Any:
    """Only `speaker`'s audio, joined end to end. `signal` is an
    ai.voice AudioSignal (anything with `samples` and `sample_rate`)."""
    import numpy as np

    rate = signal.sample_rate
    total_ms = round(len(signal.samples) / rate * 1000)
    chunks = [
        signal.samples[round(start * rate / 1000) : round(end * rate / 1000)]
        for start, end in kept_ranges(segments, speaker, total_ms)
    ]
    samples = np.concatenate(chunks) if chunks else signal.samples[:0]
    return dataclasses.replace(signal, samples=samples)
