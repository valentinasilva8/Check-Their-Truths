"""Phase A + B tests: config loading, HTML extraction, fallback, URL safety, and tools."""

from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from sources import (
    extract_paragraphs,
    fetch_source,
    get_official_source,
    get_sources_for_side,
    load_config,
    load_snapshot,
    normalize_text,
)

FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_loads():
    config = load_config()
    assert "washington_2026_09" in config["cases"]


def test_config_sources():
    config = load_config()
    sources = config["cases"]["washington_2026_09"]["sources"]
    names = {s["name"] for s in sources}
    assert "us_fact_sheet" in names
    assert "china_mfa_english" in names
    assert "china_govcn_mirror" in names
    assert "china_embassy_mirror" in names
    assert "china_mfa_chinese_original" in names


def test_config_side_filter():
    config = load_config()
    us_sources = get_sources_for_side(config, "washington_2026_09", "us")
    china_sources = get_sources_for_side(config, "washington_2026_09", "china")
    assert all(s["side"] == "us" for s in us_sources)
    assert all(s["side"] == "china" for s in china_sources)
    assert all(s.get("role") != "term_check_only" for s in china_sources)


def test_config_priority_order():
    config = load_config()
    china = get_sources_for_side(config, "washington_2026_09", "china")
    priorities = [s["priority"] for s in china]
    assert priorities == sorted(priorities)


def test_cases_both_types():
    config = load_config()
    cases = config["cases"]
    assert cases["washington_2026_09"]["type"] == "meeting"
    assert cases["medicare_checks_2026_10"]["type"] == "claim_check"


def test_get_official_source_wrong_case_type():
    config = load_config()
    result = get_official_source(config, "medicare_checks_2026_10", "us")
    assert "error" in result
    assert "meeting" in result["error"]


# ---------------------------------------------------------------------------
# Extraction: content checks on saved HTML fixtures
# ---------------------------------------------------------------------------

def _fixture(name: str) -> bytes:
    path = FIXTURES / f"{name}.html"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}. Run: python sources.py --refresh-snapshots")
    return path.read_bytes()


def test_whitehouse_contains_super_intelligence():
    html = _fixture("us_fact_sheet")
    paras = extract_paragraphs(html, "us_fact_sheet", "en")
    combined = " ".join(paras).lower()
    assert "super intelligence" in combined


def test_mfa_english_contains_ai_dialogue():
    html = _fixture("china_mfa_english")
    paras = extract_paragraphs(html, "china_mfa_english", "en")
    combined = " ".join(paras)
    assert "China-U.S. AI Dialogue" in combined


def test_mfa_english_last_paragraph_mentions_servicemembers():
    html = _fixture("china_mfa_english")
    paras = extract_paragraphs(html, "china_mfa_english", "en")
    assert paras, "No paragraphs extracted"
    assert "servicemembers" in paras[-1].lower()


def test_chinese_original_contains_rengong_zhineng():
    html = _fixture("china_mfa_chinese_original")
    paras = extract_paragraphs(html, "china_mfa_chinese_original", "zh")
    combined = "".join(paras)
    assert "人工智能" in combined


def test_no_boilerplate_in_any_fixture():
    source_names = [
        ("us_fact_sheet", "en"),
        ("china_mfa_english", "en"),
        ("china_govcn_mirror", "en"),
        ("china_embassy_mirror", "en"),
        ("china_mfa_chinese_original", "zh"),
    ]
    boilerplate = ["Privacy Policy", "Skip to", "Copyright"]
    for source_name, lang in source_names:
        html = _fixture(source_name)
        paras = extract_paragraphs(html, source_name, lang)
        for para in paras:
            for phrase in boilerplate:
                assert phrase not in para, (
                    f"Boilerplate '{phrase}' found in {source_name}: {para[:120]!r}"
                )


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def test_fallback_to_snapshot(monkeypatch):
    config = load_config()

    china_sources = get_sources_for_side(config, "washington_2026_09", "china")
    has_snapshot = any(
        load_snapshot("washington_2026_09", s["name"]) for s in china_sources
    )
    if not has_snapshot:
        pytest.skip("No china snapshot saved yet. Run: python sources.py --refresh-snapshots")

    def fail(*args, **kwargs):
        raise requests.ConnectionError("simulated network failure")

    monkeypatch.setattr(requests, "get", fail)
    result = get_official_source(config, "washington_2026_09", "china")
    assert "error" not in result, f"Expected fallback, got: {result.get('error')}"
    assert result["live"] is False
    assert result["paragraphs"]


def test_live_page_changed_flag(monkeypatch):
    config = load_config()

    china_sources = get_sources_for_side(config, "washington_2026_09", "china")
    has_snapshot = any(
        load_snapshot("washington_2026_09", s["name"]) for s in china_sources
    )
    if not has_snapshot:
        pytest.skip("No china snapshot saved yet. Run: python sources.py --refresh-snapshots")

    class FakeResponse:
        status_code = 200
        url = "https://www.fmprc.gov.cn/eng/xw/zyxw/202609/t20260926_12031663.html"
        content = b"<html><body><p>No marker here</p></body></html>"

    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())
    result = get_official_source(config, "washington_2026_09", "china")
    assert "error" not in result, f"Expected snapshot fallback, got: {result.get('error')}"
    assert result["live"] is False
    assert result.get("live_changed") is True
    assert result.get("live_changed_note") == "live page changed or unavailable; showing snapshot"


# ---------------------------------------------------------------------------
# URL safety
# ---------------------------------------------------------------------------

def test_url_not_in_config_refused():
    config = load_config()
    with pytest.raises(ValueError, match="URL not in config"):
        fetch_source("https://evil.com/malicious", config)


def test_empty_url_refused():
    config = load_config()
    with pytest.raises(ValueError, match="URL not in config"):
        fetch_source("", config)


# ---------------------------------------------------------------------------
# normalize_text: shared normalization utility
# ---------------------------------------------------------------------------

def test_normalize_text_collapses_whitespace():
    assert normalize_text("  hello   world  ") == "hello world"


def test_normalize_text_nbsp_becomes_space():
    assert normalize_text("hello\xa0world") == "hello world"


def test_normalize_text_curly_single_quotes():
    assert normalize_text("‘hello’") == "'hello'"


def test_normalize_text_curly_double_quotes():
    assert normalize_text("“hello”") == '"hello"'
