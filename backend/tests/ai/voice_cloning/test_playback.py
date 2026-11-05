from ai.voice_cloning.answers import AnswerCorrection
from ai.voice_cloning.base import ProsodyParams
from ai.voice_cloning.playback import EDGE_PAUSE_MS, speak_answers, speak_script
from ai.voice_cloning.script import ScriptSegment
from ai.voice_cloning.wav import read_wav

from .fakes import FakeVoiceClient


def answer(text, unsupported=()):
    return AnswerCorrection("ex-0", "weak", "q", "a", text, "", "", tuple(unsupported))


def test_each_verified_answer_becomes_a_confident_clip():
    voice = FakeVoiceClient()
    out = speak_answers(
        [answer("Yes we are audited yearly"), answer("It is 25 dollars", ["25"])], "v1", voice
    )
    assert len(out) == 1
    assert out[0].duration_ms == 5 * 100 + EDGE_PAUSE_MS
    assert voice.spoken == [("Yes we are audited yearly", "v1", ProsodyParams("confident"))]
    assert voice.cloned == []  # the saved voice is reused, never re-cloned


def test_unverified_answers_on_request():
    voice = FakeVoiceClient()
    out = speak_answers([answer("It is 25 dollars", ["25"])], "v1", voice, include_unverified=True)
    assert len(out) == 1


def seg(i, original, corrected, prosody=ProsodyParams(), rejected=()):
    return ScriptSegment(i, original, corrected, "", (), prosody, rejected)


def test_script_is_one_wav_with_each_segments_delivery():
    voice = FakeVoiceClient()
    segments = [
        seg(0, "So um we grow", "We grow", ProsodyParams("calm", 0.9, 400)),
        seg(1, "like fast", "drifted away entirely", rejected=("too different",)),
        seg(2, "  ", "  "),
    ]
    audio = speak_script(segments, "v1", voice)
    assert read_wav(audio).duration_ms == 200 + 400 + 200
    assert [(text, p.emotion) for text, _, p in voice.spoken] == [
        ("We grow", "calm"),
        ("like fast", "neutral"),  # rejected rewrite falls back to the original
    ]
