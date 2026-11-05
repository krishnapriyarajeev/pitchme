"""A whole call driven with a fake room and a fake agent session."""

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("livekit.agents", reason="needs the rehearsal extra")

from ai.config import AISettings
from ai.rehearsal.agent import (
    TIME_UP_LINE,
    BuyerAgent,
    RehearsalConfigError,
    build_session,
    run_call,
)
from ai.rehearsal.deal import CallSetup, Deal

SETUP = CallSetup("s-1", "user-1", Deal("Jo", "Saber", deal_stage="cold_call"))


class Clock:
    def __init__(self):
        self.now = 1_000.0

    def __call__(self):
        return self.now


class FakeCtx:
    def __init__(self, joins=True):
        self.joins = joins
        self.room = object()
        self.waited_for = None

    async def wait_for_participant(self, identity=None):
        self.waited_for = identity
        if not self.joins:
            await asyncio.Event().wait()


class FakeHandle:
    def __init__(self, session):
        self.session = session

    async def wait_for_playout(self):
        pass


class FakeSession:
    """Plays a scripted call: each item is (role, text, start, stop) in
    seconds after the call start, then the seller hangs up (or not)."""

    def __init__(self, clock, script=(), hang_up=True, error=None):
        self.clock, self.script, self.hang_up, self.error = clock, script, hang_up, error
        self.handlers, self.said, self.started_with = {}, [], None
        self.closed = False

    def on(self, event, handler):
        self.handlers[event] = handler

    def _emit(self, event, payload):
        self.handlers[event](payload)

    async def start(self, *, agent, room, room_options, record):
        self.started_with = SimpleNamespace(agent=agent, options=room_options, record=record)

    def generate_reply(self, *, instructions):
        self.opening = instructions
        base = self.clock.now
        for role, text, start, stop in self.script:
            item = SimpleNamespace(
                role=role, text_content=text, created_at=base + stop, interrupted=False,
                metrics={"started_speaking_at": base + start, "stopped_speaking_at": base + stop},
            )  # fmt: skip
            self._emit("conversation_item_added", SimpleNamespace(item=item))
        if self.hang_up:
            self.clock.now += 95
            self._emit("close", SimpleNamespace(error=self.error))

    def say(self, text, allow_interruptions):
        self.said.append(text)
        return FakeHandle(self)

    async def aclose(self):
        self.closed = True


class FakeResults:
    def __init__(self):
        self.started_calls, self.reports = [], []

    async def started(self, session_id, at):
        self.started_calls.append((session_id, at))
        return True

    async def finished(self, session_id, report):
        self.reports.append((session_id, report))
        return True


async def test_call_from_join_to_hang_up():
    clock, results = Clock(), FakeResults()
    session = FakeSession(
        clock,
        script=[
            ("user", "Hi Jo, it's Sam.", 3.0, 4.5),
            ("assistant", "Yes, who is this?", 0.2, 1.4),
            ("system", "ignored", 0, 0),
        ],
    )
    ctx = FakeCtx()
    report = await run_call(
        ctx, SETUP, make_session=lambda: session, results=results, max_minutes=20, clock=clock
    )
    assert ctx.waited_for == "user-1"
    assert isinstance(session.started_with.agent, BuyerAgent)
    assert session.started_with.options.participant_identity == "user-1"
    assert session.started_with.record is False
    assert "Yes, who is this?" in session.opening  # cold-call opening
    assert [(t.role, t.start_ms) for t in report.turns] == [("buyer", 200), ("seller", 3000)]
    assert report.ended_by == "seller_left" and report.error is None
    assert (report.ended_at - report.started_at).total_seconds() == 95
    assert results.started_calls == [("s-1", report.started_at)]
    assert results.reports == [("s-1", report)]


async def test_seller_who_never_joins_is_a_no_show():
    results = FakeResults()
    report = await run_call(
        FakeCtx(joins=False), SETUP, make_session=pytest.fail, results=results,
        max_minutes=20, join_timeout_s=0.01,
    )  # fmt: skip
    assert report.ended_by == "no_show" and report.started_at is None
    assert results.started_calls == []
    assert results.reports == [("s-1", report)]


async def test_time_limit_ends_with_a_goodbye():
    clock, results = Clock(), FakeResults()
    session = FakeSession(clock, hang_up=False)
    report = await run_call(
        FakeCtx(), SETUP, make_session=lambda: session, results=results,
        max_minutes=0.0002, clock=clock,
    )  # fmt: skip
    assert report.ended_by == "time_limit"
    assert session.said == [TIME_UP_LINE]
    assert session.closed


async def test_session_error_is_reported():
    clock, results = Clock(), FakeResults()
    session = FakeSession(clock, error=RuntimeError("tts failed"))
    report = await run_call(
        FakeCtx(), SETUP, make_session=lambda: session, results=results, max_minutes=20,
        clock=clock,
    )  # fmt: skip
    assert (report.ended_by, report.error) == ("error", "tts failed")


async def test_missing_keys_end_the_call_with_an_error():
    def no_keys():
        return build_session(AISettings(_env_file=None), vad=None)

    results = FakeResults()
    report = await run_call(FakeCtx(), SETUP, make_session=no_keys, results=results, max_minutes=20)
    assert report.ended_by == "error"
    assert report.error == ("RehearsalConfigError: DEEPGRAM_API_KEY, GROQ_API_KEY not set")
    assert results.reports[0][1] is report


def test_build_session_names_each_missing_key():
    settings = AISettings(_env_file=None, groq_api_key="g")
    with pytest.raises(RehearsalConfigError, match=r"^DEEPGRAM_API_KEY not set$"):
        build_session(settings, vad=None)


async def test_build_session_with_keys():
    pytest.importorskip("livekit.plugins.deepgram")
    settings = AISettings(_env_file=None, groq_api_key="g", deepgram_api_key="d")
    session = build_session(settings, vad=None)
    assert session.stt is not None and session.tts is not None and session.llm is not None
