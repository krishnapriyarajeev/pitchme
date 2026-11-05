import pytest

from ai.core.llm import LLMError
from ai.core.transcript import Segment, Transcript
from ai.core.types import Finding, Severity, TimestampedNote
from ai.voice_cloning.script import align_findings, check_rewrite, correct_script
from tests.ai.speech.helpers import FakeLLM

TALK = Transcript(
    segments=(
        Segment("So um our tool cuts churn by twenty percent.", 0, 4000),
        Segment("We, like, integrate with Salesforce.", 4500, 7000),
        Segment("Thanks for listening.", 7500, 9000),
    )
)

FINDINGS = (
    Finding(
        "speech", "frequent_fillers", Severity.MEDIUM, "Fillers.", TimestampedNote(0, 6000, "")
    ),
    Finding("voice", "high_jitter", Severity.MEDIUM, "Tense voice."),
    Finding("speech", "pace_too_fast", Severity.LOW, "Rushed.", TimestampedNote(7600, 7600, "")),
)


def segment(i, text, ids=(), emotion="neutral", speed=1.0, pause=0):
    return {
        "segment_index": i,
        "corrected_text": text,
        "change_description": "Removed fillers." if ids else "",
        "related_finding_ids": list(ids),
        "emotion": emotion,
        "speed": speed,
        "pause_after_ms": pause,
    }


def test_findings_land_on_overlapping_segments_or_are_global():
    aligned = align_findings(FINDINGS, TALK)
    assert [(a.id, a.segment_indices) for a in aligned] == [
        ("speech-0", (0, 1)),
        ("voice-1", ()),
        ("speech-2", (2,)),  # a zero-length note still finds its segment
    ]


def test_rewrite_keeps_good_edits_and_rejects_drift():
    llm = FakeLLM(
        {
            "segments": [
                segment(
                    0,
                    "Our tool cuts churn by twenty percent.",
                    ["speech-0", "voice-1"],
                    "calm",
                    0.9,
                    300,
                ),
                segment(
                    1,
                    "Our platform offers comprehensive enterprise integrations everywhere.",
                    ["speech-0"],
                ),
                # Segment 2 skipped by the model.
            ]
        }
    )
    first, second, third = correct_script(TALK, FINDINGS, llm)
    assert first.changed and not first.rejected_because
    assert first.text_to_speak == "Our tool cuts churn by twenty percent."
    assert first.related_finding_ids == ("speech-0", "voice-1")
    assert (first.prosody.emotion, first.prosody.speed, first.prosody.pause_after_ms) == (
        "calm",
        0.9,
        300,
    )
    assert second.rejected_because
    assert second.text_to_speak == "We, like, integrate with Salesforce."
    assert not third.changed
    assert third.prosody.emotion == "neutral"


def test_prompt_marks_global_findings():
    llm = FakeLLM({"segments": []})
    correct_script(TALK, FINDINGS, llm)
    prompt = llm.prompts[0]
    assert "[1] We, like, integrate with Salesforce." in prompt
    assert "id=voice-1 segment_index=-1 voice/high_jitter: Tense voice." in prompt


def test_unknown_finding_ids_and_bad_cues_are_cleaned():
    llm = FakeLLM({"segments": [segment(2, "Thanks for listening.", ["made-up"], "ecstatic", 3.0)]})
    last = correct_script(TALK, FINDINGS, llm)[2]
    assert last.related_finding_ids == ()
    assert (last.prosody.emotion, last.prosody.speed) == ("neutral", 1.5)


@pytest.mark.parametrize(
    ("corrected", "reason"),
    [
        ("Our tool cuts churn by twenty percent.", None),
        ("Churn.", "length changed"),
        ("Our tool cuts churn by thirty percent.", "adds numbers not in the original: 30"),
        ("Completely different sentence about pricing tiers and plans.", "wording similarity"),
    ],
)
def test_check_rewrite(corrected, reason):
    reasons = check_rewrite("So um our tool cuts churn by twenty percent.", corrected)
    if reason is None:
        assert reasons == ()
    else:
        assert any(reason in r for r in reasons)


def test_empty_transcript_and_malformed_reply():
    llm = FakeLLM({"segments": []})
    assert correct_script(Transcript(segments=()), FINDINGS, llm) == ()
    assert llm.prompts == []
    with pytest.raises(LLMError, match="did not match"):
        correct_script(TALK, FINDINGS, FakeLLM({"segments": [{"segment_index": "x"}]}))
