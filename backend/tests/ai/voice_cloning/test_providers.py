from types import SimpleNamespace

import pytest

from ai.config import AISettings
from ai.providers import make_voice_clone_client
from ai.providers.cartesia.voice_clone import OUTPUT_FORMAT, CartesiaVoiceClient
from ai.providers.resemble.voice_clone import ResembleVoiceClient
from ai.voice_cloning.base import ProsodyParams, VoiceCloneError, VoiceSample

from .fakes import tone_wav


def _settings(**values):
    return AISettings(_env_file=None, **values)


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "me.wav"
    path.write_bytes(tone_wav(200))
    return path


class FakeCartesia:
    def __init__(self, error=None):
        self.calls = []
        self.error = error
        self.voices = SimpleNamespace(clone=self._clone, delete=self._delete)
        self.tts = SimpleNamespace(generate=self._generate)

    def _clone(self, **kwargs):
        name, handle = kwargs["clip"]
        self.calls.append(("clone", name, len(handle.read()), kwargs["name"], kwargs["language"]))
        if self.error:
            raise self.error
        return SimpleNamespace(id="voice-123")

    def _generate(self, **kwargs):
        self.calls.append(("tts", kwargs))
        if self.error:
            raise self.error
        return SimpleNamespace(read=lambda: b"RIFF...")

    def _delete(self, voice_id):
        self.calls.append(("delete", voice_id))


def test_cartesia_clones_from_the_sample_file(sample):
    fake = FakeCartesia()
    client = CartesiaVoiceClient(client=fake, language="en")
    assert client.clone_voice(VoiceSample(sample), "pitchme-user-1") == "voice-123"
    assert fake.calls == [("clone", "me.wav", sample.stat().st_size, "pitchme-user-1", "en")]


def test_cartesia_sends_emotion_and_speed(sample):
    fake = FakeCartesia()
    client = CartesiaVoiceClient(client=fake, model="sonic-3")
    assert client.synthesize("Hi", "v1", ProsodyParams("confident", 0.9)) == b"RIFF..."
    request = fake.calls[0][1]
    assert request["model_id"] == "sonic-3"
    assert request["voice"] == {"mode": "id", "id": "v1"}
    assert request["output_format"] == OUTPUT_FORMAT
    assert request["generation_config"] == {"speed": 0.9, "emotion": "confident"}
    client.synthesize("Hi", "v1", ProsodyParams())
    assert fake.calls[1][1]["generation_config"] == {"speed": 1.0}


def test_cartesia_errors_are_wrapped(sample, tmp_path):
    client = CartesiaVoiceClient(client=FakeCartesia(error=RuntimeError("402 plan")))
    with pytest.raises(VoiceCloneError, match="Cartesia clone failed: 402 plan"):
        client.clone_voice(VoiceSample(sample), "n")
    with pytest.raises(VoiceCloneError, match="Cartesia speech failed"):
        client.synthesize("Hi", "v1", ProsodyParams())
    with pytest.raises(VoiceCloneError, match="Could not read voice sample"):
        client.clone_voice(VoiceSample(tmp_path / "gone.wav"), "n")


def test_cartesia_delete():
    fake = FakeCartesia()
    CartesiaVoiceClient(client=fake).delete_voice("v9")
    assert fake.calls == [("delete", "v9")]


class FakeResemble:
    def __init__(self, statuses=("running", "finished"), projects=()):
        self.calls = []
        self.statuses = list(statuses)
        ok = {"success": True}
        v2 = SimpleNamespace(
            projects=SimpleNamespace(
                all=lambda page, size: {"items": list(projects)},
                create=lambda name, desc: (
                    self._log("project", name) or {**ok, "item": {"uuid": "p1"}}
                ),
            ),
            voices=SimpleNamespace(
                create=lambda **kw: self._log("voice", kw) or {**ok, "item": {"uuid": "rv1"}},
                build=lambda uuid: self._log("build", uuid) or ok,
                get=lambda uuid: {"item": {"status": self.statuses.pop(0)}},
                delete=lambda uuid: self._log("delete", uuid) or ok,
            ),
            recordings=SimpleNamespace(
                create=lambda *a: self._log("recording", a[0], a[3]) or ok,
            ),
            clips=SimpleNamespace(
                create_sync=lambda project, voice, text, **kw: (
                    self._log("clip", project, voice, text, kw)
                    or {**ok, "item": {"audio_src": "https://cdn/clip.wav"}}
                )
            ),
        )
        self.sdk = SimpleNamespace(v2=v2)

    def _log(self, *entry):
        self.calls.append(entry)


def test_resemble_clone_waits_for_training(sample):
    fake = FakeResemble()
    sleeps = []
    client = ResembleVoiceClient(sdk=fake.sdk, sleep=sleeps.append)
    voice = client.clone_voice(VoiceSample(sample, "hello there", "https://consent/1"), "me")
    assert voice == "rv1"
    assert [c[0] for c in fake.calls] == ["voice", "recording", "build"]
    assert fake.calls[1] == ("recording", "rv1", "hello there")
    assert len(sleeps) == 1


def test_resemble_needs_transcript_and_consent(sample):
    client = ResembleVoiceClient(sdk=FakeResemble().sdk)
    with pytest.raises(VoiceCloneError, match="transcript and a consent"):
        client.clone_voice(VoiceSample(sample), "me")


def test_resemble_failed_training(sample):
    client = ResembleVoiceClient(sdk=FakeResemble(statuses=["failed"]).sdk, sleep=lambda s: None)
    with pytest.raises(VoiceCloneError, match="stopped with status 'failed'"):
        client.clone_voice(VoiceSample(sample, "t", "https://c"), "me")


def test_resemble_speaks_through_one_project():
    fake = FakeResemble()
    client = ResembleVoiceClient(sdk=fake.sdk, fetch=lambda url: b"WAV:" + url.encode())
    assert client.synthesize("Hi", "rv1", ProsodyParams()) == b"WAV:https://cdn/clip.wav"
    client.synthesize("Again", "rv1", ProsodyParams())
    assert [c[0] for c in fake.calls] == ["project", "clip", "clip"]
    assert fake.calls[1][4] == {"sample_rate": 16_000, "output_format": "wav"}


def test_resemble_reuses_an_existing_project_and_deletes():
    fake = FakeResemble(projects=[{"name": "pitchme-playback", "uuid": "p0"}])
    client = ResembleVoiceClient(sdk=fake.sdk, fetch=lambda url: b"")
    client.synthesize("Hi", "rv1", ProsodyParams())
    client.delete_voice("rv1")
    assert fake.calls[0][1] == "p0"
    assert fake.calls[1] == ("delete", "rv1")


def test_factory_picks_and_checks_keys():
    with pytest.raises(VoiceCloneError, match="CARTESIA_API_KEY is not set"):
        make_voice_clone_client(_settings(cartesia_api_key=""))
    with pytest.raises(VoiceCloneError, match="RESEMBLE_API_KEY is not set"):
        make_voice_clone_client(_settings(voice_clone_provider="resemble", resemble_api_key=""))
    with pytest.raises(VoiceCloneError, match="Unknown VOICE_CLONE_PROVIDER 'elevenlabs'"):
        make_voice_clone_client(_settings(voice_clone_provider="elevenlabs"))
    client = make_voice_clone_client(_settings(cartesia_api_key="test-key-not-used"))
    assert isinstance(client, CartesiaVoiceClient)
    assert client.model == "sonic-3"
