"""Starting an analysis and reading it back, with the queue on fakeredis."""

import uuid

import pytest
from sqlalchemy import text

from server.db import AnalysisStatus, PracticeSession
from server.jobs.analysis import AnalysisJob
from server.services.analysis import NOT_STARTED, STOPPED

pytestmark = pytest.mark.integration

RESULT = {
    "overall_score": 72,
    "dimensions": [{"name": "content", "label": "Content", "score": 72, "summary": "Ok.",
                    "skipped": None}],
    "summary": "Price was dodged.",
    "findings": [{"pipeline": "content", "category": "dodged", "severity": "high",
                  "summary": "Dodged price.", "note": {"t_start_ms": 0, "t_end_ms": 900,
                  "quote": "What does it cost?"}, "details": {}}],
    "strengths": [],
    "prep_list": ["Dodged price."],
    "corrected_answers": [{"question": "What does it cost?", "original": "It depends.",
                           "stronger": "40 dollars a seat.", "change": "Gave the price.",
                           "citation": "", "verified": True, "unsupported_numbers": [],
                           "t_start_ms": 1200, "audio_key": None}],
    "questions": 1,
    "handled": 0,
    "metrics": {},
    "annotated_video_key": None,
    "notes": [],
}  # fmt: skip


def analyze(client, session_id, **body):
    return client.post(f"/api/sessions/{session_id}/analyze", json=body or None)


def analysis(client, session_id):
    return client.get(f"/api/sessions/{session_id}/analysis")


def test_only_a_finished_call_can_be_analysed(signed_in):
    session_id = signed_in.post(
        "/api/sessions", json={"prospect_name": "Jo", "company": "Saber"}
    ).json()["session_id"]
    response = analyze(signed_in, session_id)
    assert response.status_code == 409
    assert analysis(signed_in, session_id).json()["status"] == "not_started"


def test_analyze_queues_one_job(signed_in, finished_call, analysis_queue):
    response = analyze(signed_in, finished_call, mode="audio")
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    (job,) = analysis_queue.jobs
    assert job.func_name == "server.jobs.analysis.run_session_analysis"
    assert job.args == (finished_call, "audio")
    assert job.timeout == 30 * 60
    # A second request while it waits does not queue another.
    assert analyze(signed_in, finished_call).json()["status"] == "queued"
    assert len(analysis_queue.jobs) == 1


def test_default_mode_includes_video(signed_in, finished_call, analysis_queue):
    analyze(signed_in, finished_call)
    assert analysis_queue.jobs[0].args[1] == "audio_video"


def test_redis_down_is_unavailable_and_changes_nothing(signed_in, finished_call, analysis_queue):
    def down(*args, **kwargs):
        raise ConnectionError("redis down")

    analysis_queue.enqueue = down
    response = analyze(signed_in, finished_call)
    assert response.status_code == 503
    assert response.json()["code"] == "analysis_unavailable"
    assert analysis(signed_in, finished_call).json()["status"] == "not_started"


def test_result_has_fresh_links(signed_in, finished_call, db_sessionmaker, storage):
    analyze(signed_in, finished_call)
    with db_sessionmaker() as db:
        row = db.get(PracticeSession, uuid.UUID(finished_call))
        prefix = f"users/{row.user_id}/sessions/{finished_call}/analysis/"
    data = {
        **RESULT,
        "corrected_answers": [{**RESULT["corrected_answers"][0], "audio_key": prefix + "c.wav"}],
        "annotated_video_key": prefix + "annotated.mp4",
    }

    class Done:
        def to_dict(self):
            return dict(data)

    AnalysisJob(db_sessionmaker, storage, analyze=lambda request, **kw: Done())(
        uuid.UUID(finished_call), "audio_video"
    )
    body = analysis(signed_in, finished_call).json()
    assert body["status"] == "complete" and body["error"] is None
    result = body["result"]
    assert result["overall_score"] == 72
    assert result["findings"][0]["note"]["quote"] == "What does it cost?"
    assert "c.wav" in result["corrected_answers"][0]["audio_url"]
    assert "audio_key" not in result["corrected_answers"][0]
    assert "X-Amz-Signature" in result["annotated_video_url"]
    summary = signed_in.get("/api/sessions").json()[0]
    assert (summary["analysis_status"], summary["overall_score"]) == ("complete", 72)


def test_a_failed_analysis_can_be_run_again(
    signed_in, finished_call, db_sessionmaker, analysis_queue
):
    with db_sessionmaker() as db:
        row = db.get(PracticeSession, uuid.UUID(finished_call))
        row.analysis_status, row.analysis_error = AnalysisStatus.failed, "boom"
        db.commit()
    assert analysis(signed_in, finished_call).json()["error"] == "boom"
    response = analyze(signed_in, finished_call)
    assert response.json() | {"started_at": None} == {
        "status": "queued", "stage": None, "error": None, "started_at": None,
        "finished_at": None,
    }  # fmt: skip


def _age(db_sessionmaker, session_id, status, column, minutes):
    with db_sessionmaker() as db:
        db.execute(
            text(
                f"UPDATE practice_sessions SET analysis_status = :s, {column} = "
                f"now() - make_interval(mins => :m) WHERE id = :id"
            ),
            {"s": status, "m": minutes, "id": session_id},
        )
        db.commit()


def test_a_job_no_worker_took_is_given_up(signed_in, finished_call, db_sessionmaker):
    _age(db_sessionmaker, finished_call, "queued", "updated_at", 11)
    body = analysis(signed_in, finished_call).json()
    assert (body["status"], body["error"]) == ("failed", NOT_STARTED)


def test_a_job_that_died_is_marked_failed(signed_in, finished_call, db_sessionmaker):
    _age(db_sessionmaker, finished_call, "running", "analysis_started_at", 36)
    body = analysis(signed_in, finished_call).json()
    assert (body["status"], body["error"]) == ("failed", STOPPED)


def test_a_running_job_is_left_alone(signed_in, finished_call, db_sessionmaker, analysis_queue):
    _age(db_sessionmaker, finished_call, "running", "analysis_started_at", 5)
    assert analysis(signed_in, finished_call).json()["status"] == "running"
    assert analyze(signed_in, finished_call).json()["status"] == "running"
    assert analysis_queue.jobs == []


def test_others_cannot_analyse_or_read(api, finished_call):
    other = api.post(
        "/api/auth/register", json={"email": "o@example.com", "password": "rehearse-daily"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {other}"}
    assert api.post(f"/api/sessions/{finished_call}/analyze", headers=headers).status_code == 404
    assert api.get(f"/api/sessions/{finished_call}/analysis", headers=headers).status_code == 404
