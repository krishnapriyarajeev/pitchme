from types import SimpleNamespace

import pytest

pytest.importorskip("livekit.agents", reason="needs the rehearsal extra")

from ai.rehearsal.deal import CallSetup, Deal
from ai.rehearsal.worker import CONSOLE_SETUP, accept_rehearsals, build_server


class FakeRequest:
    def __init__(self, metadata):
        self.room = SimpleNamespace(name="room", metadata=metadata)
        self.outcome = None

    async def accept(self, **kwargs):
        self.outcome = ("accept", kwargs)

    async def reject(self):
        self.outcome = ("reject", {})


async def test_rehearsal_rooms_are_joined_as_the_buyer():
    request = FakeRequest(CallSetup("s-1", "user-1", Deal("Jo", "Saber")).to_metadata())
    await accept_rehearsals(request)
    assert request.outcome == ("accept", {"name": "Buyer", "identity": "buyer"})


@pytest.mark.parametrize("metadata", ["", '{"kind": "other"}'])
async def test_other_rooms_are_left_alone(metadata):
    request = FakeRequest(metadata)
    await accept_rehearsals(request)
    assert request.outcome == ("reject", {})


def test_console_buyer_talks_to_whoever_joins():
    assert CONSOLE_SETUP.seller_identity == ""


def test_server_builds_from_settings():
    from ai.config import AISettings

    server = build_server(AISettings(_env_file=None, livekit_api_secret="s" * 32))
    assert server is not None


class FakeJobCtx:
    def __init__(self, metadata, console=False):
        self.job = SimpleNamespace(room=SimpleNamespace(metadata=metadata))
        self.room = SimpleNamespace(name="rehearsal-s-1")
        self.proc = SimpleNamespace(userdata={"vad": "silero"})
        self.console = console
        self.events = []

    def is_fake_job(self):
        return self.console

    async def connect(self):
        self.events.append("connect")

    async def delete_room(self):
        self.events.append("delete_room")

    def shutdown(self):
        self.events.append("shutdown")


@pytest.mark.parametrize("console", [False, True])
async def test_job_runs_the_call_then_deletes_the_room(console, monkeypatch):
    from ai.config import AISettings
    from ai.rehearsal import worker

    setup = CallSetup("s-1", "user-1", Deal("Jo", "Saber"))
    seen = {}

    async def fake_run_call(ctx, setup, *, make_session, results, max_minutes):
        seen.update(setup=setup, results=results, max_minutes=max_minutes)
        ctx.events.append("call")

    monkeypatch.setattr(worker, "run_call", fake_run_call)
    ctx = FakeJobCtx(setup.to_metadata(), console=console)
    await worker.run_job(ctx, AISettings(_env_file=None, rehearsal_max_minutes=7))

    assert ctx.events == ["connect", "call", "delete_room", "shutdown"]
    assert seen["max_minutes"] == 7
    if console:
        assert seen["setup"] is CONSOLE_SETUP
        assert await seen["results"].finished("console", None)
        assert await seen["results"].started("console", None)
    else:
        assert seen["setup"] == setup
        assert isinstance(seen["results"], worker.ResultsClient)


def test_entrypoint_can_be_sent_to_a_job_process():
    """LiveKit pickles the entrypoint into each job process; a nested
    function cannot be pickled and every call failed to start."""
    import pickle

    from ai.rehearsal import worker

    assert pickle.loads(pickle.dumps(worker.entrypoint)) is worker.entrypoint


async def test_entrypoint_runs_the_job_with_current_settings(monkeypatch):
    from ai.rehearsal import worker

    seen = []

    async def fake_run_job(ctx, settings):
        seen.append((ctx, settings.agent_port))

    monkeypatch.setattr(worker, "run_job", fake_run_job)
    await worker.entrypoint("ctx")
    assert seen == [("ctx", worker.get_ai_settings().agent_port)]
