"""The analysis job on real Postgres and MinIO, with the pipeline faked."""

import uuid
from dataclasses import dataclass, field

import pytest

from ai.analysis.pipeline import AnalysisError
from server.db import AnalysisStatus, PracticeSession, User, VoiceCloneStatus
from server.jobs.analysis import FAILED, AnalysisJob, mark_failed, on_job_failure

pytestmark = pytest.mark.integration


@dataclass
class FakeResult:
    notes: list = field(default_factory=list)

    def to_dict(self):
        return {"overall_score": 70, "notes": list(self.notes), "corrected_answers": []}


class FakeAnalyze:
    def __init__(self, error=None):
        self.error = error
        self.request = None

    def __call__(self, request, *, save_audio, save_video, on_stage):
        self.request = request
        self.recording_bytes = request.recording.read_bytes() if request.recording else None
        on_stage("analyzing")
        if self.error:
            raise self.error
        self.keys = [save_audio(0, b"RIFFwav"), save_video(request.recording or __file__)]
        return FakeResult(notes=["from the pipeline"])


def job(db_sessionmaker, storage, analyze, **kwargs):
    sleeps = []
    return AnalysisJob(
        db_sessionmaker, storage, analyze=analyze, sleep=sleeps.append, **kwargs
    ), sleeps


def row_of(db_sessionmaker, session_id):
    with db_sessionmaker() as db:
        return db.get(PracticeSession, uuid.UUID(session_id))


def test_job_analyses_the_call_with_recording_playbook_and_voice(
    finished_call, db_sessionmaker, storage
):
    with db_sessionmaker() as db:
        user = db.query(User).one()
        user.voice_clone_id, user.voice_clone_status = "voice-9", VoiceCloneStatus.ready
        user.playbook_key = f"users/{user.id}/profile/playbook.txt"
        storage.put_bytes(user.playbook_key, b"Pricing: 40 dollars a seat.", "text/plain")
        user_id = user.id
        db.commit()
    analyze = FakeAnalyze()
    run, _ = job(db_sessionmaker, storage, analyze)
    run(uuid.UUID(finished_call), "audio")

    request = analyze.request
    assert analyze.recording_bytes == b"fake mp4"
    assert "40 dollars a seat" in request.reference.text
    assert (request.voice_id, request.mode) == ("voice-9", "audio")
    assert [t.role for t in request.turns] == ["buyer", "seller"]
    prefix = f"users/{user_id}/sessions/{finished_call}/analysis/"
    assert analyze.keys == [prefix + "corrected-0.wav", prefix + "annotated.mp4"]
    assert sorted(storage.list_prefix(prefix)) == sorted(analyze.keys)

    row = row_of(db_sessionmaker, finished_call)
    assert row.analysis_status is AnalysisStatus.complete
    assert row.analysis_stage is None and row.analysis_error is None
    assert row.analysis_started_at <= row.analysis_finished_at
    assert row.analysis_data == {
        "overall_score": 70,
        "notes": ["from the pipeline"],
        "corrected_answers": [],
    }


def test_clone_that_is_not_ready_is_not_used(finished_call, db_sessionmaker, storage):
    with db_sessionmaker() as db:
        user = db.query(User).one()
        user.voice_clone_id, user.voice_clone_status = "voice-9", VoiceCloneStatus.pending
        db.commit()
    analyze = FakeAnalyze()
    job(db_sessionmaker, storage, analyze)[0](uuid.UUID(finished_call), "audio_video")
    assert analyze.request.voice_id is None
    assert analyze.request.reference is None


def test_recording_that_never_arrives_is_analysed_without(finished_call, db_sessionmaker, storage):
    row = row_of(db_sessionmaker, finished_call)
    storage.delete_prefix(row.recording_key)
    analyze = FakeAnalyze()
    run, sleeps = job(db_sessionmaker, storage, analyze, recording_wait_s=10)
    run(uuid.UUID(finished_call), "audio")
    assert analyze.request.recording is None
    assert sleeps == [5, 5]


def test_unreadable_playbook_is_a_note(finished_call, db_sessionmaker, storage):
    with db_sessionmaker() as db:
        user = db.query(User).one()
        user.playbook_key = f"users/{user.id}/profile/playbook.pdf"
        storage.put_bytes(user.playbook_key, b"not a pdf", "application/pdf")
        db.commit()
    job(db_sessionmaker, storage, FakeAnalyze())[0](uuid.UUID(finished_call), "audio")
    notes = row_of(db_sessionmaker, finished_call).analysis_data["notes"]
    assert notes == [
        "Your playbook could not be read, so answers were judged without it.",
        "from the pipeline",
    ]


def test_a_rerun_replaces_the_last_runs_files(finished_call, db_sessionmaker, storage):
    row = row_of(db_sessionmaker, finished_call)
    stale = f"users/{row.user_id}/sessions/{finished_call}/analysis/corrected-5.wav"
    storage.put_bytes(stale, b"old", "audio/wav")
    job(db_sessionmaker, storage, FakeAnalyze())[0](uuid.UUID(finished_call), "audio")
    assert not storage.exists(stale)


@pytest.mark.parametrize(
    ("error", "message"),
    [(AnalysisError("The call has no speech to analyse."), "The call has no speech to analyse."),
     (RuntimeError("boom"), FAILED)],
)  # fmt: skip
def test_failures_are_recorded_plainly(finished_call, db_sessionmaker, storage, error, message):
    job(db_sessionmaker, storage, FakeAnalyze(error=error))[0](uuid.UUID(finished_call), "audio")
    row = row_of(db_sessionmaker, finished_call)
    assert (row.analysis_status, row.analysis_error) == (AnalysisStatus.failed, message)
    assert row.analysis_data is None


def test_missing_session_is_ignored(db_sessionmaker, storage):
    job(db_sessionmaker, storage, FakeAnalyze())[0](uuid.uuid4(), "audio")


def test_killed_job_is_marked_failed(finished_call, db_sessionmaker, monkeypatch):
    with db_sessionmaker() as db:
        db.get(PracticeSession, uuid.UUID(finished_call)).analysis_status = AnalysisStatus.running
        db.commit()
    monkeypatch.setattr("server.db.session.get_sessionmaker", lambda: db_sessionmaker)
    on_job_failure(type("Job", (), {"args": (finished_call, "audio")})(), None)
    row = row_of(db_sessionmaker, finished_call)
    assert (row.analysis_status, row.analysis_error) == (AnalysisStatus.failed, FAILED)
    # A finished analysis is left alone.
    mark_failed(uuid.UUID(finished_call), db_sessionmaker, "other")
    assert row_of(db_sessionmaker, finished_call).analysis_error == FAILED
