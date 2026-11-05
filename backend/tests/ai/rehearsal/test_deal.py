import json

import pytest

from ai.rehearsal.deal import STAGES, CallSetup, Deal, InvalidSetup, normalize


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Discovery", "discovery"),
        ("Cold call", "cold_call"),
        ("cold-call", "cold_call"),
        ("COLD_CALL", "cold_call"),
        ("Close", "closing"),
        ("Proposal", "proposal"),
        ("Renewal", "renewal"),
    ],
)
def test_stage_labels_from_the_app(value, expected):
    assert normalize(value, STAGES, "deal stage") == expected


def test_unknown_value_names_the_choices():
    with pytest.raises(ValueError, match="expected one of cold_call, discovery"):
        normalize("Lunch", STAGES, "deal stage")


def test_deal_normalizes_its_choices():
    deal = Deal(
        "Jo Bennett",
        "Saber",
        deal_stage="Negotiation",
        buyer_composure="Direct - low patience for fluff",
        audience_type="VP Sales",
    )
    assert (deal.deal_stage, deal.buyer_composure, deal.audience_type) == (
        "negotiation",
        "direct",
        "vp_sales",
    )


def test_deal_defaults():
    deal = Deal("Jo", "Saber", audience_type="")
    assert (deal.deal_stage, deal.audience_type, deal.buyer_composure) == (
        "discovery",
        "general",
        None,
    )


def test_setup_round_trips_through_room_metadata():
    setup = CallSetup("s-1", "user-1", Deal("Jo", "Saber", product="Payroll software"))
    assert CallSetup.from_metadata(setup.to_metadata()) == setup


def test_unknown_deal_keys_are_ignored():
    raw = json.loads(CallSetup("s-1", "user-1", Deal("Jo", "Saber")).to_metadata())
    raw["deal"]["added_later"] = "x"
    assert CallSetup.from_metadata(json.dumps(raw)).deal == Deal("Jo", "Saber")


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        "[]",
        '{"kind": "other"}',
        '{"kind": "pitchme.rehearsal", "version": 2}',
        '{"kind": "pitchme.rehearsal", "version": 1, "session_id": "s"}',
        '{"kind": "pitchme.rehearsal", "version": 1, "session_id": "s", "seller_identity": "u",'
        ' "deal": {"prospect_name": "Jo", "company": "S", "deal_stage": "lunch"}}',
    ],
)
def test_bad_metadata_is_rejected(raw):
    with pytest.raises(InvalidSetup):
        CallSetup.from_metadata(raw)
