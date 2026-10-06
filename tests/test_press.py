"""Phase P tests. Guardian responses are mocked. Bodies are invented text."""

import json
from pathlib import Path

import pytest

import press as press_mod
from press import (
    citation_record_errors,
    get_press_coverage,
    match_press_span,
    quote_sha256,
    save_citations,
    verify_citations,
)
from sources import load_config


@pytest.fixture(autouse=True)
def clear_press_cache():
    press_mod._cache.clear()
    yield
    press_mod._cache.clear()


class _Response:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = ""

    def json(self):
        if self.status_code != 200:
            raise ValueError("no json")
        return self._payload


def _payload(article_id: str, body: str, type_name: str = "article") -> dict:
    return {
        "response": {
            "content": {
                "id": article_id,
                "type": type_name,
                "webUrl": f"https://example.test/{article_id}",
                "webPublicationDate": "2026-01-02T03:04:05Z",
                "fields": {
                    "headline": "Invented headline for tests",
                    "byline": "Test Writer",
                    "body": body,
                },
            }
        }
    }


def _article_ids() -> list[str]:
    config = load_config()
    return list(config["cases"]["washington_2026_09"]["press_articles"])


def test_fetch_numbers_paragraphs_across_articles(monkeypatch):
    config = load_config()
    ids = _article_ids()
    bodies = {
        ids[0]: (
            "<p>The council agreed that the river project would start next spring without delay.</p>"
            "<p>A spokesperson said the bridge plan was postponed until the following year entirely.</p>"
            "<div>This div is not a paragraph and must be ignored.</div>"
        ),
        ids[1]: "<p>The harbor board approved a new dock for the fishing fleet last month.</p>",
    }
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        article_id = url.split(config["guardian"]["content_api"].rstrip("/") + "/")[1]
        assert "search" not in url
        assert params["show-fields"] == config["guardian"]["show_fields"]
        assert "api-key" in params
        return _Response(200, _payload(article_id, bodies[article_id]))

    monkeypatch.setattr("press.requests.get", fake_get)
    monkeypatch.setattr("press._load_api_key", lambda: "test-key-not-real")
    result = get_press_coverage(config, "washington_2026_09")
    assert "error" not in result
    flat = [
        paragraph["id"]
        for article in result["articles"]
        for paragraph in article["paragraphs"]
    ]
    assert flat == ["A1-P1", "A1-P2", "A2-P1"]
    texts = [
        paragraph["text"]
        for article in result["articles"]
        for paragraph in article["paragraphs"]
    ]
    assert all("div is not a paragraph" not in text for text in texts)
    assert result["articles"][0]["headline"] == "Invented headline for tests"
    assert result["articles"][0]["url"].startswith("https://example.test/")
    assert len(calls) == 2

    get_press_coverage(config, "washington_2026_09")
    assert len(calls) == 2  # second call is the in-memory cache


def test_api_500_is_unavailable(monkeypatch):
    config = load_config()
    monkeypatch.setattr("press._load_api_key", lambda: "test-key-not-real")
    monkeypatch.setattr(
        "press.requests.get",
        lambda *args, **kwargs: _Response(500),
    )
    result = get_press_coverage(config, "washington_2026_09")
    assert result["error"].startswith("press side unavailable")
    assert "Do not invent Guardian text" in result["error"]
    assert "compare_statements" in result["error"]
    assert "test-key-not-real" not in json.dumps(result)


def test_missing_secrets_is_unavailable(monkeypatch):
    config = load_config()
    called = {"n": 0}

    def fail_get(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("must not fetch without a key")

    monkeypatch.setattr("press._load_api_key", lambda: None)
    monkeypatch.setattr("press.requests.get", fail_get)
    result = get_press_coverage(config, "washington_2026_09")
    assert result["error"].startswith("press side unavailable")
    assert "Do not invent Guardian text" in result["error"]
    assert "compare_statements" in result["error"]
    assert called["n"] == 0


def test_liveblog_is_excluded(monkeypatch):
    config = load_config()
    ids = _article_ids()

    def fake_get(url, params=None, headers=None, timeout=None):
        article_id = url.split(config["guardian"]["content_api"].rstrip("/") + "/")[1]
        body = "<p>The council agreed that the river project would start next spring without delay.</p>"
        return _Response(200, _payload(article_id, body, type_name="liveblog"))

    monkeypatch.setattr("press.requests.get", fake_get)
    monkeypatch.setattr("press._load_api_key", lambda: "test-key-not-real")
    result = get_press_coverage(config, "washington_2026_09")
    assert result["error"].startswith("press side unavailable")
    assert "Do not invent Guardian text" in result["error"]
    assert "compare_statements" in result["error"]
    assert ids  # config still has curated ids; they were excluded by type


def test_wrong_case_type():
    config = load_config()
    result = get_press_coverage(config, "medicare_checks_2026_10")
    assert "error" in result
    assert "meeting" in result["error"]


def test_fetch_does_not_write_a_citation_file(monkeypatch, tmp_path):
    config = load_config()
    monkeypatch.setattr(press_mod, "CITATIONS_DIR", tmp_path)
    ids = _article_ids()

    def fake_get(url, params=None, headers=None, timeout=None):
        article_id = url.split(config["guardian"]["content_api"].rstrip("/") + "/")[1]
        body = "<p>The council agreed that the river project would start next spring without delay.</p>"
        if article_id == ids[1]:
            body = "<p>The harbor board approved a new dock for the fishing fleet last month.</p>"
        return _Response(200, _payload(article_id, body))

    monkeypatch.setattr("press.requests.get", fake_get)
    monkeypatch.setattr("press._load_api_key", lambda: "test-key-not-real")
    result = get_press_coverage(config, "washington_2026_09")
    assert "error" not in result
    assert list(tmp_path.iterdir()) == []


def test_citation_validator_rejects_quote_text_and_missing_fields(tmp_path):
    bad = {
        "case_id": "example",
        "citations": [
            {
                "headline": "Invented headline",
                "url": "https://example.test/one",
                "byline": "Test Writer",
                "published": "2026-01-02T03:04:05Z",
                "paragraph_id": "A1-P1",
                "quote": "The council agreed that the river project would start",
                "attributed_to": None,
                "retrieved_at": "2026-01-03T00:00:00-04:00",
                "quote_sha256": "not-a-hash",
            },
            {
                "paragraph_id": "A2-P1",
            },
        ],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    errors = citation_record_errors(json.loads(path.read_text(encoding="utf-8")))
    assert any("quote text must not be stored" in error for error in errors)
    assert any("missing byline" in error for error in errors)
    assert any("missing url" in error for error in errors)
    assert any("missing headline" in error for error in errors)
    assert any("missing published" in error for error in errors)
    assert any("missing retrieved_at" in error for error in errors)
    assert any("quote_sha256" in error for error in errors)


def test_match_press_span_keeps_source_punctuation():
    source = 'Reporters noted what he called "super intelligence", during the Washington visit yesterday.'
    model = 'what he called "super intelligence," during the Washington visit yesterday'
    expected = 'what he called "super intelligence", during the Washington visit yesterday'
    assert match_press_span(model, source) == expected


def test_match_press_span_rejects_one_changed_word():
    source = 'Reporters noted what he called "super intelligence", during the Washington visit yesterday.'
    model = 'what he called "super intelligence," during the Beijing visit yesterday'
    assert match_press_span(model, source) is None


def test_press_cache_expires_after_23_hours(monkeypatch):
    config = load_config()
    ids = _article_ids()
    calls = {"n": 0}
    clock = {"now": 1_000_000.0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["n"] += 1
        article_id = url.split(config["guardian"]["content_api"].rstrip("/") + "/")[1]
        body = "<p>The council agreed that the river project would start next spring without delay.</p>"
        if article_id == ids[1]:
            body = "<p>The harbor board approved a new dock for the fishing fleet last month.</p>"
        return _Response(200, _payload(article_id, body))

    monkeypatch.setattr("press.requests.get", fake_get)
    monkeypatch.setattr("press._load_api_key", lambda: "test-key-not-real")
    monkeypatch.setattr("press._now", lambda: clock["now"])
    assert "error" not in get_press_coverage(config, "washington_2026_09")
    assert calls["n"] == 2
    assert "error" not in get_press_coverage(config, "washington_2026_09")
    assert calls["n"] == 2
    clock["now"] += 23 * 60 * 60 + 1
    assert "error" not in get_press_coverage(config, "washington_2026_09")
    assert calls["n"] == 4


def test_save_citations_writes_hashes_not_quotes(monkeypatch, tmp_path):
    config = load_config()
    press_result = {
        "case_id": "washington_2026_09",
        "articles": [
            {
                "article_id": "example/river-plan",
                "headline": "Council sets the river schedule",
                "byline": "Ada Example",
                "url": "https://example.test/river",
                "published": "2026-01-01T00:00:00Z",
                "paragraphs": [
                    {
                        "id": "A1-P1",
                        "text": "The council agreed that the river project would start next spring without delay.",
                    }
                ],
            }
        ],
    }
    monkeypatch.setattr("press.get_press_coverage", lambda config, case_id: press_result)

    def fake_compare(config, case_id, topic, left, right):
        return {
            "rows": [
                {
                    "label": "only_press",
                    "topic": "river",
                    "reason": "Only the press mentions the river project.",
                    "left_quote": None,
                    "right_quote": "The council agreed that the river project would start next spring",
                    "right_paragraph_id": "A1-P1",
                    "attributed_to": "Ada Example",
                }
            ]
        }

    monkeypatch.setattr("compare.compare_statements", fake_compare)
    dest = tmp_path / "washington_2026_09.json"
    result = save_citations(config, "washington_2026_09", dest=dest)
    assert "error" not in result
    saved = json.loads(dest.read_text(encoding="utf-8"))
    assert citation_record_errors(saved) == []
    assert len(saved["citations"]) == 1
    entry = saved["citations"][0]
    assert entry["url"] == "https://example.test/river"
    assert entry["headline"] == "Council sets the river schedule"
    assert entry["published"] == "2026-01-01T00:00:00Z"
    assert entry["paragraph_id"] == "A1-P1"
    displayed = "The council agreed that the river project would start next spring"
    assert entry["retrieved_at"]
    assert entry["byline"] == "Ada Example"
    assert "quote" not in entry
    assert entry["quote_sha256"] == quote_sha256(displayed)
    assert "river project" not in dest.read_text(encoding="utf-8")


def test_verify_citations_refetches_and_checks_the_hash(monkeypatch, tmp_path):
    quote = "The council agreed that the river project would start next spring"
    press_result = {
        "case_id": "washington_2026_09",
        "articles": [
            {
                "headline": "Council sets the river schedule",
                "byline": "Ada Example",
                "url": "https://example.test/river",
                "published": "2026-01-01T00:00:00Z",
                "paragraphs": [
                    {
                        "id": "A1-P1",
                        "text": "The council agreed that the river project would start next spring without delay.",
                    }
                ],
            }
        ],
    }
    seen = {}

    def fake_get(config, case_id, refresh=False):
        seen["refresh"] = refresh
        return press_result

    monkeypatch.setattr("press.get_press_coverage", fake_get)
    entry = {
        "url": "https://example.test/river",
        "headline": "Council sets the river schedule",
        "byline": "Ada Example",
        "paragraph_id": "A1-P1",
        "published": "2026-01-01T00:00:00Z",
        "retrieved_at": "2026-01-03T00:00:00-04:00",
        "attributed_to": "Ada Example",
        "quote_sha256": quote_sha256(quote),
    }
    path = tmp_path / "citations.json"
    path.write_text(json.dumps({"case_id": "washington_2026_09", "citations": [entry]}), encoding="utf-8")
    result = verify_citations(load_config(), "washington_2026_09", path=path)
    assert seen["refresh"] is True
    assert result["ok"] is True
    assert result["checked"] == 1

    entry["quote_sha256"] = quote_sha256("a different invented sentence that is not in the paragraph")
    path.write_text(json.dumps({"case_id": "washington_2026_09", "citations": [entry]}), encoding="utf-8")
    result = verify_citations(load_config(), "washington_2026_09", path=path)
    assert result["ok"] is False
    assert result["mismatches"]


def test_stored_press_citations_are_content_free():
    """Fails if the citation file stores quote text or is missing required fields."""
    path = Path(__file__).resolve().parents[1] / "data" / "press_citations" / "washington_2026_09.json"
    assert path.exists(), f"citation record missing at {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = citation_record_errors(data)
    assert errors == []
    assert data["citations"], "citation record is empty"
    assert '"quote"' not in path.read_text(encoding="utf-8")
