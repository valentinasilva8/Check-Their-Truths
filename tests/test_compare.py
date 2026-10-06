"""Phase C tests: compare_statements -- all offline, model mocked."""

import json
from unittest.mock import MagicMock

import pytest

import compare as _compare_mod
from compare import _is_ai_topic, _normalize, _verify_quote, compare_statements
from sources import load_config, load_snapshot


# ---------------------------------------------------------------------------
# Fixture: clear cache before and after every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    _compare_mod._cache.clear()
    yield
    _compare_mod._cache.clear()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_model_response(rows: list) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = json.dumps(rows)
    return mock


# ---------------------------------------------------------------------------
# Normalization and quote verification
# ---------------------------------------------------------------------------

def test_normalize_curly_quotes():
    assert _normalize("‘Hello’ “world”") == "'Hello' \"world\""


def test_normalize_nbsp_and_whitespace():
    assert _normalize("one two  three") == "one two three"


def test_verify_quote_passes():
    paras = ["The United States and China agreed on a framework for bilateral dialogue."]
    assert _verify_quote("United States and China agreed on a framework", paras) is True


def test_verify_quote_too_short():
    paras = ["The two leaders agreed."]
    assert _verify_quote("two leaders agreed", paras) is False  # 3 words


def test_verify_quote_exactly_six_words():
    paras = ["The two leaders agreed to meet again soon."]
    assert _verify_quote("The two leaders agreed to meet", paras) is True


def test_verify_quote_not_substring():
    paras = ["The United States and China agreed."]
    assert _verify_quote("United States and China disagreed on terms", paras) is False


# ---------------------------------------------------------------------------
# _is_ai_topic
# ---------------------------------------------------------------------------

def test_is_ai_topic_empty():
    assert _is_ai_topic("") is True


def test_is_ai_topic_ai():
    assert _is_ai_topic("AI") is True


def test_is_ai_topic_artificial_intelligence():
    assert _is_ai_topic("Artificial Intelligence naming") is True


def test_is_ai_topic_super_intelligence():
    assert _is_ai_topic("super intelligence") is True


def test_is_ai_topic_unrelated():
    assert _is_ai_topic("coal trade") is False


# ---------------------------------------------------------------------------
# Quote verification failures
# ---------------------------------------------------------------------------

def test_compare_drops_bad_quote(monkeypatch):
    config = load_config()
    fake_rows = [{
        "topic": "AI",
        "label": "contradiction",
        "reason": "Different terms used.",
        "left_quote": "this phrase does not appear anywhere in any source paragraph at all",
        "right_quote": "this phrase also does not appear in any source paragraph whatsoever",
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "ai_bad_quote", "us", "china")
    assert result["dropped"] == 1  # one row dropped
    assert len(result["rows"]) == 1  # term_check row still present for ai topic
    assert result["rows"][0]["label"] == "term_check"
    # Each failed quote adds its own reason string; contradiction has two quotes, both fail
    assert len(result["drop_reasons"]) == 2


def test_compare_drops_short_quote(monkeypatch):
    config = load_config()
    snap = load_snapshot("washington_2026_09", "us_fact_sheet")
    assert snap, "us_fact_sheet snapshot missing"
    para = snap["paragraphs"][0]
    words = para.split()
    short_quote = " ".join(words[:5])  # 5 words -- IS a substring, but too short
    assert short_quote in para

    fake_rows = [{
        "topic": "test",
        "label": "only_us",
        "reason": "Only the US mentions this point.",
        "left_quote": short_quote,
        "right_quote": None,
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "test_short_q", "us", "china")
    assert result["dropped"] == 1
    dropped_non_term = [r for r in result["rows"] if r["label"] != "term_check"]
    assert len(dropped_non_term) == 0


def test_compare_keeps_valid_quote(monkeypatch):
    config = load_config()
    snap = load_snapshot("washington_2026_09", "us_fact_sheet")
    assert snap, "us_fact_sheet snapshot missing"
    para = snap["paragraphs"][0]
    words = para.split()
    valid_quote = " ".join(words[:6])  # 6 words -- passes
    assert len(valid_quote.split()) == 6

    fake_rows = [{
        "topic": "test",
        "label": "only_us",
        "reason": "Only the US mentions this specific point.",
        "left_quote": valid_quote,
        "right_quote": None,
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "test_valid_q", "us", "china")
    assert result["dropped"] == 0
    verified = [r for r in result["rows"] if r["label"] != "term_check"]
    assert len(verified) == 1


# ---------------------------------------------------------------------------
# Label validation
# ---------------------------------------------------------------------------

def test_compare_drops_invalid_label(monkeypatch):
    config = load_config()
    snap = load_snapshot("washington_2026_09", "us_fact_sheet")
    para = snap["paragraphs"][0]
    valid_quote = " ".join(para.split()[:6])

    fake_rows = [{
        "topic": "test",
        "label": "invented_label",
        "reason": "Some reason.",
        "left_quote": valid_quote,
        "right_quote": None,
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "test_bad_label", "us", "china")
    assert result["dropped"] >= 1
    assert any("label" in dr for dr in result["drop_reasons"])


def test_compare_drops_contradiction_missing_right_quote(monkeypatch):
    config = load_config()
    snap = load_snapshot("washington_2026_09", "us_fact_sheet")
    para = snap["paragraphs"][0]
    valid_quote = " ".join(para.split()[:6])

    fake_rows = [{
        "topic": "test",
        "label": "contradiction",
        "reason": "They contradict each other.",
        "left_quote": valid_quote,
        "right_quote": None,  # contradiction requires both
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "test_missing_rq", "us", "china")
    assert result["dropped"] >= 1
    assert any("contradiction" in dr for dr in result["drop_reasons"])


# ---------------------------------------------------------------------------
# Invalid JSON from model
# ---------------------------------------------------------------------------

def test_compare_invalid_json(monkeypatch):
    config = load_config()
    mock = MagicMock()
    mock.choices[0].message.content = "not valid json {{{"
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: mock)
    result = compare_statements(config, "washington_2026_09", "test_bad_json", "us", "china")
    assert "error" in result
    assert "JSON" in result["error"] or "json" in result["error"].lower()


# ---------------------------------------------------------------------------
# Wrong case type
# ---------------------------------------------------------------------------

def test_compare_wrong_case_type():
    config = load_config()
    result = compare_statements(config, "medicare_checks_2026_10", "premiums", "us", "china")
    assert "error" in result
    assert "meeting" in result["error"]


# ---------------------------------------------------------------------------
# Press side
# ---------------------------------------------------------------------------

def test_compare_press_not_yet_available():
    config = load_config()
    result = compare_statements(config, "washington_2026_09", "ai", "press", "china")
    assert "error" in result
    assert "not available yet" in result["error"]


# ---------------------------------------------------------------------------
# Chinese term check
# ---------------------------------------------------------------------------

def test_chinese_term_check_ai_topic(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response([]))
    result = compare_statements(config, "washington_2026_09", "ai", "us", "china")
    term_rows = [r for r in result["rows"] if r["label"] == "term_check"]
    assert len(term_rows) == 1
    assert "人工智能" in term_rows[0]["reason"]
    assert "超级智能" in term_rows[0]["reason"]


def test_chinese_term_check_artificial_intelligence_topic(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response([]))
    result = compare_statements(config, "washington_2026_09", "artificial intelligence", "us", "china")
    term_rows = [r for r in result["rows"] if r["label"] == "term_check"]
    assert len(term_rows) == 1


def test_chinese_term_check_empty_topic(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response([]))
    result = compare_statements(config, "washington_2026_09", "", "us", "china")
    term_rows = [r for r in result["rows"] if r["label"] == "term_check"]
    assert len(term_rows) == 1


def test_chinese_term_check_no_fire_for_unrelated_topic(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response([]))
    result = compare_statements(config, "washington_2026_09", "coal trade", "us", "china")
    term_rows = [r for r in result["rows"] if r["label"] == "term_check"]
    assert len(term_rows) == 0


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def test_compare_term_check_outside_cap(monkeypatch):
    """term_check row is appended after the 12-row cap; it does not consume a slot."""
    config = load_config()
    snap = load_snapshot("washington_2026_09", "us_fact_sheet")
    valid_quote = " ".join(snap["paragraphs"][0].split()[:6])

    # 13 valid rows -- exceeds MAX_ROWS=12
    fake_rows = [
        {
            "topic": f"topic_{i}",
            "label": "only_us",
            "reason": f"Only the US mentions topic number {i}.",
            "left_quote": valid_quote,
            "right_quote": None,
        }
        for i in range(13)
    ]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "ai", "us", "china")

    non_term = [r for r in result["rows"] if r["label"] != "term_check"]
    term_rows = [r for r in result["rows"] if r["label"] == "term_check"]

    assert result["cap_hit"] is True
    assert len(non_term) == 12  # capped at MAX_ROWS
    assert len(term_rows) == 1  # term_check appended after cap
    assert len(result["rows"]) == 13  # 12 regular + 1 term_check


def test_compare_cache_hit(monkeypatch):
    config = load_config()
    call_count = {"n": 0}

    snap = load_snapshot("washington_2026_09", "us_fact_sheet")
    valid_quote = " ".join(snap["paragraphs"][0].split()[:6])
    fake_rows = [{
        "topic": "cache test",
        "label": "only_us",
        "reason": "Only the US mentions this specific point.",
        "left_quote": valid_quote,
        "right_quote": None,
    }]

    def counting_completion(**kw):
        call_count["n"] += 1
        return _make_model_response(fake_rows)

    monkeypatch.setattr("compare.litellm.completion", counting_completion)

    compare_statements(config, "washington_2026_09", "cache_test_topic", "us", "china")
    compare_statements(config, "washington_2026_09", "cache_test_topic", "us", "china")
    assert call_count["n"] == 1
