"""The analysis job: one finished call through ai.analysis.

Runs on the RQ worker (`make worker`), never in the API process, so an
API restart cannot lose the job or leave the session "running" forever.
Progress is written to the
session row (analysis_status and analysis_stage), which the app polls.
"""

from __future__ import annotations

import logging
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai.analysis.pipeline import AnalysisError, AnalysisRequest, run_analysis
from ai.rehearsal.transcript import CallTurn
from server.db import AnalysisStatus, PracticeSession, VoiceCloneStatus
from server.storage import Storage, keys

log = logging.getLogger(__name__)

FAILED = "The analysis failed. Run it again."
# Egress uploads the recording a few seconds after the call ends.
RECORDING_WAIT_S = 30


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class _Snapshot:
    user_id: uuid.UUID
    turns: tuple[CallTurn, ...]
    recording_key: str | None
    playbook_key: str | None
    voice_id: str | None


@dataclass
class AnalysisJob:
    sessions: sessionmaker[Session]
    storage: Storage
    analyze: Callable[..., Any] = run_analysis
    sleep: Callable[[float], None] = time.sleep
    recording_wait_s: float = RECORDING_WAIT_S
    notes: list[str] = field(default_factory=list)

    def __call__(self, session_id: uuid.UUID, mode: str) -> None:
        snapshot = self._start(session_id)
        if snapshot is None:
            return
        self.notes = []
        try:
            data = self._run(session_id, snapshot, mode)
        except AnalysisError as exc:
            self._finish(session_id, AnalysisStatus.failed, error=str(exc))
        except Exception:
            log.exception("Analysis of session %s failed", session_id)
            self._finish(session_id, AnalysisStatus.failed, error=FAILED)
        else:
            self._finish(session_id, AnalysisStatus.complete, data=data)

    # ---- steps ----

    def _start(self, session_id: uuid.UUID) -> _Snapshot | None:
        with self.sessions() as db:
            row = db.get(PracticeSession, session_id)
            if row is None:
                log.warning("Analysis job for missing session %s", session_id)
                return None
            row.analysis_status = AnalysisStatus.running
            row.analysis_stage = "preparing"
            row.analysis_started_at = _now()
            row.analysis_finished_at = None
            row.analysis_error = None
            user = row.user
            snapshot = _Snapshot(
                user_id=user.id,
                turns=tuple(CallTurn(**turn) for turn in row.transcript or []),
                recording_key=row.recording_key,
                playbook_key=user.playbook_key,
                voice_id=user.voice_clone_id
                if user.voice_clone_status is VoiceCloneStatus.ready
                else None,
            )
            db.commit()
            return snapshot

    def _run(self, session_id: uuid.UUID, snap: _Snapshot, mode: str) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="pitchme-job-") as tmp:
            workdir = Path(tmp)
            recording = self._recording(snap.recording_key, workdir)
            reference = self._reference(snap.playbook_key, workdir)
            # A rerun replaces the last run's files.
            self.storage.delete_prefix(keys.session_prefix(snap.user_id, session_id) + "analysis/")

            def save_audio(index: int, wav: bytes) -> str:
                key = keys.corrected_audio_key(snap.user_id, session_id, index)
                return self.storage.put_bytes(key, wav, "audio/wav")

            def save_video(path: Path) -> str:
                key = keys.annotated_video_key(snap.user_id, session_id)
                return self.storage.put_file(key, path, "video/mp4")

            result = self.analyze(
                AnalysisRequest(
                    turns=snap.turns,
                    recording=recording,
                    reference=reference,
                    voice_id=snap.voice_id,
                    mode=mode,
                ),
                save_audio=save_audio,
                save_video=save_video,
                on_stage=lambda stage: self._stage(session_id, stage),
            )
        data = result.to_dict()
        data["notes"] = self.notes + data["notes"]
        return data

    def _recording(self, key: str | None, workdir: Path) -> Path | None:
        if not key:
            return None
        waited = 0.0
        while not self.storage.exists(key):
            if waited >= self.recording_wait_s:
                log.warning("Recording %s never arrived", key)
                return None
            self.sleep(5)
            waited += 5
        return self.storage.get_file(key, workdir / "recording.mp4")

    def _reference(self, key: str | None, workdir: Path) -> Any:
        """The user's playbook, which the content judge checks answers
        against."""
        if not key:
            return None
        from ai.content.reference import ReferenceExtractionError, extract_reference

        try:
            path = self.storage.get_file(key, workdir / Path(key).name)
            return extract_reference(path)
        except (ReferenceExtractionError, OSError, ValueError) as exc:
            log.warning("Could not read playbook %s: %s", key, exc)
            self.notes.append("Your playbook could not be read, so answers were judged without it.")
            return None

    def _stage(self, session_id: uuid.UUID, stage: str) -> None:
        with self.sessions() as db:
            row = db.get(PracticeSession, session_id)
            if row is not None:
                row.analysis_stage = stage
                db.commit()

    def _finish(
        self,
        session_id: uuid.UUID,
        status: AnalysisStatus,
        *,
        data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self.sessions() as db:
            row = db.get(PracticeSession, session_id)
            if row is None:
                return
            row.analysis_status = status
            row.analysis_stage = None
            row.analysis_finished_at = _now()
            row.analysis_error = error
            if data is not None:
                row.analysis_data = data
            db.commit()


def mark_failed(session_id: uuid.UUID, sessions: sessionmaker[Session], error: str) -> None:
    with sessions() as db:
        row = db.get(PracticeSession, session_id)
        if row is not None and row.analysis_status in (
            AnalysisStatus.queued,
            AnalysisStatus.running,
        ):
            row.analysis_status = AnalysisStatus.failed
            row.analysis_stage = None
            row.analysis_error = error
            row.analysis_finished_at = _now()
            db.commit()


# ---- what RQ calls (module-level so the worker can import them) ----


def run_session_analysis(session_id: str, mode: str) -> None:
    from server.db.session import get_sessionmaker
    from server.storage import get_storage

    AnalysisJob(get_sessionmaker(), get_storage())(uuid.UUID(session_id), mode)


def on_job_failure(job: Any, connection: Any, *exc_info: Any) -> None:
    """RQ calls this when the job is killed (for example on timeout), when
    the job itself had no chance to record the failure."""
    from server.db.session import get_sessionmaker

    mark_failed(uuid.UUID(job.args[0]), get_sessionmaker(), FAILED)
