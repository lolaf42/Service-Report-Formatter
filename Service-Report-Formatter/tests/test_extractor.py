from extractor import parse_response


def test_parse_response_with_fences():
    raw = "```json\n{\"entries\": [], \"open_questions\": []}\n```"
    parsed = parse_response(raw)
    assert isinstance(parsed, dict)
    assert "entries" in parsed


def test_parse_response_malformed_returns_raw():
    raw = "some text not json { invalid }"
    parsed = parse_response(raw)
    assert parsed.get("_raw") == raw
