"""Creating, listing and showing rehearsal sessions, on real Postgres and
MinIO with a fake LiveKit."""

import uuid

import pytest

from ai.rehearsal.deal import CallSetup
from server.db import PracticeSession

pytestmark = pytest.mark.integration

DEAL = {
    "prospect_name": "Jo Bennett",
    "company": "Saber Industries",
    "industry": "Office supplies",
    "deal_stage": "Cold call",
    "buyer_composure": "Guarded",
    "competitors": "Staples",
    "audience_type": "VP Sales",
}


def create(client, **changes):
    return client.post("/api/sessions", json={**DEAL, **changes})


def test_create_opens_a_room_with_the_deal_and_records_it(signed_in, live_calls, db_sessionmaker):
    signed_in.put("/api/profile", json={"sells": "Payroll software", "role_title": "AE"})
    response = create(signed_in)
    assert response.status_code == 201
    body = response.json()
    session_id = body["session_id"]
    room = f"rehearsal-{session_id}"
    assert body["room_name"] == room
    assert body["livekit_url"] == "ws://192.168.1.5:7880"

    setup = CallSetup.from_metadata(live_calls.rooms[room])
    user_id = signed_in.get("/api/profile").json()["id"]
    assert setup.session_id == session_id
    assert setup.seller_identity == f"seller-{user_id}"
    assert body["token"] == f"token:{room}:seller-{user_id}:KP"
    assert setup.deal.deal_stage == "cold_call"
    assert setup.deal.audience_type == "vp_sales"
    assert (setup.deal.product, setup.deal.seller_role) == ("Payroll software", "AE")

    key = f"users/{user_id}/sessions/{session_id}/recording.mp4"
    assert live_calls.recordings == [(room, key)]
    with db_sessionmaker() as db:
        row = db.get(PracticeSession, uuid.UUID(session_id))
        assert (row.status, row.egress_id, row.recording_key) == ("waiting", "EG_1", key)
        assert (row.deal_stage, row.buyer_composure, row.audience_type) == (
            "cold_call",
            "guarded",
            "vp_sales",
        )


def test_livekit_down_saves_nothing(signed_in, live_calls):
    live_calls.fail_create = True
    response = create(signed_in)
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Live calls are not available right now. Please try again in a minute.",
        "code": "live_call_unavailable",
    }
    assert signed_in.get("/api/sessions").json() == []


def test_call_goes_on_without_a_recording(signed_in, live_calls, db_sessionmaker):
    live_calls.fail_recording = True
    session_id = create(signed_in).json()["session_id"]
    with db_sessionmaker() as db:
        row = db.get(PracticeSession, uuid.UUID(session_id))
        assert (row.egress_id, row.recording_key) == (None, None)


@pytest.mark.parametrize(
    ("field", "value"),
    [("deal_stage", "lunch"), ("audience_type", "astronaut"), ("prospect_name", "  "),
     ("buyer_composure", "sleepy"), ("company", "x" * 121)],
)  # fmt: skip
def test_bad_deal_is_rejected(signed_in, live_calls, field, value):
    response = create(signed_in, **{field: value})
    assert response.status_code == 422
    assert live_calls.rooms == {}


def test_needs_sign_in(api):
    assert create(api).status_code == 401


def test_list_is_newest_first_and_paged(signed_in):
    ids = [create(signed_in, company=f"Co {i}").json()["session_id"] for i in range(3)]
    listed = signed_in.get("/api/sessions").json()
    assert [s["session_id"] for s in listed] == ids[::-1]
    assert listed[0]["status"] == "waiting"
    assert listed[0]["analysis_status"] == "not_started"
    page = signed_in.get("/api/sessions", params={"limit": 1, "offset": 1}).json()
    assert [s["session_id"] for s in page] == [ids[1]]
    assert signed_in.get("/api/sessions", params={"limit": 0}).status_code == 422


def test_others_cannot_see_a_session(signed_in, api):
    session_id = create(signed_in).json()["session_id"]
    other = api.post(
        "/api/auth/register", json={"email": "other@example.com", "password": "rehearse-daily"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {other}"}
    assert api.get(f"/api/sessions/{session_id}", headers=headers).status_code == 404
    assert api.get("/api/sessions", headers=headers).json() == []


def test_detail_before_the_call(signed_in):
    session_id = create(signed_in).json()["session_id"]
    detail = signed_in.get(f"/api/sessions/{session_id}").json()
    assert detail["transcript"] == []
    assert detail["recording_url"] is None  # egress has not uploaded yet
    assert detail["competitors"] == "Staples"
    assert signed_in.get(f"/api/sessions/{uuid.uuid4()}").status_code == 404


def test_detail_links_the_recording_once_it_is_stored(signed_in, storage, db_sessionmaker):
    session_id = create(signed_in).json()["session_id"]
    with db_sessionmaker() as db:
        key = db.get(PracticeSession, uuid.UUID(session_id)).recording_key
    storage.put_bytes(key, b"mp4", "video/mp4")
    url = signed_in.get(f"/api/sessions/{session_id}").json()["recording_url"]
    assert "recording.mp4" in url and "X-Amz-Signature" in url
