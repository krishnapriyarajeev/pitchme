from ai.core.transcript import Word
from ai.core.types import Severity
from ai.speech import score_speech
from ai.speech.report import QUOTE_MAX_WORDS, quote_between

from .helpers import FakeLLM, steady_words, transcript_of


def _categories(report):
    return [f.category for f in report.findings]


def test_calm_clear_talk_has_no_findings():
    words = steady_words(150, logprob=-0.05)
    report = score_speech(transcript_of(words), FakeLLM())
    assert report.findings == ()
    assert report.fluency.wpm_mean > 140
    assert report.articulation.clarity_score == 1.0


def test_rushed_stretch_is_one_finding_not_one_per_window():
    calm = steady_words(75)  # 0-30 s at 150 wpm
    rushed = steady_words(150, every_ms=200, length_ms=150, start_ms=30_000)  # 300 wpm
    report = score_speech(transcript_of(calm + rushed), FakeLLM())
    pace = [f for f in report.findings if f.category == "pace_too_fast"]
    assert len(pace) == 1
    finding = pace[0]
    assert finding.severity is Severity.MEDIUM
    assert finding.details["windows"] > 1
    assert finding.note.t_end_ms > finding.note.t_start_ms
    assert finding.note.quote.startswith("word")


def test_slightly_slow_pace_is_low_severity():
    words = steady_words(50, every_ms=600)  # 100 wpm
    report = score_speech(transcript_of(words), FakeLLM())
    assert _categories(report) == ["pace_too_slow"]
    assert report.findings[0].severity is Severity.LOW


def test_frequent_fillers():
    words = steady_words(150, text="um")
    llm = FakeLLM({"fillers": [{"word": "um", "count": 20}], "summary": "Says um."})
    report = score_speech(transcript_of(words), llm)
    finding = next(f for f in report.findings if f.category == "frequent_fillers")
    assert finding.details["filler_counts"] == {"um": 20}
    assert "'um' (20 times)" in finding.summary


def test_a_few_fillers_are_not_reported():
    words = steady_words(150, text="um")
    llm = FakeLLM({"fillers": [{"word": "um", "count": 3}], "summary": "s"})
    assert "frequent_fillers" not in _categories(score_speech(transcript_of(words), llm))


def _with_gaps(texts_and_gaps):
    words, t = [], 0
    for text, gap in texts_and_gaps:
        words.append(Word(text, t, t + 300))
        t += 300 + gap
    return words


def test_run_of_hesitations_is_reported_with_its_quote():
    words = _with_gaps(
        [("So", 100), ("the", 900), ("main", 900), ("thing", 900), ("is", 100), ("price.", 100)]
    )
    report = score_speech(transcript_of(words), FakeLLM())
    finding = next(f for f in report.findings if f.category == "hesitation_run")
    assert finding.details["pause_count"] == 3
    assert finding.details["total_pause_ms"] == 2_700
    assert finding.note.quote == "the main thing is"


def test_rhetorical_pause_breaks_a_run():
    words = _with_gaps(
        [("the", 900), ("main", 900), ("point.", 900), ("Then", 900), ("we", 100), ("go", 100)]
    )
    report = score_speech(transcript_of(words), FakeLLM())
    assert "hesitation_run" not in _categories(report)


def test_unclear_while_rushing_suggests_slowing_down():
    words = steady_words(150, every_ms=400, logprob=-0.05)
    for i in range(0, 150, 5):
        words[i] = Word("mumble", words[i].start_ms, words[i].end_ms, -1.5)
    rushed = steady_words(40, every_ms=150, length_ms=100, logprob=-2.0, start_ms=70_000)
    report = score_speech(transcript_of(words + rushed), FakeLLM())
    finding = next(f for f in report.findings if f.category == "unclear_articulation")
    assert finding.details["unclear_words"] == 70
    assert finding.note.quote == "word"
    assert len(finding.details["examples"]) == 5
    assert "slowing down" in finding.summary


def test_findings_are_most_severe_first():
    words = steady_words(50, every_ms=600, text="um")  # slow: low
    llm = FakeLLM({"fillers": [{"word": "um", "count": 30}], "summary": "s"})
    report = score_speech(transcript_of(words), llm)
    severities = [f.severity.rank for f in report.findings]
    assert severities == sorted(severities, reverse=True)
    assert _categories(report) == ["frequent_fillers", "pace_too_slow"]


def test_quote_is_cut_to_the_limit():
    words = tuple(steady_words(40))
    quote = quote_between(words, 0, 100_000)
    assert quote.endswith("...")
    assert len(quote.split()) == QUOTE_MAX_WORDS + 1


def test_findings_serialise():
    words = steady_words(50, every_ms=600)
    finding = score_speech(transcript_of(words), FakeLLM()).findings[0]
    data = finding.to_dict()
    assert data["pipeline"] == "speech"
    assert data["note"]["quote"]
