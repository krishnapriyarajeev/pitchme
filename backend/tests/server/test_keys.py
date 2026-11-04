import uuid

import pytest

from server.storage import keys

UID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def test_profile_keys_keep_extension():
    assert keys.profile_voice_key(UID, "m4a") == f"users/{UID}/profile/voice.m4a"
    assert keys.profile_voice_key(UID, ".WAV") == f"users/{UID}/profile/voice.wav"
    assert keys.profile_playbook_key(UID) == f"users/{UID}/profile/playbook.pdf"


@pytest.mark.parametrize("ext", ["exe", "html", ""])
def test_unknown_extension_rejected(ext):
    with pytest.raises(ValueError):
        keys.profile_voice_key(UID, ext)


def test_session_keys_are_user_scoped():
    prefix = f"users/{UID}/sessions/{SID}/"
    assert keys.recording_key(UID, SID) == prefix + "recording.mp4"
    assert keys.annotated_video_key(UID, SID) == prefix + "analysis/annotated.mp4"
    assert keys.corrected_audio_key(UID, SID, 2) == prefix + "analysis/corrected-2.wav"


@pytest.mark.parametrize(
    ("key", "owned"),
    [
        (f"users/{UID}/profile/voice.wav", True),
        (f"users/{SID}/profile/voice.wav", False),
        (f"users/{UID}/../{SID}/profile/voice.wav", False),
        ("recordings/x.mp4", False),
    ],
)
def test_is_owned_by(key, owned):
    assert keys.is_owned_by(key, UID) is owned
