from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

AnalysisMode = Literal["audio", "audio_video"]
AnalysisState = Literal["not_started", "queued", "running", "complete", "failed"]


class AnalyzeRequest(BaseModel):
    # audio skips body language and the annotated video, and is faster.
    mode: AnalysisMode = "audio_video"


class AnalysisStatusResponse(BaseModel):
    status: AnalysisState
    # transcribing, analyzing or finishing while running.
    stage: str | None
    # A plain message when the analysis failed.
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class Dimension(BaseModel):
    name: str
    label: str
    score: int | None
    summary: str
    skipped: str | None = None


class Moment(BaseModel):
    t_start_ms: int
    t_end_ms: int
    quote: str


class FindingOut(BaseModel):
    pipeline: str
    category: str
    severity: Literal["info", "low", "medium", "high"]
    summary: str
    note: Moment | None = None
    details: dict[str, Any] = {}


class CorrectedAnswer(BaseModel):
    question: str
    original: str
    stronger: str
    change: str
    citation: str
    verified: bool
    unsupported_numbers: list[str]
    t_start_ms: int | None
    # Presigned; None when there is no voice clone or speaking failed.
    audio_url: str | None


class AnalysisResult(BaseModel):
    overall_score: int | None
    dimensions: list[Dimension]
    summary: str
    findings: list[FindingOut]
    strengths: list[str]
    prep_list: list[str]
    corrected_answers: list[CorrectedAnswer]
    questions: int
    handled: int
    metrics: dict[str, Any]
    annotated_video_url: str | None
    notes: list[str]


class AnalysisResponse(AnalysisStatusResponse):
    # Set once the status is complete.
    result: AnalysisResult | None
