"""Object key layout in the media bucket.

Every object a user owns lives under `users/<user_id>/`, so ownership checks
and delete-my-data are one prefix test or one prefix delete.

    users/<uid>/profile/voice.<ext>
    users/<uid>/profile/playbook.<ext>
    users/<uid>/sessions/<sid>/recording.mp4
    users/<uid>/sessions/<sid>/analysis/annotated.mp4
    users/<uid>/sessions/<sid>/analysis/corrected-<n>.wav
"""

from __future__ import annotations

import uuid
from typing import NewType

ObjectKey = NewType("ObjectKey", str)

VOICE_EXTENSIONS = frozenset({"wav", "m4a", "mp3", "webm", "ogg"})
PLAYBOOK_EXTENSIONS = frozenset({"pdf", "pptx", "docx", "txt"})


def user_prefix(user_id: uuid.UUID | str) -> str:
    return f"users/{user_id}/"


def session_prefix(user_id: uuid.UUID | str, session_id: uuid.UUID | str) -> str:
    return f"{user_prefix(user_id)}sessions/{session_id}/"


def _ext(ext: str, allowed: frozenset[str]) -> str:
    ext = ext.lower().lstrip(".")
    if ext not in allowed:
        raise ValueError(f"unsupported extension {ext!r}; expected one of {sorted(allowed)}")
    return ext


def profile_voice_key(user_id: uuid.UUID | str, ext: str = "wav") -> ObjectKey:
    """The voice sample keeps its real extension (phones record m4a, not wav)."""
    return ObjectKey(f"{user_prefix(user_id)}profile/voice.{_ext(ext, VOICE_EXTENSIONS)}")


def profile_playbook_key(user_id: uuid.UUID | str, ext: str = "pdf") -> ObjectKey:
    return ObjectKey(f"{user_prefix(user_id)}profile/playbook.{_ext(ext, PLAYBOOK_EXTENSIONS)}")


def recording_key(user_id: uuid.UUID | str, session_id: uuid.UUID | str) -> ObjectKey:
    """Where LiveKit egress writes the call recording."""
    return ObjectKey(f"{session_prefix(user_id, session_id)}recording.mp4")


def annotated_video_key(user_id: uuid.UUID | str, session_id: uuid.UUID | str) -> ObjectKey:
    return ObjectKey(f"{session_prefix(user_id, session_id)}analysis/annotated.mp4")


def corrected_audio_key(
    user_id: uuid.UUID | str, session_id: uuid.UUID | str, index: int
) -> ObjectKey:
    return ObjectKey(f"{session_prefix(user_id, session_id)}analysis/corrected-{index}.wav")


def is_owned_by(key: str, user_id: uuid.UUID | str) -> bool:
    """True when the key sits under the user's prefix and has no path tricks."""
    return key.startswith(user_prefix(user_id)) and ".." not in key.split("/")
