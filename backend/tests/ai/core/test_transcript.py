from ai.core import Segment, Transcript, Word


def _transcript() -> Transcript:
    return Transcript(
        segments=(
            Segment(
                text="Thanks for the time.",
                start_ms=0,
                end_ms=1200,
                words=(Word("Thanks", 0, 400), Word("for", 400, 600), Word("the", 600, 700)),
            ),
            Segment(
                text="Let me explain.",
                start_ms=1500,
                end_ms=2600,
                words=(Word("Let", 1500, 1700, logprob=-0.1),),
                confidence=-0.2,
            ),
        )
    )


def test_words_flatten_in_order():
    assert [w.text for w in _transcript().words] == ["Thanks", "for", "the", "Let"]


def test_text_and_duration():
    transcript = _transcript()
    assert transcript.text == "Thanks for the time. Let me explain."
    assert transcript.duration_ms == 2600
    assert not transcript.is_empty


def test_empty_transcript():
    transcript = Transcript(segments=())
    assert transcript.text == ""
    assert transcript.duration_ms == 0
    assert transcript.words == ()
    assert transcript.is_empty
