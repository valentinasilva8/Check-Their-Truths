"""The home page and its files load. No model call."""

from fastapi.testclient import TestClient

from app import app


def test_home_page_and_assets_load():
    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    assert "Two Readouts" in page.text
    assert "/static/styles.css" in page.text
    assert "/static/app.js" in page.text

    css = client.get("/static/styles.css")
    script = client.get("/static/app.js")
    assert css.status_code == 200
    assert "Newsreader" in css.text
    assert script.status_code == 200
    assert "compare_statements" in script.text
