"""Phase C tests: compare_statements -- all offline, model mocked."""

import json
from unittest.mock import MagicMock

import pytest

import compare as _compare_mod
import press as _press_mod
from compare import _is_ai_topic, _normalize, _verify_quote, compare_statements
from sources import load_config, load_snapshot


# ---------------------------------------------------------------------------
# Fixture: clear cache before and after every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    _compare_mod._cache.clear()
    _press_mod._cache.clear()
    yield
    _compare_mod._cache.clear()
    _press_mod._cache.clear()


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


def test_verify_quote_longer_than_80_chars():
    """A valid quote longer than 80 chars passes verification on its full text.

    The drop_reason message appends right_quote[:80] for display, but _verify_quote
    always receives the full string. This test confirms that: a quote > 80 chars that
    IS a verbatim substring of the paragraph passes without truncation.
    """
    snap = load_snapshot("washington_2026_09", "china_mfa_english")
    assert snap, "china_mfa_english snapshot missing"
    long_para = next((p for p in snap["paragraphs"] if len(p) > 90), None)
    assert long_para is not None, "Expected at least one China MFA paragraph > 90 chars"

    # Take a 85-char interior slice so the quote does not start at position 0
    # (ensures the first 80 chars alone is not trivially the full match).
    quote = long_para[5:90]  # 85 chars, starting mid-paragraph
    assert len(quote) > 80
    assert len(quote.split()) >= 6
    assert quote in long_para, "Test setup error: slice must be a substring"

    assert _verify_quote(quote, [long_para]) is True


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

def _invented_press() -> dict:
    """Press payload with invented sentences. Not from any published article."""
    river = (
        "The council agreed that the river project would start next spring without delay."
    )
    bridge = (
        "A spokesperson said the bridge plan was postponed until the following year entirely."
    )
    return {
        "case_id": "washington_2026_09",
        "side": "press",
        "articles": [
            {
                "article_id": "example/river-plan",
                "headline": "Council sets the river schedule",
                "byline": "Ada Example",
                "url": "https://example.test/river",
                "published": "2026-01-01T00:00:00Z",
                "paragraphs": [
                    {"id": "A1-P1", "text": river},
                    {"id": "A1-P2", "text": bridge},
                ],
            }
        ],
    }


def test_compare_press_unavailable(monkeypatch):
    config = load_config()
    monkeypatch.setattr(
        "compare.get_press_coverage",
        lambda config, case_id: {"error": "press side unavailable"},
    )
    result = compare_statements(config, "washington_2026_09", "ai", "us", "press")
    assert result["error"] == "press side unavailable"


def test_compare_press_span_must_be_in_named_paragraph(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: _invented_press())
    bridge = _invented_press()["articles"][0]["paragraphs"][1]["text"]
    fake_rows = [{
        "topic": "bridge",
        "label": "only_press",
        "reason": "Only the press mentions the bridge plan.",
        "left_quote": None,
        "right_quote": bridge,
        "left_paragraph_id": None,
        "right_paragraph_id": "A1-P1",
        "attributed_to": "Ada Example",
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "bridge", "us", "press")
    assert "error" not in result
    assert result["dropped"] == 1
    assert result["rows"] == []
    assert any("A1-P1" in reason for reason in result["drop_reasons"])


def test_compare_press_keeps_span_and_citation_fields(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: _invented_press())
    river = "The council agreed that the river project would start next spring"
    fake_rows = [{
        "topic": "river",
        "label": "only_press",
        "reason": "Only the press mentions the river project.",
        "left_quote": None,
        "right_quote": river,
        "left_paragraph_id": None,
        "right_paragraph_id": "A1-P1",
        "attributed_to": "Ada Example",
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "river", "us", "press")
    assert result["dropped"] == 0
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["right_paragraph_id"] == "A1-P1"
    assert row["right_quote"] == river
    assert row["right_headline"] == "Council sets the river schedule"
    assert row["right_byline"] == "Ada Example"
    assert row["right_url"] == "https://example.test/river"
    assert row["right_published"] == "2026-01-01T00:00:00Z"
    assert row["attributed_to"] == "Ada Example"
    assert row["left_quote"] is None


def test_compare_press_drops_span_over_40_words(monkeypatch):
    config = load_config()
    words = [f"token{i}" for i in range(41)]
    paragraph = " ".join(words)
    payload = _invented_press()
    payload["articles"][0]["paragraphs"][0]["text"] = paragraph
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: payload)
    fake_rows = [{
        "topic": "tokens",
        "label": "only_press",
        "reason": "Only the press has this long invented sentence.",
        "left_quote": None,
        "right_quote": paragraph,
        "right_paragraph_id": "A1-P1",
        "attributed_to": None,
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "tokens", "us", "press")
    assert result["rows"] == []
    assert result["dropped"] == 1
    assert any("span over 40 words" in reason for reason in result["drop_reasons"])
    assert all("..." not in reason for reason in result["drop_reasons"])


def test_press_one_quote_relabels_contradiction(monkeypatch):
    """A row without both quotes cannot stay contradiction."""
    config = load_config()
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: _invented_press())
    river = "The council agreed that the river project would start next spring"
    fake_rows = [{
        "topic": "river",
        "label": "contradiction",
        "reason": "Only one side has a quote.",
        "left_quote": None,
        "right_quote": river,
        "left_paragraph_id": None,
        "right_paragraph_id": "A1-P1",
        "attributed_to": None,
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "river_one_side", "us", "press")
    assert result["dropped"] == 0
    assert result["rows"][0]["label"] == "only_press"
    assert result["rows"][0]["left_quote"] is None
    assert result["rows"][0]["right_quote"] == river


def test_press_two_quote_contradiction_is_not_relabeled(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: _invented_press())
    snap = load_snapshot("washington_2026_09", "us_fact_sheet")
    official = " ".join(snap["paragraphs"][0].split()[:8])
    river = "The council agreed that the river project would start next spring"
    fake_rows = [{
        "topic": "river",
        "label": "contradiction",
        "reason": "These two claims cannot both be true.",
        "left_quote": official,
        "right_quote": river,
        "left_paragraph_id": "P1",
        "right_paragraph_id": "A1-P1",
        "attributed_to": None,
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "river_conflict", "us", "press")
    assert result["dropped"] == 0
    row = result["rows"][0]
    assert row["label"] == "contradiction"
    assert row["left_quote"] == official
    assert row["right_quote"] == river
    assert row["left_headline"] == "White House fact sheet"
    assert row["left_published"] == "2026-09-25"
    assert row["source_note"] is None
    assert row["right_byline"] == "Ada Example"
    assert row["right_url"] == "https://example.test/river"


def test_press_attribution_is_not_rewritten(monkeypatch):
    config = load_config()
    payload = _invented_press()
    payload["articles"][0]["paragraphs"][0]["text"] = (
        "Pat Kim urged a delay, according to a readout from the invented wire service Xinhua."
    )
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: payload)
    fake_rows = [{
        "topic": "delay",
        "label": "only_press",
        "reason": "Only the press mentions the delay.",
        "right_quote": "Pat Kim urged a delay, according to a readout",
        "right_paragraph_id": "A1-P1",
        "attributed_to": "Pat Kim",
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "delay", "us", "press")
    row = result["rows"][0]
    assert row["attributed_to"] == "Pat Kim"
    assert row["reason"] == "Only the press mentions the delay."
    assert row["source_note"] is None


def test_xinhua_attribution_adds_source_note(monkeypatch):
    config = load_config()
    payload = _invented_press()
    payload["articles"][0]["paragraphs"][0]["text"] = (
        "Pat Kim urged a delay, according to a readout from the invented wire service Xinhua."
    )
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: payload)
    fake_rows = [{
        "topic": "delay",
        "label": "only_press",
        "reason": "Only the press mentions the delay.",
        "right_quote": "Pat Kim urged a delay, according to a readout",
        "right_paragraph_id": "A1-P1",
        "attributed_to": "Pat Kim (via Xinhua readout)",
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "delay_note", "us", "press")
    row = result["rows"][0]
    assert row["reason"] == "Only the press mentions the delay."
    assert row["source_note"] == (
        "Cites a Xinhua readout, which is not the China source used here."
    )


def test_press_comma_inside_quote_displays_source_punctuation(monkeypatch):
    config = load_config()
    source = 'Reporters noted what he called "super intelligence", during the Washington visit yesterday.'
    model = 'what he called "super intelligence," during the Washington visit yesterday'
    expected = 'what he called "super intelligence", during the Washington visit yesterday'
    payload = _invented_press()
    payload["articles"][0]["paragraphs"][0]["text"] = source
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: payload)
    fake_rows = [{
        "topic": "naming",
        "label": "only_press",
        "reason": "Only the press reports the name.",
        "right_quote": model,
        "right_paragraph_id": "A1-P1",
        "attributed_to": "Ada Example",
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "comma_case", "us", "press")
    assert result["dropped"] == 0
    assert result["rows"][0]["right_quote"] == expected
    assert model not in result["rows"][0]["right_quote"]


def test_press_one_changed_word_fails(monkeypatch):
    config = load_config()
    source = 'Reporters noted what he called "super intelligence", during the Washington visit yesterday.'
    model = 'what he called "super intelligence," during the Beijing visit yesterday'
    payload = _invented_press()
    payload["articles"][0]["paragraphs"][0]["text"] = source
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: payload)
    fake_rows = [{
        "topic": "naming",
        "label": "only_press",
        "reason": "Only the press reports the name.",
        "right_quote": model,
        "right_paragraph_id": "A1-P1",
        "attributed_to": "Ada Example",
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "changed_word", "us", "press")
    assert result["rows"] == []
    assert result["dropped"] == 1


def test_official_quote_rejects_inserted_comma(monkeypatch):
    """Official verification stays exact. A moved comma is not a press-style word match."""
    config = load_config()
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: _invented_press())
    snap = load_snapshot("washington_2026_09", "us_fact_sheet")
    official = " ".join(snap["paragraphs"][0].split()[:8])
    bad = official.replace(" ", ", ", 1)
    river = "The council agreed that the river project would start next spring"
    fake_rows = [{
        "topic": "river",
        "label": "different_framing",
        "reason": "The two sides use different words.",
        "left_quote": bad,
        "right_quote": river,
        "left_paragraph_id": "P1",
        "right_paragraph_id": "A1-P1",
        "attributed_to": None,
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "official_comma", "us", "press")
    assert result["rows"] == []
    assert result["dropped"] == 1


def test_press_compare_cache_expires_after_23_hours(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: _invented_press())
    river = "The council agreed that the river project would start next spring"
    fake_rows = [{
        "topic": "river",
        "label": "only_press",
        "reason": "Only the press mentions the river project.",
        "right_quote": river,
        "right_paragraph_id": "A1-P1",
        "attributed_to": None,
    }]
    calls = {"n": 0}
    clock = {"now": 1_000_000.0}

    def fake_completion(**kwargs):
        calls["n"] += 1
        return _make_model_response(fake_rows)

    monkeypatch.setattr("compare.litellm.completion", fake_completion)
    monkeypatch.setattr("compare._now", lambda: clock["now"])
    compare_statements(config, "washington_2026_09", "river_cache", "us", "press")
    compare_statements(config, "washington_2026_09", "river_cache", "us", "press")
    assert calls["n"] == 1
    clock["now"] += 23 * 60 * 60 + 1
    compare_statements(config, "washington_2026_09", "river_cache", "us", "press")
    assert calls["n"] == 2


def test_compare_press_does_not_write_citations(monkeypatch):
    config = load_config()
    monkeypatch.setattr("compare.get_press_coverage", lambda config, case_id: _invented_press())
    before = []
    if _press_mod.CITATIONS_DIR.exists():
        before = sorted(path.name for path in _press_mod.CITATIONS_DIR.iterdir())

    def forbid_save(*args, **kwargs):
        raise AssertionError("compare_statements must not write citations")

    monkeypatch.setattr("press.save_citations", forbid_save)
    river = "The council agreed that the river project would start next spring"
    fake_rows = [{
        "topic": "river",
        "label": "only_press",
        "reason": "Only the press mentions the river project.",
        "right_quote": river,
        "right_paragraph_id": "A1-P1",
        "attributed_to": None,
    }]
    monkeypatch.setattr("compare.litellm.completion", lambda **kw: _make_model_response(fake_rows))
    result = compare_statements(config, "washington_2026_09", "river_no_write", "us", "press")
    assert "error" not in result
    after = []
    if _press_mod.CITATIONS_DIR.exists():
        after = sorted(path.name for path in _press_mod.CITATIONS_DIR.iterdir())
    assert after == before


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
