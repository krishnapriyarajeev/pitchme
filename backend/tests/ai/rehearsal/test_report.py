import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ai.rehearsal.report import CallReport, ResultsClient
from ai.rehearsal.transcript import CallTurn

T0 = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
REPORT = CallReport(
    turns=(CallTurn("buyer", "Hello?", 0, 800),),
    ended_by="seller_left",
    ended_at=T0 + timedelta(seconds=95.5),
    started_at=T0,
)


def test_report_body():
    body = REPORT.to_json()
    assert body["duration_seconds"] == 95.5
    assert body["started_at"] == "2026-11-05T10:00:00+00:00"
    assert body["transcript"][0]["text"] == "Hello?"


def test_no_show_has_no_duration():
    report = CallReport((), "no_show", T0)
    assert report.to_json()["duration_seconds"] is None
    assert report.to_json()["started_at"] is None


def client_for(responses, sleeps):
    calls = []

    def handler(request):
        calls.append(request)
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return httpx.Response(result, text="nope")

    async def sleep(seconds):
        sleeps.append(seconds)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ResultsClient("http://api/", "k" * 32, http=http, sleep=sleep), calls


async def test_results_are_posted_with_the_internal_key():
    sleeps = []
    client, calls = client_for([204], sleeps)
    async with client:
        assert await client.finished("s-1", REPORT)
    (request,) = calls
    assert str(request.url) == "http://api/internal/sessions/s-1/results"
    assert request.headers["X-Internal-Key"] == "k" * 32
    assert json.loads(request.content)["ended_by"] == "seller_left"


async def test_network_errors_and_5xx_are_retried_with_backoff():
    sleeps = []
    client, calls = client_for([httpx.ConnectError("down"), 503, 204], sleeps)
    assert await client.started("s-1", T0)
    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]
    assert json.loads(calls[0].content) == {"started_at": "2026-11-05T10:00:00+00:00"}


@pytest.mark.parametrize("status", [403, 404, 409])
async def test_a_refusal_is_not_retried(status, caplog):
    client, calls = client_for([status], [])
    assert not await client.finished("s-1", REPORT)
    assert len(calls) == 1
    assert f"HTTP {status}" in caplog.text


async def test_gives_up_after_the_last_try(caplog):
    sleeps = []
    client, calls = client_for([500, 500, 500], sleeps)
    assert not await client.finished("s-1", REPORT)
    assert len(calls) == 3 and sleeps == [1.0, 2.0]
    assert "after 3 tries" in caplog.text
