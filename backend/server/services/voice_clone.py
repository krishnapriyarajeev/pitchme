"""Clone the user's voice from their uploaded sample.

Runs as a background task after the upload is confirmed, because a clone
takes seconds with Cartesia and minutes with Resemble. The profile shows
`voice_clone_status` meanwhile: pending, then ready or failed. There is no
placeholder voice id: without a working provider the status is failed.

If the user uploads another sample before a clone finishes, the late clone
is thrown away instead of overwriting the newer one, and a clone that is
replaced is deleted from the provider so it is not left behind.
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from ai.providers import get_voice_clone_client
from ai.utils.audio import AudioExtractionError, extract_audio
from ai.utils.media import local_media
from ai.voice_cloning.base import VoiceCloneClient, VoiceCloneError, VoiceSample
from server.db import User, VoiceCloneStatus
from server.storage import Storage

log = logging.getLogger(__name__)

UNREADABLE = "We could not read that recording. Please record your sample again."
UNAVAILABLE = "Voice cloning failed. Please try again later."


@dataclass
class VoiceCloner:
    sessions: sessionmaker[Session]
    storage: Storage
    client_factory: Callable[[], VoiceCloneClient] = get_voice_clone_client

    def __call__(
        self, user_id: uuid.UUID, sample_key: str, previous_clone_id: str | None = None
    ) -> None:
        try:
            client = self.client_factory()
            voice_id = self._clone(client, user_id, sample_key)
        except AudioExtractionError as exc:
            log.warning("Voice sample %s is unreadable: %s", sample_key, exc)
            self._save(user_id, sample_key, VoiceCloneStatus.failed, error=UNREADABLE)
            return
        except Exception as exc:
            # Missing key or SDK, provider error, storage error: the user sees
            # a plain message, the log keeps the detail.
            log.error("Voice clone for user %s failed: %s", user_id, exc)
            self._save(user_id, sample_key, VoiceCloneStatus.failed, error=UNAVAILABLE)
            return

        kept = self._save(user_id, sample_key, VoiceCloneStatus.ready, voice_id=voice_id)
        stale = [previous_clone_id] if kept else [voice_id, previous_clone_id]
        for old in filter(None, stale):
            try:
                client.delete_voice(old)
            except VoiceCloneError as exc:
                log.warning("Could not delete old voice %s: %s", old, exc)

    def _clone(self, client: VoiceCloneClient, user_id: uuid.UUID, sample_key: str) -> str:
        with local_media(sample_key, self.storage) as sample, tempfile.TemporaryDirectory() as tmp:
            # Phones record m4a or webm; providers want plain WAV.
            wav = extract_audio(sample, Path(tmp) / "sample.wav")
            return client.clone_voice(VoiceSample(wav), name=f"pitchme-{user_id}")

    def _save(
        self,
        user_id: uuid.UUID,
        sample_key: str,
        status: VoiceCloneStatus,
        *,
        voice_id: str | None = None,
        error: str | None = None,
    ) -> bool:
        """Store the outcome; False when the sample was replaced meanwhile."""
        with self.sessions() as db:
            user = db.get(User, user_id)
            if user is None or user.voice_sample_key != sample_key:
                return False
            user.voice_clone_id = voice_id
            user.voice_clone_status = status
            user.voice_clone_error = error
            db.commit()
            return True


def mark_pending(db: Session, user: User) -> str | None:
    """Reset the clone for a new attempt; returns the clone it replaces."""
    previous = user.voice_clone_id
    user.voice_clone_id = None
    user.voice_clone_status = VoiceCloneStatus.pending
    user.voice_clone_error = None
    db.commit()
    return previous
