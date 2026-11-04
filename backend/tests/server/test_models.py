from server.db import AnalysisStatus, Base, PracticeSession, SessionStatus, User


def test_tables_registered():
    assert set(Base.metadata.tables) == {"users", "practice_sessions"}


def test_user_stores_keys_not_urls():
    columns = set(User.__table__.columns.keys())
    assert {"voice_sample_key", "playbook_key", "voice_clone_id"} <= columns
    assert not any(name.endswith("_url") for name in columns)


def test_analysis_state_is_separate_from_result():
    columns = PracticeSession.__table__.columns
    assert columns["analysis_status"].type.enums == [s.value for s in AnalysisStatus]
    assert columns["analysis_data"].nullable


def test_session_status_enum_values():
    assert PracticeSession.__table__.columns["status"].type.enums == [
        "waiting",
        "active",
        "complete",
        "failed",
    ]
    assert SessionStatus("active") is SessionStatus.active


def test_session_cascades_from_user():
    (fk,) = PracticeSession.__table__.columns["user_id"].foreign_keys
    assert fk.ondelete == "CASCADE"
