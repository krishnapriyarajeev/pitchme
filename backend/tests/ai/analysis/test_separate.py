from ai.analysis.separate import BUYER, SELLER, buyer_words, separate_speakers
from ai.core.transcript import Segment, Transcript, Word
from ai.diarize.base import DiarizedSegment
from ai.diarize.filter_speaker import kept_ranges, original_time


def transcript(*spoken: str) -> Transcript:
    """One word every 400 ms, each segment one line of speech."""
    segments, t = [], 0
    for line in spoken:
        words = []
        for text in line.split():
            words.append(Word(text, t, t + 300))
            t += 400
        segments.append(Segment(line, words[0].start_ms, words[-1].end_ms, tuple(words)))
        t += 1000
    return Transcript(tuple(segments))


BUYER_LINES = [
    "Yes, who is this?",
    "We already use Staples for that, and frankly the price is the problem.",
]


def test_buyer_lines_are_found_in_the_recording():
    rec = transcript(
        "Yes who is this",
        "Hi Jo it's Sam from PitchMe",
        "We already use Staples for that and frankly the price is the problem",
        "Fair, so let me show you the numbers",
    )
    mask = buyer_words(rec, BUYER_LINES)
    sizes = [len(s.words) for s in rec.segments]
    expected = [True] * sizes[0] + [False] * sizes[1] + [True] * sizes[2] + [False] * sizes[3]
    assert mask == expected


def test_misheard_words_inside_a_buyer_line_stay_with_the_buyer():
    rec = transcript("We already use stables for that and frankly the price is the problem")
    assert all(buyer_words(rec, BUYER_LINES))


def test_a_common_word_alone_is_not_the_buyer():
    rec = transcript("yes we can do that")
    assert not any(buyer_words(rec, ["Yes."]))


def test_segments_alternate_and_cover_each_run():
    rec = transcript("Yes who is this", "Hi Jo it's Sam")
    segments = separate_speakers(rec, BUYER_LINES)
    assert [s.speaker for s in segments] == [BUYER, SELLER]
    assert segments[0] == DiarizedSegment(BUYER, 0, 1500)
    assert segments[1].start_ms == 2600


def test_no_buyer_lines_means_all_seller():
    rec = transcript("Just me talking here")
    assert [s.speaker for s in separate_speakers(rec, [])] == [SELLER]
    assert separate_speakers(Transcript(()), BUYER_LINES) == ()


def test_original_time_reverses_closing_up():
    ranges = kept_ranges((DiarizedSegment(BUYER, 1000, 3000),), SELLER, 5000)
    assert ranges == [(0, 1000), (3000, 5000)]
    assert [original_time(t, ranges) for t in (0, 999, 1000, 1500, 3000)] == [
        0,
        999,
        1000,
        3500,
        5000,
    ]
    assert original_time(9999, ranges) == 5000
    assert original_time(42, []) == 42
