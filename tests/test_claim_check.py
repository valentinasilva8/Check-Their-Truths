"""Phase M tests: check_claim -- all offline, using snapshots and fixtures."""

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from claim_check import (
    _build_context_note,
    _extract_number,
    _find_paragraph,
    _normalize,
    _parse_number,
    load_claims,
    verdict_approximately,
    verdict_at_least,
    verdict_direction,
    check_claim,
)
from sources import load_config, load_snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config():
    return load_config()


def _claims():
    return load_claims()


# ---------------------------------------------------------------------------
# _parse_number: plain and word forms
# ---------------------------------------------------------------------------

def test_parse_number_plain():
    assert _parse_number("90") == Decimal("90")


def test_parse_number_decimal():
    assert _parse_number("202.90") == Decimal("202.90")


def test_parse_number_million():
    assert _parse_number("20 million") == Decimal("20000000")


def test_parse_number_million_with_space():
    assert _parse_number("20 million") == Decimal("20000000")


# ---------------------------------------------------------------------------
# verdict_at_least: rule boundaries
# ---------------------------------------------------------------------------

def test_at_least_equal_supported():
    assert verdict_at_least(Decimal("20000000"), Decimal("20000000")) == "supported"


def test_at_least_greater_supported():
    assert verdict_at_least(Decimal("21000000"), Decimal("20000000")) == "supported"


def test_at_least_less_contradicted():
    assert verdict_at_least(Decimal("19000000"), Decimal("20000000")) == "contradicted"


# ---------------------------------------------------------------------------
# verdict_approximately: 5% and 25% boundaries
# ---------------------------------------------------------------------------

def test_approximately_exactly_5pct_supported():
    # |95 - 100| / 100 = 5% -> supported
    verdict, pct = verdict_approximately(Decimal("95"), Decimal("100"))
    assert verdict == "supported"
    assert pct == Decimal("5.0")


def test_approximately_above_5pct_imprecise():
    # |94 - 100| / 100 = 6% -> imprecise
    verdict, pct = verdict_approximately(Decimal("94"), Decimal("100"))
    assert verdict == "imprecise"
    assert pct == Decimal("6.0")


def test_approximately_exactly_25pct_imprecise():
    # |75 - 100| / 100 = 25% -> imprecise (boundary is imprecise, not contradicted)
    verdict, pct = verdict_approximately(Decimal("75"), Decimal("100"))
    assert verdict == "imprecise"
    assert pct == Decimal("25.0")


def test_approximately_above_25pct_contradicted():
    # |74 - 100| / 100 = 26% -> contradicted
    verdict, pct = verdict_approximately(Decimal("74"), Decimal("100"))
    assert verdict == "contradicted"
    assert pct == Decimal("26.0")


def test_approximately_round_half_up():
    # |90 - 100| / 100 = 10% exactly, rounds to 10.0
    verdict, pct = verdict_approximately(Decimal("90"), Decimal("100"))
    assert verdict == "imprecise"
    assert pct == Decimal("10.0")


# ---------------------------------------------------------------------------
# verdict_direction: increase, decrease, zero
# ---------------------------------------------------------------------------

def test_direction_decrease_is_supported():
    assert verdict_direction("decrease", Decimal("200"), Decimal("185")) == "supported"


def test_direction_increase_is_contradicted_for_decrease_claim():
    assert verdict_direction("decrease", Decimal("185"), Decimal("203")) == "contradicted"


def test_direction_zero_change_is_contradicted():
    assert verdict_direction("decrease", Decimal("185"), Decimal("185")) == "contradicted"


def test_direction_increase_is_supported():
    assert verdict_direction("increase", Decimal("185"), Decimal("203")) == "supported"


def test_direction_decrease_is_contradicted_for_increase_claim():
    assert verdict_direction("increase", Decimal("203"), Decimal("185")) == "contradicted"


# ---------------------------------------------------------------------------
# claimed_phrase not in post -> not_checkable
# ---------------------------------------------------------------------------

def test_claimed_phrase_not_in_post(monkeypatch):
    config = _config()
    claims = _claims()
    # Patch the claim's post to have different text so claimed_phrase is absent
    original_text = claims["posts"]["trump_truth_social_2026_10_02"]["verbatim_text"]
    claims["posts"]["trump_truth_social_2026_10_02"]["verbatim_text"] = "completely different text"
    try:
        result = check_claim(config, claims, "medicare_checks_2026_10", "C1")
    finally:
        claims["posts"]["trump_truth_social_2026_10_02"]["verbatim_text"] = original_text

    assert result["verdict"] == "not_checkable"
    assert result["reason"] == "claimed_phrase not found in post text"


# ---------------------------------------------------------------------------
# check_claim on meeting case -> clear error
# ---------------------------------------------------------------------------

def test_check_claim_on_meeting_case_returns_error():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "washington_2026_09", "C1")
    assert "error" in result
    assert "meeting" in result["error"]


# ---------------------------------------------------------------------------
# C1: at_least -> supported (20 million enrolled)
# ---------------------------------------------------------------------------

def test_c1_supported():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C1")

    assert result["verdict"] == "supported"
    assert result["numbers"]["official"] == "20000000"
    assert result["numbers"]["claimed"] == "20000000"
    assert result["evidence_quote"] is not None
    assert "20 million" in result["evidence_quote"]
    assert result["context_note"] is None


# ---------------------------------------------------------------------------
# C2: approximately -> imprecise ($90 vs $100 claimed)
# ---------------------------------------------------------------------------

def test_c2_imprecise():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C2")

    assert result["verdict"] == "imprecise"
    assert result["numbers"]["official"] == "90"
    assert result["numbers"]["claimed"] == "100.00"
    assert result["numbers"]["pct_diff"] == "10.0%"
    assert result["context_note"] is None


# ---------------------------------------------------------------------------
# C3: direction -> contradicted (premium increased, not decreased)
# ---------------------------------------------------------------------------

def test_c3_contradicted():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    assert result["verdict"] == "contradicted"

    nums = result["numbers"]
    assert nums["2025_premium"] == "185.00"
    assert nums["2026_premium"] == "202.90"
    assert nums["monthly_change"] == "+17.90"
    assert nums["pct_change"] == "+9.7%"
    assert nums["annual_change"] == "214.80"


def test_c3_arithmetic_string():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C3")
    arith = result["arithmetic"]
    # Must contain the three key numbers
    assert "202.90" in arith
    assert "185.00" in arith
    assert "17.90" in arith


def test_c3_context_note_present():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    assert result["context_note"] is not None
    assert result["context_note"].startswith("CMS also states:")
    assert "Part B premium increase would have been about $11 more a month" in result["context_note"]


def test_c3_context_note_contains_verbatim_sentence():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C3")
    snap = load_snapshot("medicare_checks_2026_10", "cms_2026_premiums")

    note = result["context_note"]
    assert note is not None
    # The sentence after the lead-in must be a verbatim substring of a CMS paragraph
    sentence = note[len("CMS also states: "):]
    norm_sentence = _normalize(sentence)
    found = any(norm_sentence in _normalize(p) for p in snap["paragraphs"])
    assert found, f"context_note sentence not found verbatim in CMS snapshot: {sentence!r}"


# ---------------------------------------------------------------------------
# C3 cross-check mismatch -> not_checkable
# ---------------------------------------------------------------------------

def test_c3_cross_check_mismatch(monkeypatch):
    """When stated change does not match computed change, verdict is not_checkable.

    Paragraph contains the anchor so before/after are extracted correctly
    (202.90 - 185.00 = 17.90 computed). A patched regex_stated_change
    captures $18.00 from a second sentence, creating a 17.90 != 18.00 mismatch.
    """
    config = _config()
    claims = _claims()

    # Paragraph has the anchor plus an extra sentence with a different amount.
    # regex_before/regex_after extract from the anchor sentence as normal.
    # Patched regex_stated_change extracts from the extra sentence.
    fake_para = (
        "The standard monthly premium for Medicare Part B enrollees will be "
        "$202.90 for 2026, an increase of $17.90 from $185.00 in 2025. "
        "The uncorrected change would have been $18.00."
    )
    fake_snap = {
        "paragraphs": [fake_para],
        "url": "https://example.com",
        "retrieved_at": "2026-10-05",
        "live": False,
        "live_changed": False,
    }

    # Patch regex_stated_change to capture $18.00 (computed stays 17.90 -> mismatch)
    claims["claims"]["medicare_checks_2026_10"]["C3"]["checks"]["regex_stated_change"] = (
        r"uncorrected change would have been \$([\d.]+)"
    )

    with patch("claim_check.fetch_source_by_name", return_value=fake_snap):
        result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    assert result["verdict"] == "not_checkable"
    assert "stated and computed changes do not match" in result["reason"]


# ---------------------------------------------------------------------------
# context_note absent when anchor missing -> null
# ---------------------------------------------------------------------------

def test_c3_context_note_absent_when_anchor_missing(monkeypatch):
    """context_note is null when the context anchor sentence is not in the source."""
    config = _config()
    claims = _claims()

    # Paragraph has the C3 anchor but NOT the context_note anchor
    fake_para = (
        "The standard monthly premium for Medicare Part B enrollees will be "
        "$202.90 for 2026, an increase of $17.90 from $185.00 in 2025."
    )
    fake_snap = {"paragraphs": [fake_para], "url": "https://example.com", "retrieved_at": "2026-10-05", "live": False, "live_changed": False}

    with patch("claim_check.fetch_source_by_name", return_value=fake_snap):
        result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    assert result["verdict"] == "contradicted"
    assert result["context_note"] is None


# ---------------------------------------------------------------------------
# Anchor missing on live page -> snapshot fallback, live_changed True
# ---------------------------------------------------------------------------

def test_anchor_missing_on_live_page_uses_snapshot(monkeypatch):
    """When marker absent on live page, fetch_source_by_name falls back to snapshot."""
    config = _config()
    claims = _claims()

    # Simulate live page returning content without the marker
    import requests
    mock_resp = type("R", (), {
        "status_code": 200,
        "content": b"<html><body><div class='field--name-body'><p>No marker here.</p></div></body></html>",
    })()

    with patch("sources.fetch_source", return_value=mock_resp):
        result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    # Snapshot fallback: verdict still contradicted from real snapshot data
    assert result["verdict"] == "contradicted"
    assert result["live"] is False
    assert result["live_changed"] is True


# ---------------------------------------------------------------------------
# Extraction tests: anchors found in fixtures
# ---------------------------------------------------------------------------

def test_wh_anchor_found_in_snapshot():
    snap = load_snapshot("medicare_checks_2026_10", "wh_medicare_fact_sheet")
    assert snap is not None, "WH Medicare snapshot missing"
    anchor = "one-time payments of $90 per person to help more than 20 million enrollees"
    found = _find_paragraph(anchor, snap["paragraphs"])
    assert found is not None, f"Anchor not found in WH snapshot"
    assert "20 million" in found


def test_cms_c3_anchor_found_in_snapshot():
    snap = load_snapshot("medicare_checks_2026_10", "cms_2026_premiums")
    assert snap is not None, "CMS snapshot missing"
    anchor = "will be $202.90 for 2026, an increase of $17.90 from $185.00"
    found = _find_paragraph(anchor, snap["paragraphs"])
    assert found is not None, "C3 anchor not found in CMS snapshot"
    assert "202.90" in found


def test_cms_context_anchor_found_in_snapshot():
    snap = load_snapshot("medicare_checks_2026_10", "cms_2026_premiums")
    assert snap is not None, "CMS snapshot missing"
    anchor = "the Part B premium increase would have been about $11 more a month"
    found = _find_paragraph(anchor, snap["paragraphs"])
    assert found is not None, "context_note anchor not found in CMS snapshot"


def test_cms_c3_numbers_extract_correctly():
    snap = load_snapshot("medicare_checks_2026_10", "cms_2026_premiums")
    anchor = "will be $202.90 for 2026, an increase of $17.90 from $185.00"

    before, _ = _extract_number(anchor, r"from \$([\d.]+) in 2025", snap["paragraphs"])
    after, _ = _extract_number(anchor, r"will be \$([\d.]+) for 2026", snap["paragraphs"])
    stated, _ = _extract_number(anchor, r"increase of \$([\d.]+) from", snap["paragraphs"])

    assert before == Decimal("185.00"), f"Expected 185.00, got {before}"
    assert after == Decimal("202.90"), f"Expected 202.90, got {after}"
    assert stated == Decimal("17.90"), f"Expected 17.90, got {stated}"
