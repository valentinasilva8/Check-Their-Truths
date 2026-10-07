"""The home page and its files load. No model call."""

from fastapi.testclient import TestClient

from app import app


def test_home_page_and_assets_load():
    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    assert "Check Their Truths" in page.text
    assert "/static/styles.css" in page.text
    assert "/static/app.js" in page.text

    css = client.get("/static/styles.css")
    script = client.get("/static/app.js")
    assert css.status_code == 200
    assert "Newsreader" in css.text
    assert script.status_code == 200
    assert "compare_statements" in script.text


def test_arithmetic_is_shown_exactly_and_only_counts_get_commas():
    client = TestClient(app)
    script = client.get("/static/app.js").text
    assert "commaIntegers" not in script
    assert r"\d{4,}" not in script
    assert 'el("p", "arithmetic", result.arithmetic)' in script
    assert "function formatCount" in script
    assert "/^\\d{5,}$/" in script
