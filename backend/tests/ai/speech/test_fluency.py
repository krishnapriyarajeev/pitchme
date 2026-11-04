import pytest

from ai.core.llm import LLMError
from ai.core.transcript import Word
from ai.speech.fluency import (
    MIN_WINDOW_MS,
    FillerCount,
    count_fillers,
    find_pauses,
    rolling_wpm,
    score_fluency,
)
from ai.speech.prompts.fillers import SYSTEM_PROMPT

from .helpers import FakeLLM, steady_words, transcript_of


def test_steady_speech_is_150_wpm_in_every_window():
    words = steady_words(150)  # 60 seconds at one word per 400 ms
    windows = rolling_wpm(tuple(words), 60_000)
    assert windows[0].t_start_ms == 0
    assert windows[0].t_end_ms == 15_000
    # A 15 s window holds 37 or 38 words at this spacing.
    assert all(w.wpm == pytest.approx(150, abs=6) for w in windows)


def test_short_tail_window_is_dropped():
    words = steady_words(50)  # 20 seconds
    windows = rolling_wpm(tuple(words), 20_000)
    assert all(w.t_end_ms - w.t_start_ms >= MIN_WINDOW_MS for w in windows)
    assert windows[-1].t_end_ms == 20_000


def test_a_short_talk_still_gets_one_window():
    words = steady_words(5)  # 2 seconds
    windows = rolling_wpm(tuple(words), 2_000)
    assert len(windows) == 1
    assert windows[0].wpm == 150.0


def test_no_words_no_windows():
    assert rolling_wpm((), 0) == ()


def test_pause_after_punctuation_is_rhetorical_and_mid_clause_is_hesitation():
    words = (
        Word("Hello.", 0, 300),
        Word("We", 1_000, 1_200),  # 700 ms after a full stop
        Word("build", 1_300, 1_500),  # 100 ms, not a pause
        Word("tools", 2_200, 2_500),  # 700 ms mid clause
    )
    pauses = find_pauses(words)
    assert [(p.start_ms, p.end_ms, p.is_hesitation) for p in pauses] == [
        (300, 1_000, False),
        (1_500, 2_200, True),
    ]
    assert pauses[1].duration_ms == 700


def _talk(text: str):
    words = [Word(token, i * 400, i * 400 + 300) for i, token in enumerate(text.split())]
    return transcript_of(words)


def test_fillers_are_sorted_and_lower_cased():
    llm = FakeLLM(
        {
            "fillers": [{"word": "Um", "count": 1}, {"word": "you know", "count": 2}],
            "summary": " Leans on 'you know'. ",
        }
    )
    talk = _talk("Um, the plan, you know, works. You know it does.")
    fillers, summary = count_fillers(talk, llm)
    assert fillers == (FillerCount("you know", 2), FillerCount("um", 1))
    assert summary == "Leans on 'you know'."


def test_model_cannot_count_more_than_was_said():
    llm = FakeLLM(
        {
            "fillers": [
                {"word": "like", "count": 9},
                {"word": "basically", "count": 3},  # never said
            ],
            "summary": "s",
        }
    )
    fillers, _ = count_fillers(_talk("It is, like, really like good"), llm)
    assert fillers == (FillerCount("like", 2),)


def test_word_inside_another_word_is_not_counted():
    llm = FakeLLM({"fillers": [{"word": "so", "count": 1}], "summary": "s"})
    fillers, _ = count_fillers(_talk("Also some solid points"), llm)
    assert fillers == ()


def test_prompt_carries_the_transcript_and_system_prompt():
    llm = FakeLLM()
    count_fillers(_talk("hello there"), llm)
    assert llm.prompts == ["TRANSCRIPT:\nhello there"]
    assert "verbal crutch" in SYSTEM_PROMPT


def test_empty_transcript_skips_the_model():
    llm = FakeLLM()
    assert count_fillers(transcript_of([]), llm) == ((), "No speech to check for fillers.")
    assert llm.prompts == []


@pytest.mark.parametrize(
    "reply",
    [
        {"summary": "missing fillers"},
        {"fillers": [{"word": "um"}], "summary": "no count"},
        {"fillers": [{"word": "um", "count": -1}], "summary": "negative"},
    ],
)
def test_malformed_reply_raises(reply):
    with pytest.raises(LLMError, match="did not match"):
        count_fillers(_talk("um hello"), FakeLLM(reply))


def test_score_fluency_combines_rate_pauses_and_fillers():
    words = steady_words(150, text="um")
    llm = FakeLLM({"fillers": [{"word": "um", "count": 30}], "summary": "Says um."})
    report = score_fluency(transcript_of(words), llm)
    assert report.wpm_mean == pytest.approx(150, abs=3)
    assert report.wpm_p95 == pytest.approx(150, abs=6)
    assert report.pauses == ()
    assert report.filler_total == 30
    # 30 fillers over 59.9 seconds of speech
    assert report.filler_per_min == 30.1
    assert report.filler_summary == "Says um."
    assert report.hesitation_pauses == ()
    assert report.rhetorical_pauses == ()


def test_score_fluency_on_silence():
    report = score_fluency(transcript_of([]), FakeLLM())
    assert report.wpm_mean == 0.0
    assert report.wpm_p95 == 0.0
    assert report.filler_per_min == 0.0
