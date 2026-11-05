import pytest

from ai.rehearsal.deal import AUDIENCES, COMPOSURES, STAGES, Deal
from ai.rehearsal.prompts import buyer


def test_every_choice_has_a_persona():
    assert set(buyer.AUDIENCES) == set(AUDIENCES)
    assert set(buyer.STAGES) == set(STAGES)
    assert set(buyer.COMPOSURES) == set(COMPOSURES)


@pytest.mark.parametrize("stage", STAGES)
def test_each_stage_has_its_own_situation(stage):
    prompt = buyer.build_system_prompt(Deal("Jo", "Saber", deal_stage=stage))
    assert buyer.STAGES[stage].situation in prompt


def test_prompt_carries_the_deal():
    deal = Deal(
        "Jo Bennett",
        "Saber Industries",
        deal_stage="renewal",
        industry="Office supplies",
        buyer_composure="analytical",
        competitors="Staples",
        audience_type="procurement",
        product="Payroll software for small teams",
        seller_role="Account Executive",
    )
    prompt = buyer.build_system_prompt(deal)
    assert prompt.startswith("You are Jo Bennett, Head of Procurement at Saber Industries.")
    for text in (
        "Industry: Office supplies",
        "Alternatives you know of and may mention: Staples",
        buyer.COMPOSURES["analytical"],
        "The seller (Account Executive) sells: Payroll software for small teams",
        "existing customer",
    ):
        assert text in prompt


def test_minimal_deal_has_no_empty_sections():
    prompt = buyer.build_system_prompt(Deal("Jo", "Saber"))
    assert "Industry" not in prompt
    assert "What is being sold" not in prompt
    assert buyer.COMPOSURES[buyer.DEFAULT_COMPOSURE] in prompt


def test_opening_follows_the_stage():
    line = buyer.opening_instruction(Deal("Jo", "Saber", deal_stage="cold_call"))
    assert "Yes, who is this?" in line
