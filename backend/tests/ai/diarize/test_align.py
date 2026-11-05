from ai.core.transcript import Segment, Transcript, Word
from ai.diarize.align import MAX_GAP_MS, speaker_at, tag_speakers
from ai.diarize.base import DiarizedSegment as D


def transcript(*words: tuple[str, int, int]) -> Transcript:
    ws = tuple(Word(t, s, e) for t, s, e in words)
    return Transcript(
        segments=(Segment(" ".join(w.text for w in ws), ws[0].start_ms, ws[-1].end_ms, ws),)
    )


SEGMENTS = (D("A", 0, 2000), D("B", 2000, 4000))


def test_each_word_takes_the_speaker_at_its_midpoint():
    # "so" starts in A's segment but its midpoint is in B's.
    tagged = tag_speakers(
        transcript(("we", 100, 400), ("ship", 500, 900), ("so", 1900, 2300), ("why", 2500, 2900)),
        SEGMENTS,
    )
    assert [(w.text, w.speaker) for w in tagged.words] == [
        ("we", "A"),
        ("ship", "A"),
        ("so", "B"),
        ("why", "B"),
    ]
    assert tagged.speakers == ("A", "B")
    assert [w.index for w in tagged.words] == [0, 1, 2, 3]


def test_shortest_overlapping_segment_wins():
    segments = (D("A", 0, 10_000), D("B", 3000, 3600))
    assert speaker_at(3300, segments) == "B"
    assert speaker_at(5000, segments) == "A"


def test_small_gap_takes_the_nearest_segment():
    segments = (D("A", 0, 1000), D("B", 5000, 6000))
    assert speaker_at(1400, segments) == "A"
    assert speaker_at(4700, segments) == "B"
    assert speaker_at(1000 + MAX_GAP_MS + 1, segments) is None
    assert speaker_at(100, ()) is None


def test_turns_group_runs_and_absorb_unassigned_words():
    segments = (D("A", 0, 1000), D("B", 4000, 6000))
    tagged = tag_speakers(
        transcript(
            ("hi", 0, 300),
            ("there", 400, 700),
            ("um", 2500, 2700),  # in a long gap: unassigned
            ("price", 4100, 4500),
            ("ok", 4600, 4900),
        ),
        segments,
    )
    assert tagged.words[2].speaker is None
    turns = tagged.turns()
    assert [(t.speaker, t.text) for t in turns] == [("A", "hi there um"), ("B", "price ok")]
    assert (turns[1].start_ms, turns[1].end_ms) == (4100, 4900)


def test_leading_unassigned_words_form_their_own_turn():
    tagged = tag_speakers(transcript(("so", 0, 200), ("yes", 5000, 5200)), (D("B", 5000, 6000),))
    assert [(t.speaker, t.text) for t in tagged.turns()] == [(None, "so"), ("B", "yes")]
