"""Speak corrected answers or a corrected talk in the user's cloned voice.

The voice is cloned once, when the user uploads their sample, and its id is
reused here. Cloning again for every playback, as the first version did,
is slow and costs money on every run.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ai.providers import get_voice_clone_client

from .answers import AnswerCorrection
from .base import ProsodyParams, VoiceCloneClient
from .script import ScriptSegment
from .wav import join_wav, read_wav

# A short lead-in and tail so a clip does not start or stop abruptly.
EDGE_PAUSE_MS = 150


@dataclass(frozen=True)
class AnswerPlayback:
    correction: AnswerCorrection
    audio: bytes  # WAV
    duration_ms: int


def speak_answers(
    corrections: Sequence[AnswerCorrection],
    voice_id: str,
    client: VoiceCloneClient | None = None,
    *,
    include_unverified: bool = False,
) -> tuple[AnswerPlayback, ...]:
    """One clip per corrected answer, spoken with a confident delivery.
    Unverified rewrites (a number from nowhere) are skipped unless asked
    for: the user would hear a claim they cannot back up."""
    voice = client or get_voice_clone_client()
    out = []
    for correction in corrections:
        if not correction.verified and not include_unverified:
            continue
        clip = voice.synthesize(correction.stronger_response, voice_id, ProsodyParams("confident"))
        audio = join_wav([clip], [EDGE_PAUSE_MS])
        out.append(AnswerPlayback(correction, audio, read_wav(audio).duration_ms))
    return tuple(out)


def speak_script(
    segments: Sequence[ScriptSegment],
    voice_id: str,
    client: VoiceCloneClient | None = None,
) -> bytes:
    """The whole corrected talk as one WAV, each segment with its own
    delivery and the pause after it."""
    voice = client or get_voice_clone_client()
    spoken = [s for s in segments if s.text_to_speak.strip()]
    clips = [voice.synthesize(s.text_to_speak, voice_id, s.prosody) for s in spoken]
    return join_wav(clips, [s.prosody.pause_after_ms for s in spoken])
