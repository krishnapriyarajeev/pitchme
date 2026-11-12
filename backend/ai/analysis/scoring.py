"""Dimension scores and the overall score, all out of 100.

Content is the judge's own score. Speech, voice and body language start at
100 and lose points for each finding, by severity, so every score comes
with the findings that explain it. Each finding costs points once.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from ai.core.types import Finding, Severity

PENALTY: Mapping[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 5,
    Severity.MEDIUM: 12,
    Severity.HIGH: 20,
}

# Content counts most, then how the seller looked and sounded.
WEIGHTS: Mapping[str, float] = {"content": 0.5, "speech": 0.15, "voice": 0.15, "vision": 0.2}

LABELS: Mapping[str, str] = {
    "content": "Content",
    "speech": "Speech",
    "voice": "Voice",
    "vision": "Body language",
}

CLEAN: Mapping[str, str] = {
    "speech": "Clear and easy to follow, at a comfortable pace.",
    "voice": "Steady energy and natural intonation.",
    "vision": "Upright, engaged and looking at the camera.",
}


@dataclass(frozen=True)
class DimensionScore:
    name: str
    label: str
    # None when the dimension could not be scored; `skipped` says why.
    score: int | None
    summary: str
    skipped: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def from_findings(name: str, findings: Sequence[Finding]) -> DimensionScore:
    lost = sum(PENALTY[f.severity] for f in findings)
    worst = sorted(findings, key=lambda f: -f.severity.rank)
    summary = worst[0].summary if worst and worst[0].severity is not Severity.INFO else CLEAN[name]
    return DimensionScore(name, LABELS[name], max(0, 100 - lost), summary)


def content_score(score: int | None, summary: str) -> DimensionScore:
    if score is None:
        return skipped("content", summary)
    return DimensionScore("content", LABELS["content"], max(0, min(100, score)), summary)


def skipped(name: str, reason: str) -> DimensionScore:
    return DimensionScore(name, LABELS[name], None, reason, skipped=reason)


def overall(dimensions: Sequence[DimensionScore]) -> int | None:
    """Weighted mean of the scored dimensions. A dimension that was not
    scored (no video, say) leaves the others' weights to share its part."""
    scored = [(WEIGHTS[d.name], d.score) for d in dimensions if d.score is not None]
    total = sum(w for w, _ in scored)
    if not total:
        return None
    return round(sum(w * s for w, s in scored) / total)
