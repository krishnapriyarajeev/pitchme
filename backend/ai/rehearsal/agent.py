"""The AI buyer on a live LiveKit call, and the run of one call.

Needs the rehearsal extra. `run_call` takes the session factory and the
results client as arguments, so tests drive a whole call with fakes.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from livekit.agents import NOT_GIVEN, Agent, AgentSession, room_io

from ai.config import AISettings

from .deal import CallSetup, Deal
from .prompts.buyer import build_system_prompt, opening_instruction
from .report import CallReport, EndedBy, ResultsClient
from .transcript import Transcript

log = logging.getLogger(__name__)

# How long the buyer waits for the seller to join before giving up.
JOIN_TIMEOUT_S = 120
TIME_UP_LINE = "I'm afraid I have to jump into another meeting. Let's pick this up another time."
GOODBYE_TIMEOUT_S = 15


class RehearsalConfigError(RuntimeError):
    """A key the live call needs is missing."""


class BuyerAgent(Agent):
    def __init__(self, deal: Deal) -> None:
        super().__init__(instructions=build_system_prompt(deal))
        self.deal = deal


def build_session(settings: AISettings, vad: Any) -> AgentSession:
    """Deepgram hears the seller and speaks for the buyer; Groq thinks.
    `vad` is the Silero model the worker loads once per process."""
    from livekit.plugins import deepgram, groq

    missing = [
        name
        for name, secret in (
            ("DEEPGRAM_API_KEY", settings.deepgram_api_key),
            ("GROQ_API_KEY", settings.groq_api_key),
        )
        if not secret.get_secret_value()
    ]
    if missing:
        raise RehearsalConfigError(f"{', '.join(missing)} not set")
    deepgram_key = settings.deepgram_api_key.get_secret_value()
    return AgentSession(
        stt=deepgram.STT(model=settings.deepgram_stt_model, language="en", api_key=deepgram_key),
        llm=groq.LLM(model=settings.groq_model, api_key=settings.groq_api_key.get_secret_value()),
        tts=deepgram.TTS(model=settings.deepgram_tts_voice, api_key=deepgram_key),
        vad=vad,
    )


def _now(clock: Callable[[], float]) -> datetime:
    return datetime.fromtimestamp(clock(), UTC)


@dataclass
class _Ending:
    by: EndedBy = "seller_left"
    error: str | None = None


async def run_call(
    ctx: Any,
    setup: CallSetup,
    *,
    make_session: Callable[[], AgentSession],
    results: ResultsClient | Any,
    max_minutes: float,
    join_timeout_s: float = JOIN_TIMEOUT_S,
    clock: Callable[[], float] = time.time,
) -> CallReport:
    """One call from the seller joining to the report.

    The call ends when the seller leaves, when the session fails, or after
    `max_minutes`, when the buyer says goodbye. A seller who never joins
    is reported as a no-show, so the session does not stay waiting forever.
    """
    try:
        await asyncio.wait_for(
            ctx.wait_for_participant(identity=setup.seller_identity or None), join_timeout_s
        )
    except TimeoutError:
        log.info("Seller never joined %s", setup.session_id)
        report = CallReport((), "no_show", _now(clock))
        await results.finished(setup.session_id, report)
        return report

    call_start = clock()
    started_at = _now(clock)
    await results.started(setup.session_id, started_at)

    transcript = Transcript(call_start)
    ending = _Ending()
    closed = asyncio.Event()

    def on_close(event: Any) -> None:
        if event.error is not None:
            ending.by, ending.error = "error", str(event.error)
        closed.set()

    try:
        session = make_session()
        session.on("conversation_item_added", lambda event: transcript.add(event.item))
        session.on("close", on_close)
        await session.start(
            agent=BuyerAgent(setup.deal),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                participant_identity=setup.seller_identity or NOT_GIVEN,
                close_on_disconnect=True,
            ),
            # Recording is egress's job; this would upload to LiveKit Cloud.
            record=False,
        )
        session.generate_reply(instructions=opening_instruction(setup.deal))
        try:
            await asyncio.wait_for(closed.wait(), max_minutes * 60)
        except TimeoutError:
            ending.by = "time_limit"
            try:
                await asyncio.wait_for(
                    session.say(TIME_UP_LINE, allow_interruptions=False).wait_for_playout(),
                    GOODBYE_TIMEOUT_S,
                )
            finally:
                await session.aclose()
    except Exception as exc:
        log.exception("Call %s failed", setup.session_id)
        ending.by, ending.error = "error", f"{type(exc).__name__}: {exc}"

    report = CallReport(
        transcript.turns, ending.by, _now(clock), started_at=started_at, error=ending.error
    )
    await results.finished(setup.session_id, report)
    return report
