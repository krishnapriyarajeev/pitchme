from ai.analysis.scoring import (
    CLEAN,
    WEIGHTS,
    DimensionScore,
    content_score,
    from_findings,
    overall,
    skipped,
)
from ai.core.types import Finding, Severity


def finding(severity, summary="x"):
    return Finding("speech", "pace", severity, summary)


def test_findings_cost_points_by_severity():
    dim = from_findings(
        "speech",
        [finding(Severity.LOW, "a bit fast"), finding(Severity.HIGH, "rushed the price"),
         finding(Severity.INFO)],
    )  # fmt: skip
    assert dim.score == 100 - 5 - 20
    assert dim.summary == "rushed the price"
    assert dim.label == "Speech"


def test_clean_dimension_scores_full_marks():
    dim = from_findings("voice", [finding(Severity.INFO, "noted")])
    assert (dim.score, dim.summary) == (100, CLEAN["voice"])


def test_score_never_goes_below_zero():
    assert from_findings("vision", [finding(Severity.HIGH)] * 9).score == 0


def test_content_uses_the_judges_score():
    assert content_score(140, "great").score == 100
    dim = content_score(None, "The buyer asked nothing.")
    assert dim.score is None and dim.skipped == "The buyer asked nothing."


def test_overall_is_the_weighted_mean():
    dims = [
        DimensionScore("content", "Content", 80, ""),
        DimensionScore("speech", "Speech", 60, ""),
        DimensionScore("voice", "Voice", 100, ""),
        DimensionScore("vision", "Body language", 50, ""),
    ]
    assert sum(WEIGHTS.values()) == 1
    assert overall(dims) == round(0.5 * 80 + 0.15 * 60 + 0.15 * 100 + 0.2 * 50)


def test_skipped_dimensions_share_their_weight():
    dims = [DimensionScore("content", "Content", 80, ""), skipped("vision", "No video.")]
    assert overall(dims) == 80
    assert overall([skipped("content", "nothing")]) is None


def test_to_dict():
    assert skipped("vision", "No video.").to_dict() == {
        "name": "vision", "label": "Body language", "score": None,
        "summary": "No video.", "skipped": "No video.",
    }  # fmt: skip
