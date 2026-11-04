import pytest

from ai.core import LLMClient, LLMError, parse_json_object


def test_parses_plain_object():
    assert parse_json_object('{"score": 3}', "Test") == {"score": 3}


def test_strips_a_json_fence():
    assert parse_json_object('```json\n{"ok": true}\n```', "Test") == {"ok": True}
    assert parse_json_object('```\n{"ok": true}\n```', "Test") == {"ok": True}


@pytest.mark.parametrize("reply", [None, "", "   "])
def test_empty_reply(reply):
    with pytest.raises(LLMError, match="Test returned an empty response"):
        parse_json_object(reply, "Test")


def test_invalid_json():
    with pytest.raises(LLMError, match="did not return valid JSON"):
        parse_json_object("{not json", "Test")


def test_rejects_non_object():
    with pytest.raises(LLMError, match="expected an object"):
        parse_json_object("[1, 2]", "Test")


def test_client_is_abstract():
    with pytest.raises(TypeError):
        LLMClient()
