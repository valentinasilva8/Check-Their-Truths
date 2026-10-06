"""Phase M tests: check_claim -- all offline, using snapshots and fixtures."""

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from claim_check import (
    _build_context_note,
    _extract_number,
    _extract_sentence,
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
    assert result["reason"] == (
        "claimed_phrase not found in post text. Do not invent a verdict. "
        "Tell the user this phrase is not in the post excerpt."
    )


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
    assert result["checked_against"] == "Checked against: White House fact sheet, Oct 2, 2026"
    assert result["source_date"] == "2026-10-02"
    assert result["numbers"]["official"] == "20000000"
    assert result["numbers"]["claimed"] == "20000000"
    assert result["evidence_quote"] == (
        "Today, President Donald J. Trump announced that the federal government "
        "will be making one-time payments of $90 per person to help more than "
        "20 million enrollees pay for their Medicare Part B premiums."
    )
    assert result["context_note"] is None


# ---------------------------------------------------------------------------
# C2: approximately -> imprecise ($90 vs $100 claimed)
# ---------------------------------------------------------------------------

def test_c2_imprecise():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C2")

    assert result["verdict"] == "imprecise"
    assert result["numbers"]["official"] == "90.00"
    assert result["numbers"]["claimed"] == "100.00"
    assert result["numbers"]["pct_diff"] == "10.0%"
    assert result["evidence_quote"] == (
        "Today, President Donald J. Trump announced that the federal government "
        "will be making one-time payments of $90 per person to help more than "
        "20 million enrollees pay for their Medicare Part B premiums."
    )
    assert result["context_note"] is None


def test_c2_official_has_two_decimals():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C2")
    assert result["numbers"]["official"] == "90.00"


# ---------------------------------------------------------------------------
# C3: direction -> contradicted (premium increased, not decreased)
# ---------------------------------------------------------------------------

def test_c3_contradicted():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    assert result["verdict"] == "contradicted"
    assert result["checked_against"] == "Checked against: CMS fact sheet, Nov 14, 2025"
    assert result["source_date"] == "2025-11-14"

    nums = result["numbers"]
    assert nums["2025_premium"] == "185.00"
    assert nums["2026_premium"] == "202.90"
    assert nums["monthly_change"] == "+17.90"
    assert nums["pct_change"] == "+9.7%"
    assert nums["annual_change"] == "214.80"
    assert result["evidence_quote"] == (
        "The standard monthly premium for Medicare Part B enrollees will be "
        "$202.90 for 2026, an increase of $17.90 from $185.00 in 2025."
    )


def test_c3_arithmetic_string():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C3")
    assert result["arithmetic"] == (
        "202.90 - 185.00 = +17.90 per month (+9.7% vs 2025); "
        "17.90 x 12 = 214.80 per year"
    )


def test_c3_source_date_is_publication_date_not_retrieval_date():
    config = _config()
    claims = _claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C3")
    cms = next(
        source for source in config["cases"]["medicare_checks_2026_10"]["sources"]
        if source["name"] == "cms_2026_premiums"
    )
    snap = load_snapshot("medicare_checks_2026_10", "cms_2026_premiums")
    assert cms["published"] == "2025-11-14"
    assert result["source_date"] == cms["published"]
    assert result["source_date"] != snap["retrieved_at"][:10]


def test_sentence_splitter_keeps_donald_j_trump():
    expected = (
        "Today, President Donald J. Trump announced that the federal government "
        "will be making one-time payments of $90 per person to help more than "
        "20 million enrollees pay for their Medicare Part B premiums."
    )
    headed = "IMPROVING MEDICARE FOR SENIORS: " + expected
    followed = expected + " The deductible rose the next year."
    assert _extract_sentence("one-time payments of", expected) == expected
    assert _extract_sentence("one-time payments of", headed) == expected
    assert _extract_sentence("one-time payments of", followed) == expected
    assert _extract_sentence("spoke next", "Dr. Smith spoke next. Then the hearing ended.") == (
        "Dr. Smith spoke next."
    )
    assert _extract_sentence("plan held", "Mr. Jones waited. The U.S. plan held.") == (
        "The U.S. plan held."
    )


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
    """Stated change ($18.00) != computed (202.90 - 185.00 = $17.90) -> not_checkable.

    Number-free anchor matches the paragraph, regexes run sentence-scoped, producing
    computed=17.90 vs stated=18.00. No regex patching needed (D-41).
    """
    config = _config()
    claims = _claims()

    fake_para = (
        "The standard monthly premium for Medicare Part B enrollees will be "
        "$202.90 for 2026, an increase of $18.00 from $185.00 in 2025."
    )
    fake_snap = {
        "paragraphs": [fake_para],
        "url": "https://example.com",
        "retrieved_at": "2026-10-05",
        "live": False,
        "live_changed": False,
    }

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
    # Number-free anchor (D-41)
    anchor = "announced that the federal government will be making one-time payments of"
    found = _find_paragraph(anchor, snap["paragraphs"])
    assert found is not None, "Anchor not found in WH snapshot"
    assert "20 million" in found


def test_cms_c3_anchor_found_in_snapshot():
    snap = load_snapshot("medicare_checks_2026_10", "cms_2026_premiums")
    assert snap is not None, "CMS snapshot missing"
    # Number-free anchor (D-41)
    anchor = "The standard monthly premium for Medicare Part B enrollees will be"
    found = _find_paragraph(anchor, snap["paragraphs"])
    assert found is not None, "C3 anchor not found in CMS snapshot"
    assert "202.90" in found


def test_cms_context_anchor_found_in_snapshot():
    snap = load_snapshot("medicare_checks_2026_10", "cms_2026_premiums")
    assert snap is not None, "CMS snapshot missing"
    # Number-free anchor (D-41)
    anchor = "had not taken action to address unprecedented spending on skin substitutes"
    found = _find_paragraph(anchor, snap["paragraphs"])
    assert found is not None, "context_note anchor not found in CMS snapshot"


def test_cms_c3_numbers_extract_correctly():
    snap = load_snapshot("medicare_checks_2026_10", "cms_2026_premiums")
    # Number-free anchor (D-41): runs regex on the sentence containing anchor only
    anchor = "The standard monthly premium for Medicare Part B enrollees will be"

    before, _ = _extract_number(anchor, r"from \$([\d.]+) in 2025", snap["paragraphs"])
    after, _ = _extract_number(anchor, r"will be \$([\d.]+) for 2026", snap["paragraphs"])
    stated, _ = _extract_number(anchor, r"increase of \$([\d.]+) from", snap["paragraphs"])

    assert before == Decimal("185.00"), f"Expected 185.00, got {before}"
    assert after == Decimal("202.90"), f"Expected 202.90, got {after}"
    assert stated == Decimal("17.90"), f"Expected 17.90, got {stated}"


# ---------------------------------------------------------------------------
# Anchor fallback tests (D-43)
# ---------------------------------------------------------------------------

def test_live_200_marker_present_required_anchor_missing_uses_snapshot():
    """Live page has marker but not the required anchor -> falls back to snapshot.

    The snapshot has the anchor, so the verdict is still contradicted (real data).
    live=False and live_changed=True on the result.
    """
    config = _config()
    claims = _claims()

    # Live page: has marker phrase but NOT the C3 anchor phrase
    fake_html = (
        b"<html><body><div class=\"field--name-body\">"
        b"<p>Medicare Part B Premium and Deductible</p>"
        b"<p>The 2026 Part B standard premium information is here.</p>"
        b"</div></body></html>"
    )
    mock_resp = type("R", (), {"status_code": 200, "content": fake_html})()

    with patch("sources.fetch_source", return_value=mock_resp):
        result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    assert result["verdict"] == "contradicted"
    assert result["live"] is False
    assert result["live_changed"] is True


def test_anchor_missing_in_live_and_snapshot_returns_not_checkable():
    """Anchor absent in both live page and snapshot -> not_checkable."""
    config = _config()
    claims = _claims()

    fake_html = (
        b"<html><body><div class=\"field--name-body\">"
        b"<p>Medicare Part B Premium and Deductible</p>"
        b"<p>The 2026 Part B standard premium information is here.</p>"
        b"</div></body></html>"
    )
    mock_resp = type("R", (), {"status_code": 200, "content": fake_html})()

    # Snapshot also lacks the anchor phrase
    fake_snap = {
        "paragraphs": ["Some CMS text without the target anchor phrase."],
        "url": "https://example.com",
        "retrieved_at": "2026-10-05",
        "language": "en",
    }

    with patch("sources.fetch_source", return_value=mock_resp), \
         patch("sources.load_snapshot", return_value=fake_snap):
        result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    assert result["verdict"] == "not_checkable"
    assert "anchor not found in live page or snapshot" in result["reason"]


def test_number_change_on_live_page_uses_live_numbers():
    """When the live page has a different premium (anchor intact), live numbers are used.

    Marker phrase present; no old number ($202.90) anywhere on the page.
    The main sentence has $205.00, so regexes extract the new values from the live page.
    """
    config = _config()
    claims = _claims()

    # Anchor phrase is present; numbers differ from snapshot
    fake_html = (
        b"<html><body><div class=\"field--name-body\">"
        b"<p>Medicare Part B Premium and Deductible</p>"
        b"<p>The standard monthly premium for Medicare Part B enrollees will be"
        b" $205.00 for 2026, an increase of $20.00 from $185.00 in 2025.</p>"
        b"</div></body></html>"
    )
    mock_resp = type("R", (), {"status_code": 200, "content": fake_html})()

    with patch("sources.fetch_source", return_value=mock_resp):
        result = check_claim(config, claims, "medicare_checks_2026_10", "C3")

    # Live page numbers used, not snapshot
    assert result["live"] is True
    assert result["numbers"]["2026_premium"] == "205.00"
    assert result["numbers"]["2025_premium"] == "185.00"
    assert result["numbers"]["monthly_change"] == "+20.00"
    assert result["verdict"] == "contradicted"
