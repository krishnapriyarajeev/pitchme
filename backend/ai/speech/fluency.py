"""Fluency: speaking rate, pauses and filler words.

Rate and pauses are arithmetic over word timings. Fillers take one LLM call
(see prompts/fillers.py). The model's counts are checked against the
transcript text, so a filler it invents or over-counts cannot reach the
report.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass
from itertools import pairwise

from ai.core.llm import LLMClient, LLMError
from ai.core.transcript import Transcript, Word
from ai.providers import get_llm_client

from .prompts.fillers import RESPONSE_SCHEMA, SYSTEM_PROMPT, FillersResponse, build_prompt

# A gap shorter than this is normal speech rhythm, not a pause.
PAUSE_THRESHOLD_MS = 400

# A pause after one of these is a deliberate beat. A pause in the middle of
# a clause is a hesitation.
CLAUSE_END_PUNCTUATION = (".", "?", "!", ",", ";", ":")

# Rate is measured over rolling windows, so a rushed minute inside a calm
# talk still shows. Windows overlap by two thirds to catch a spike that
# falls across a boundary.
WPM_WINDOW_MS = 15_000
WPM_STEP_MS = 5_000
# A tail window shorter than this has too few words to give a fair rate.
MIN_WINDOW_MS = 5_000


@dataclass(frozen=True)
class Pause:
    start_ms: int
    end_ms: int
    is_hesitation: bool

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass(frozen=True)
class WpmWindow:
    t_start_ms: int
    t_end_ms: int
    wpm: float


@dataclass(frozen=True)
class FillerCount:
    word: str
    count: int


@dataclass(frozen=True)
class FluencyReport:
    wpm_mean: float
    wpm_p95: float
    wpm_windows: tuple[WpmWindow, ...]
    pauses: tuple[Pause, ...]
    filler_total: int
    filler_per_min: float
    filler_counts: tuple[FillerCount, ...]
    # Written by the model in the same call that counts the fillers.
    filler_summary: str

    @property
    def hesitation_pauses(self) -> tuple[Pause, ...]:
        return tuple(p for p in self.pauses if p.is_hesitation)

    @property
    def rhetorical_pauses(self) -> tuple[Pause, ...]:
        return tuple(p for p in self.pauses if not p.is_hesitation)


def find_pauses(words: tuple[Word, ...]) -> tuple[Pause, ...]:
    pauses = []
    for prev, nxt in pairwise(words):
        if nxt.start_ms - prev.end_ms < PAUSE_THRESHOLD_MS:
            continue
        is_hesitation = not prev.text.rstrip().endswith(CLAUSE_END_PUNCTUATION)
        pauses.append(Pause(prev.end_ms, nxt.start_ms, is_hesitation))
    return tuple(pauses)


def rolling_wpm(words: tuple[Word, ...], duration_ms: int) -> tuple[WpmWindow, ...]:
    if not words or duration_ms <= 0:
        return ()
    starts = [w.start_ms for w in words]
    windows = []
    for t in range(0, duration_ms, WPM_STEP_MS):
        t_end = min(t + WPM_WINDOW_MS, duration_ms)
        span = t_end - t
        if windows and span < MIN_WINDOW_MS:
            break
        count = bisect_left(starts, t_end) - bisect_left(starts, t)
        windows.append(WpmWindow(t, t_end, round(count / (span / 60_000), 1)))
        if t_end == duration_ms:
            break
    return tuple(windows)


def _occurrences(phrase: str, text: str) -> int:
    """How often `phrase` appears in `text` as whole words, ignoring case
    and punctuation between its words."""
    tokens = re.findall(r"[\w']+", phrase.lower())
    if not tokens:
        return 0
    pattern = r"(?<![\w'])" + r"\W+".join(map(re.escape, tokens)) + r"(?![\w'])"
    return len(re.findall(pattern, text.lower()))


def count_fillers(transcript: Transcript, llm: LLMClient) -> tuple[tuple[FillerCount, ...], str]:
    """Fillers the model found, most used first, with its one-line summary.

    Raises LLMError when the reply does not match `FillersResponse`, so a
    bad reply is never read as "no fillers".
    """
    text = transcript.text
    if not text.strip():
        return (), "No speech to check for fillers."

    raw = llm.complete_json(build_prompt(text), schema=RESPONSE_SCHEMA, system=SYSTEM_PROMPT)
    try:
        reply = FillersResponse.model_validate(raw)
    except ValueError as exc:
        raise LLMError(f"Filler reply did not match the expected shape: {exc}") from exc

    counts: dict[str, int] = {}
    for item in reply.fillers:
        word = item.word.strip().lower()
        # The model cannot count a word more often than it was said.
        count = min(item.count, _occurrences(word, text))
        if count > 0:
            counts[word] = max(counts.get(word, 0), count)
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return tuple(FillerCount(w, c) for w, c in ordered), reply.summary.strip()


def score_fluency(transcript: Transcript, llm: LLMClient | None = None) -> FluencyReport:
    words = transcript.words
    duration_ms = transcript.duration_ms

    windows = rolling_wpm(words, duration_ms)
    rates = sorted(w.wpm for w in windows)
    wpm_mean = round(sum(rates) / len(rates), 1) if rates else 0.0
    wpm_p95 = rates[min(len(rates) - 1, int(len(rates) * 0.95))] if rates else 0.0

    fillers, summary = count_fillers(transcript, llm or get_llm_client())
    total = sum(f.count for f in fillers)
    minutes = duration_ms / 60_000
    per_min = round(total / minutes, 1) if minutes > 0 else 0.0

    return FluencyReport(
        wpm_mean=wpm_mean,
        wpm_p95=wpm_p95,
        wpm_windows=windows,
        pauses=find_pauses(words),
        filler_total=total,
        filler_per_min=per_min,
        filler_counts=fillers,
        filler_summary=summary,
    )
