"""What the agent worker reports: the seller joined, and how the call ended."""

import uuid

import pytest

from tests.server.conftest import CALLBACK_KEY

pytestmark = pytest.mark.integration

KEY = {"X-Internal-Key": CALLBACK_KEY}
TURNS = [
    {"role": "buyer", "text": "Yes, who is this?", "start_ms": 300, "end_ms": 1400},
    {"role": "seller", "text": "Sam from PitchMe.", "start_ms": 2000, "end_ms": 3500,
     "interrupted": True},
]  # fmt: skip


def results(ended_by="seller_left", **changes):
    return {
        "transcript": TURNS,
        "ended_by": ended_by,
        "started_at": "2026-11-05T10:00:00Z",
        "ended_at": "2026-11-05T10:01:35Z",
        "duration_seconds": 95.04,
        **changes,
    }


@pytest.fixture
def session_id(signed_in):
    return signed_in.post("/api/sessions", json={"prospect_name": "Jo", "company": "Saber"}).json()[
        "session_id"
    ]


def test_a_full_call(signed_in, session_id):
    started = signed_in.post(
        f"/internal/sessions/{session_id}/started",
        json={"started_at": "2026-11-05T10:00:00Z"},
        headers=KEY,
    )
    assert started.status_code == 204
    assert signed_in.get(f"/api/sessions/{session_id}").json()["status"] == "active"

    done = signed_in.post(f"/internal/sessions/{session_id}/results", json=results(), headers=KEY)
    assert done.status_code == 204
    detail = signed_in.get(f"/api/sessions/{session_id}").json()
    assert detail["status"] == "complete"
    assert detail["end_reason"] == "seller_left"
    assert detail["duration_seconds"] == 95.0
    assert detail["started_at"].startswith("2026-11-05T10:00:00")
    assert detail["transcript"][1] == {**TURNS[1]}
    assert detail["transcript"][0]["interrupted"] is False


@pytest.mark.parametrize(
    ("ended_by", "status"),
    [("time_limit", "complete"), ("error", "failed"), ("no_show", "failed")],
)
def test_how_the_call_ended_sets_the_status(signed_in, session_id, ended_by, status):
    body = results(ended_by, error="tts failed" if ended_by == "error" else None)
    assert signed_in.post(
        f"/internal/sessions/{session_id}/results", json=body, headers=KEY
    ).status_code == 204  # fmt: skip
    detail = signed_in.get(f"/api/sessions/{session_id}").json()
    assert (detail["status"], detail["end_reason"]) == (status, ended_by)


def test_no_show_keeps_no_recording(signed_in, session_id, storage, db_sessionmaker):
    from server.db import PracticeSession

    with db_sessionmaker() as db:
        key = db.get(PracticeSession, uuid.UUID(session_id)).recording_key
    storage.put_bytes(key, b"empty room", "video/mp4")
    body = results("no_show", started_at=None, duration_seconds=None, transcript=[])
    signed_in.post(f"/internal/sessions/{session_id}/results", json=body, headers=KEY)
    detail = signed_in.get(f"/api/sessions/{session_id}").json()
    assert detail["recording_url"] is None
    assert detail["started_at"] is None


def test_each_report_is_accepted_once(signed_in, session_id):
    url = f"/internal/sessions/{session_id}"
    started = {"started_at": "2026-11-05T10:00:00Z"}
    assert signed_in.post(f"{url}/started", json=started, headers=KEY).status_code == 204
    assert signed_in.post(f"{url}/started", json=started, headers=KEY).status_code == 409
    assert signed_in.post(f"{url}/results", json=results(), headers=KEY).status_code == 204
    second = signed_in.post(f"{url}/results", json=results("error"), headers=KEY)
    assert second.status_code == 409
    assert signed_in.get(f"/api/sessions/{session_id}").json()["status"] == "complete"
    assert signed_in.post(f"{url}/started", json=started, headers=KEY).status_code == 409


def test_results_without_a_started_report(signed_in, session_id):
    url = f"/internal/sessions/{session_id}/results"
    assert signed_in.post(url, json=results(), headers=KEY).status_code == 204


@pytest.mark.parametrize("headers", [{}, {"X-Internal-Key": "wrong"}])
def test_needs_the_internal_key(api, session_id, headers):
    response = api.post(f"/internal/sessions/{session_id}/results", json=results(), headers=headers)
    assert response.status_code == 403


def test_a_user_token_is_not_enough(signed_in, session_id):
    url = f"/internal/sessions/{session_id}/results"
    assert signed_in.post(url, json=results()).status_code == 403


def test_unknown_session(api):
    url = f"/internal/sessions/{uuid.uuid4()}/results"
    assert api.post(url, json=results(), headers=KEY).status_code == 404


@pytest.mark.parametrize(
    "change",
    [{"ended_by": "bored"}, {"duration_seconds": -1},
     {"transcript": [{"role": "narrator", "text": "x", "start_ms": 0, "end_ms": 0}]}],
)  # fmt: skip
def test_malformed_results_are_rejected(api, session_id, change):
    url = f"/internal/sessions/{session_id}/results"
    assert api.post(url, json=results(**change), headers=KEY).status_code == 422
