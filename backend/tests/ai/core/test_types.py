from ai.core import Finding, Severity, TimestampedNote


def test_severity_rank_orders_findings():
    findings = [
        Finding("speech", "pace", Severity.LOW, "A little fast"),
        Finding("content", "inaccurate", Severity.HIGH, "Wrong ARR"),
        Finding("voice", "pitch", Severity.INFO, "Steady"),
    ]
    ordered = sorted(findings, key=lambda f: -f.severity.rank)
    assert [f.severity for f in ordered] == [Severity.HIGH, Severity.LOW, Severity.INFO]


def test_severity_is_a_string():
    assert Severity("medium") is Severity.MEDIUM
    assert f"{Severity.HIGH}" == "high"


def test_to_dict_is_json_ready():
    finding = Finding(
        pipeline="speech",
        category="filler",
        severity=Severity.MEDIUM,
        summary="Five fillers in ten seconds",
        note=TimestampedNote(t_start_ms=1000, t_end_ms=11000, quote="um so like"),
        details={"count": 5},
    )
    assert finding.to_dict() == {
        "pipeline": "speech",
        "category": "filler",
        "severity": "medium",
        "summary": "Five fillers in ten seconds",
        "note": {"t_start_ms": 1000, "t_end_ms": 11000, "quote": "um so like"},
        "details": {"count": 5},
    }


def test_to_dict_without_note():
    assert Finding("vision", "eye_contact", Severity.LOW, "Looked away").to_dict()["note"] is None
