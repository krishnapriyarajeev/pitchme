from ai.core.transcript import Segment, Transcript, Word
from ai.speech.articulation import (
    SEGMENT_CONFIDENCE_THRESHOLD,
    WORD_LOGPROB_THRESHOLD,
    ArticulationReport,
    score_articulation,
)

from .helpers import steady_words, transcript_of


def test_clear_words_raise_no_flags():
    report = score_articulation(transcript_of(steady_words(10, logprob=-0.05)))
    assert report.flags == ()
    assert report.words_checked == 10
    assert report.clarity_score == 1.0


def test_low_logprob_word_is_flagged():
    words = steady_words(10, logprob=-0.05)
    words[3] = Word("quarterly", words[3].start_ms, words[3].end_ms, -1.2)
    report = score_articulation(transcript_of(words))
    assert len(report.flags) == 1
    flag = report.flags[0]
    assert (flag.text, flag.source, flag.word_count, flag.logprob) == ("quarterly", "word", 1, -1.2)
    assert flag.t_start_ms == words[3].start_ms
    assert report.unclear_words == 1
    assert report.clarity_score == 0.9


def test_threshold_itself_is_clear():
    words = steady_words(2, logprob=WORD_LOGPROB_THRESHOLD)
    assert score_articulation(transcript_of(words)).flags == ()


def test_rushed_word_is_marked_as_a_rate_spike():
    calm = steady_words(10, logprob=-0.05)  # 150 wpm
    rushed = steady_words(30, every_ms=200, length_ms=150, logprob=-0.05)  # 300 wpm
    rushed[15] = Word("mumble", rushed[15].start_ms, rushed[15].end_ms, -2.0)
    calm[5] = Word("mumble", calm[5].start_ms, calm[5].end_ms, -2.0)
    assert score_articulation(transcript_of(rushed)).flags[0].co_occurring_rate_spike
    assert not score_articulation(transcript_of(calm)).flags[0].co_occurring_rate_spike


def test_segment_confidence_is_used_when_words_have_none():
    words = steady_words(20)  # no per-word logprob, as from Groq
    unsure = transcript_of(words, confidence=SEGMENT_CONFIDENCE_THRESHOLD - 0.3, per_segment=5)
    report = score_articulation(unsure)
    assert report.words_checked == 20
    assert len(report.flags) == 4
    assert {f.source for f in report.flags} == {"segment"}
    assert report.flags[0].word_count == 5
    assert report.clarity_score == 0.0

    sure = transcript_of(words, confidence=-0.2, per_segment=5)
    assert score_articulation(sure).flags == ()


def test_mixed_segments_only_flag_the_unsure_one():
    clear = Segment("we grow", 0, 700, tuple(steady_words(2)), confidence=-0.2)
    unsure_words = tuple(steady_words(3, start_ms=1_000))
    unsure = Segment("fast deal close", 1_000, 1_900, unsure_words, confidence=-1.1)
    report = score_articulation(Transcript(segments=(clear, unsure)))
    assert [f.text for f in report.flags] == ["fast deal close"]
    assert report.clarity_score == 0.4


def test_no_confidence_at_all_is_skipped_not_judged():
    report = score_articulation(transcript_of(steady_words(10)))
    assert report.words_checked == 0
    assert report.clarity_score == 1.0


def test_empty_report():
    assert ArticulationReport(flags=(), words_checked=0).unclear_words == 0
