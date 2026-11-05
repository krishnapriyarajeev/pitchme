from ai.core.transcript import Word
from ai.speech import score_articulation, score_fluency, summarize_articulation, summarize_fluency

from .helpers import FakeLLM, steady_words, transcript_of


def _fluency(words, summary="No fillers."):
    return score_fluency(transcript_of(words), FakeLLM({"fillers": [], "summary": summary}))


def test_fluency_summary_names_the_pace_and_keeps_the_model_sentence():
    text = summarize_fluency(_fluency(steady_words(150), "You barely used fillers."))
    assert text.startswith("You averaged 15")
    assert "a comfortable pace" in text
    assert text.endswith("You barely used fillers.")


def test_fluency_summary_fast_slow_and_hesitations():
    assert "faster than" in summarize_fluency(_fluency(steady_words(200, every_ms=200)))
    slow = [Word("we", 0, 300), Word("can", 1_300, 1_600), Word("ship", 2_600, 2_900)]
    text = summarize_fluency(_fluency(slow))
    assert "slower than" in text
    assert "hesitated mid-sentence 2 times" in text
    one = [Word("we", 0, 300), Word("ship", 1_300, 1_600)]
    assert "1 time." in summarize_fluency(_fluency(one))


def test_fluency_summary_on_silence_is_the_model_sentence():
    assert summarize_fluency(_fluency([], "x")) == "No speech to check for fillers."


def test_articulation_summaries():
    clear = score_articulation(transcript_of(steady_words(10, logprob=-0.1)))
    assert summarize_articulation(clear).endswith("every word was clear.")

    words = steady_words(20, logprob=-0.1)
    words[0] = Word("x", 0, 300, -2.0)
    mostly = score_articulation(transcript_of(words))
    assert summarize_articulation(mostly).endswith("articulation was clear overall.")

    unclear = score_articulation(transcript_of(steady_words(10, logprob=-2.0)))
    assert "hard to make out" in summarize_articulation(unclear)

    unscored = score_articulation(transcript_of(steady_words(10)))
    assert summarize_articulation(unscored).startswith("No confidence scores")
