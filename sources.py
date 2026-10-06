"""Config loading, URL fetching, HTML extraction, snapshot I/O, and live-first statement loader."""

import json
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

_HERE = Path(__file__).parent
CONFIG_PATH = _HERE / "config" / "sources.toml"
SNAPSHOTS_DIR = _HERE / "data" / "snapshots"
FIXTURES_DIR = _HERE / "tests" / "fixtures"
NY_TZ = ZoneInfo("America/New_York")
USER_AGENT = (
    "TwoReadouts/1.0 (Columbia IEOR4570 class project; "
    "github.com/valentinasilva8/gemini-web-tool-calling)"
)
FETCH_TIMEOUT = 20


# ---------------------------------------------------------------------------
# Config and secrets
# ---------------------------------------------------------------------------

def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_secrets() -> dict:
    """Read secrets file. Cloud Run mounts at /secrets/guardian.toml;
    local dev uses config/secrets.toml (gitignored). Never an env var."""
    cloud = Path("/secrets/guardian.toml")
    local = _HERE / "config" / "secrets.toml"
    path = cloud if cloud.exists() else local
    with open(path, "rb") as f:
        return tomllib.load(f)


def get_sources_for_side(config: dict, case_id: str, side: str) -> list[dict]:
    """Return statement sources for one side of a meeting case, sorted by priority.

    Excludes sources with role=term_check_only (Chinese original).
    Raises ValueError if the case is not found or is not a meeting type.
    """
    case = config["cases"].get(case_id)
    if not case:
        raise ValueError(f"Case '{case_id}' not found. Call list_cases to see supported cases.")
    if case.get("type") != "meeting":
        raise ValueError(
            f"Case '{case_id}' is type '{case.get('type')}', not 'meeting'. "
            "get_official_source only works for meeting cases."
        )
    if side not in ("us", "china"):
        raise ValueError(f"source must be 'us' or 'china', got '{side}'.")
    sources = [
        s for s in case["sources"]
        if s["side"] == side and s.get("role") != "term_check_only"
    ]
    return sorted(sources, key=lambda s: s["priority"])


def get_term_check_source(config: dict, case_id: str) -> dict | None:
    """Return the term_check_only source (Chinese original) for a meeting, or None."""
    case = config["cases"].get(case_id)
    if not case:
        return None
    for s in case.get("sources", []):
        if s.get("role") == "term_check_only":
            return s
    return None


def _config_url_set(config: dict) -> set[str]:
    urls: set[str] = set()
    for case in config.get("cases", {}).values():
        for source in case.get("sources", []):
            url = source.get("url", "")
            if url.startswith("http"):
                urls.add(url)
    return urls


def _config_host_set(config: dict) -> set[str]:
    return {urlparse(url).hostname for url in _config_url_set(config)}


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_source(url: str, config: dict) -> requests.Response:
    """Fetch a URL that must be listed in config/sources.toml.

    Raises ValueError if the URL is not in the config or if the response
    redirects to a host not in the config.
    """
    if url not in _config_url_set(config):
        raise ValueError(f"URL not in config: {url}")

    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=FETCH_TIMEOUT,
        allow_redirects=True,
    )

    final_host = urlparse(resp.url).hostname
    if final_host not in _config_host_set(config):
        raise ValueError(
            f"Response redirected to unexpected host '{final_host}' "
            f"(started at {urlparse(url).hostname})."
        )

    return resp


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _strip_boilerplate(soup: BeautifulSoup) -> None:
    """Remove navigation, chrome, and script elements in place."""
    for tag in soup.find_all(
        ["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]
    ):
        tag.decompose()


def _texts_from(container, language: str = "en") -> list[str]:
    """Collect text from <p> and <li> tags within a container.

    For Chinese (language='zh'), drops strings shorter than 10 characters
    to skip lone punctuation and navigation fragments.
    """
    results = []
    for tag in container.find_all(["p", "li"]):
        # Skip nested li inside li to avoid duplicating bullet text
        if tag.name == "li" and tag.find_parent("li"):
            continue
        text = tag.get_text(separator=" ", strip=True)
        if not text:
            continue
        if language == "zh" and len(text) < 10:
            continue
        results.append(text)
    return results


def _extract_whitehouse(soup: BeautifulSoup) -> list[str]:
    # WordPress block theme: article content lives in div.entry-content
    container = soup.find("div", class_=lambda c: c and "entry-content" in c.split())
    if container:
        return _texts_from(container)
    return _texts_from(soup.find("main") or soup.body or soup)


def _extract_trs(soup: BeautifulSoup) -> list[str]:
    # MFA English and Embassy mirror share the TRS CMS; content is in
    # the div whose class includes TRS_UEDITOR.
    container = soup.find("div", class_=lambda c: c and "TRS_UEDITOR" in c.split())
    if container:
        return _texts_from(container)
    return _texts_from(soup.body or soup)


def _extract_govcn(soup: BeautifulSoup) -> list[str]:
    container = soup.find("div", class_="Artical_Content")
    if container:
        return _texts_from(container)
    return _texts_from(soup.body or soup)


def _extract_mfa_chinese(soup: BeautifulSoup) -> list[str]:
    container = soup.find("div", id="News_Body_Txt_A")
    if container:
        return _texts_from(container, language="zh")
    return _texts_from(soup.body or soup, language="zh")


_EXTRACTORS: dict[str, callable] = {
    "us_fact_sheet": lambda soup: _extract_whitehouse(soup),
    "china_mfa_english": lambda soup: _extract_trs(soup),
    "china_govcn_mirror": lambda soup: _extract_govcn(soup),
    "china_embassy_mirror": lambda soup: _extract_trs(soup),
    "china_mfa_chinese_original": lambda soup: _extract_mfa_chinese(soup),
}


def extract_paragraphs(content: bytes | str, source_name: str, language: str = "en") -> list[str]:
    # Pass bytes so BeautifulSoup auto-detects encoding from the meta charset tag.
    # Passing a pre-decoded str works too, but can silently garble non-UTF-8 pages
    # (e.g. the Chinese MFA original, which requests mis-detects as ISO-8859-1).
    soup = BeautifulSoup(content, "lxml")
    _strip_boilerplate(soup)
    extractor = _EXTRACTORS.get(source_name)
    if extractor:
        return extractor(soup)
    return _texts_from(soup.body or soup, language)


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def snapshot_path(case_id: str, source_name: str) -> Path:
    return SNAPSHOTS_DIR / f"{case_id}_{source_name}.json"


def save_snapshot(
    case_id: str,
    source_name: str,
    url: str,
    retrieved_at: str,
    language: str,
    paragraphs: list[str],
) -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(case_id, source_name)
    path.write_text(
        json.dumps(
            {"url": url, "retrieved_at": retrieved_at, "language": language, "paragraphs": paragraphs},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_snapshot(case_id: str, source_name: str) -> dict | None:
    path = snapshot_path(case_id, source_name)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Live-first statement loader
# ---------------------------------------------------------------------------

def get_official_source(config: dict, case_id: str, side: str) -> dict:
    """Return the best available statement for one side of a meeting case.

    Tries sources in priority order. A source is accepted as live only when:
      - HTTP 200
      - marker string found in the response body
      - at least one paragraph extracted

    If a live source returns HTTP 200 but the marker is absent, the page may
    have changed since the snapshot was taken. Falls back to snapshots in the
    same priority order. Sets live_changed=True when that path was taken so
    the caller can surface "live page changed or unavailable; showing snapshot".

    Returns an error dict if nothing is available.
    """
    try:
        sources = get_sources_for_side(config, case_id, side)
    except ValueError as e:
        return {"error": str(e)}

    any_live_changed = False

    # Live pass
    for source in sources:
        try:
            resp = fetch_source(source["url"], config)
        except (requests.RequestException, ValueError):
            continue
        if resp.status_code != 200:
            continue
        # Decode as UTF-8 for marker checks; requests sometimes mis-detects
        # the charset of Chinese pages as ISO-8859-1.
        decoded = resp.content.decode("utf-8", errors="replace")
        marker = source.get("marker", "")
        if marker and marker.lower() not in decoded.lower():
            any_live_changed = True
            continue
        lang = source.get("language", "en")
        paragraphs = extract_paragraphs(resp.content, source["name"], lang)
        if not paragraphs:
            continue
        return {
            "case_id": case_id,
            "side": side,
            "source_name": source["name"],
            "url": source["url"],
            "retrieved_at": datetime.now(NY_TZ).isoformat(),
            "live": True,
            "language": lang,
            "paragraphs": paragraphs,
        }

    # Snapshot fallback in same priority order
    for source in sources:
        snap = load_snapshot(case_id, source["name"])
        if snap:
            result = {
                "case_id": case_id,
                "side": side,
                "source_name": source["name"],
                "live": False,
                **snap,
            }
            if any_live_changed:
                result["live_changed"] = True
                result["live_changed_note"] = "live page changed or unavailable; showing snapshot"
            return result

    return {
        "error": (
            f"All live sources failed for {side}/{case_id} and no snapshot exists. "
            "Try again later."
        )
    }


# ---------------------------------------------------------------------------
# Snapshot refresh CLI  (python sources.py --refresh-snapshots)
# ---------------------------------------------------------------------------

def _refresh_snapshots(config: dict) -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    for case_id, case in config["cases"].items():
        if case.get("type") != "meeting":
            continue
        print(f"\n{'='*60}")
        print(f"Case: {case_id}  ({case['name']})")
        print(f"{'='*60}")

        for source in case["sources"]:
            name = source["name"]
            url = source["url"]
            lang = source.get("language", "en")

            print(f"\n  [{name}]")
            print(f"  URL: {url}")

            try:
                resp = fetch_source(url, config)
            except (requests.RequestException, ValueError) as e:
                print(f"  FAILED: {e}")
                continue

            print(f"  HTTP {resp.status_code}  ({len(resp.content):,} bytes)")

            fixture_file = FIXTURES_DIR / f"{name}.html"
            fixture_file.write_bytes(resp.content)
            print(f"  Fixture: {fixture_file}")

            if resp.status_code != 200:
                print(f"  SKIP snapshot: non-200")
                continue

            decoded = resp.content.decode("utf-8", errors="replace")

            marker = source.get("marker", "")
            markers = source.get("markers", [marker] if marker else [])
            for m in markers:
                hit = m.lower() in decoded.lower() if lang == "en" else m in decoded
                print(f"  Marker '{m}': {'FOUND' if hit else 'NOT FOUND'}")

            paragraphs = extract_paragraphs(resp.content, name, lang)
            print(f"  Paragraphs: {len(paragraphs)}")

            if not paragraphs:
                print(f"  SKIP snapshot: no paragraphs extracted")
                continue

            retrieved_at = datetime.now(NY_TZ).isoformat()
            save_snapshot(case_id, name, url, retrieved_at, lang, paragraphs)
            print(f"  Snapshot: {snapshot_path(case_id, name)}")

            p1 = paragraphs[0][:300]
            p2 = paragraphs[1][:300] if len(paragraphs) > 1 else "(only one paragraph)"
            pl = paragraphs[-1][:300]
            print(f"\n  First paragraph:\n    {p1}")
            print(f"\n  Second paragraph:\n    {p2}")
            print(f"\n  Last paragraph:\n    {pl}")


if __name__ == "__main__":
    if "--refresh-snapshots" not in sys.argv:
        print("Usage: python sources.py --refresh-snapshots")
        sys.exit(1)
    _refresh_snapshots(load_config())
