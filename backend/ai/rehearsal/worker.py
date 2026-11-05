"""The LiveKit agent worker: joins each rehearsal room and plays the buyer.

Start it with `make agent` (scripts/run_agent.py). The API creates a room
with a CallSetup in its metadata; LiveKit hands the room to this worker,
which runs the call, reports the result to the API and deletes the room
so the recording stops at once instead of recording silence.
"""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents import AgentServer, JobContext, JobProcess, JobRequest

from ai.config import AISettings, get_ai_settings

from .agent import build_session, run_call
from .deal import CallSetup, Deal, InvalidSetup
from .report import ResultsClient

log = logging.getLogger(__name__)

# Used by `console` mode, which has no room and no API to report to. An
# empty identity means whoever joins first: the local microphone.
CONSOLE_SETUP = CallSetup(
    session_id="console",
    seller_identity="",
    deal=Deal(
        "Jo Bennett",
        "Saber Industries",
        deal_stage="discovery",
        industry="Office supplies",
        buyer_composure="direct",
        competitors="Staples, Office Depot",
        audience_type="vp_sales",
        product="Sales rehearsal with an AI buyer",
    ),
)


async def accept_rehearsals(request: JobRequest) -> None:
    """Join only rooms the API made for a rehearsal."""
    try:
        CallSetup.from_metadata(request.room.metadata)
    except InvalidSetup as exc:
        log.info("Not joining room %s: %s", request.room.name, exc)
        await request.reject()
        return
    await request.accept(name="Buyer", identity="buyer")


def load_vad(proc: JobProcess) -> None:
    """Load Silero once per process, not once per call."""
    from livekit.plugins import silero

    proc.userdata["vad"] = silero.VAD.load()


def build_server(settings: AISettings | None = None) -> AgentServer:
    settings = settings or get_ai_settings()
    server = AgentServer(
        ws_url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret.get_secret_value(),
        port=settings.agent_port,
        num_idle_processes=settings.agent_idle_processes,
        setup_fnc=load_vad,
    )

    server.rtc_session(entrypoint, on_request=accept_rehearsals)
    return server


async def entrypoint(ctx: JobContext) -> None:
    """Runs in a job process, so it is a module-level function (it is
    pickled) and reads the settings itself."""
    await run_job(ctx, get_ai_settings())


async def run_job(ctx: JobContext, settings: AISettings) -> None:
    console = ctx.is_fake_job()
    setup = CONSOLE_SETUP if console else CallSetup.from_metadata(ctx.job.room.metadata)
    await ctx.connect()
    log.info("Rehearsal %s in room %s", setup.session_id, ctx.room.name)

    results = ResultsClient(
        settings.server_public_base_url, settings.ai_callback_key.get_secret_value()
    )
    async with results:
        await run_call(
            ctx,
            setup,
            make_session=lambda: build_session(settings, ctx.proc.userdata["vad"]),
            results=_NoReport() if console else results,
            max_minutes=settings.rehearsal_max_minutes,
        )
    await ctx.delete_room()
    ctx.shutdown()


class _NoReport:
    """Console mode has no API to report to."""

    async def started(self, *args: Any) -> bool:
        return True

    async def finished(self, *args: Any) -> bool:
        return True
