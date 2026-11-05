"""The analysis pipeline on real Groq, judging a short call transcript with
a playbook. No recording, so no speech or video work. Runs with
make test-live."""

import pytest

from ai.analysis.pipeline import AnalysisRequest, run_analysis
from ai.config import AISettings
from ai.content.reference import ReferenceDocument, ReferenceSection
from ai.rehearsal.transcript import CallTurn

pytestmark = pytest.mark.live

TURNS = (
    CallTurn("buyer", "Thanks for calling. So what does this cost per seat?", 0, 3000),
    CallTurn("seller", "Um, it really depends, we can talk pricing later.", 3500, 7000),
    CallTurn("buyer", "Are you SOC 2 certified? Our security team will ask.", 7500, 10000),
    CallTurn("seller", "Yes, we have SOC 2 Type II and we renew it every year.", 10500, 14000),
)
PLAYBOOK = ReferenceDocument(
    (
        ReferenceSection(0, "Pricing", "Team plan: 40 dollars per seat per month."),
        ReferenceSection(1, "Security", "SOC 2 Type II, audited every year."),
    )
)


def test_dodged_price_is_flagged_and_rewritten():
    if not AISettings().groq_api_key.get_secret_value():
        pytest.skip("GROQ_API_KEY is not set")
    result = run_analysis(
        AnalysisRequest(TURNS, reference=PLAYBOOK),
        save_audio=lambda i, b: pytest.fail("no voice clone, nothing to save"),
        save_video=lambda p: pytest.fail("no video"),
    )
    print(result.to_dict())
    content = result.dimensions[0]
    assert content.name == "content" and content.score is not None
    assert result.questions == 2 and result.handled >= 1
    assert result.overall_score == content.score  # nothing else could be scored
    assert result.prep_list
    assert any("40" in a.stronger for a in result.corrected_answers)
    assert result.notes[0].startswith("This call was not recorded")
