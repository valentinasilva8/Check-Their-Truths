"""Guardian press coverage.

Full article text stays in memory and expires after 23 hours. The citation
file stores a hash of each verified quote, never the quote text. It is written
only by `python press.py --save-citations` and is not a fallback.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from sources import FETCH_TIMEOUT, NY_TZ, USER_AGENT, load_config, load_secrets

_HERE = Path(__file__).parent
CITATIONS_DIR = _HERE / "data" / "press_citations"

MAX_CITATION_WORDS = 40
PRESS_CACHE_SECONDS = 23 * 60 * 60

# Letters and digits, with a straight or curly apostrophe inside a word.
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['\u2019][A-Za-z0-9]+)*")

# In-memory only. Values are (stored_at, result). Never written by get_press_coverage.
_cache: dict = {}

UNAVAILABLE = "press side unavailable"

# Topics recorded by the explicit citation command. Not read back at runtime.
CITATION_TOPICS = ("", "AI naming", "taiwan", "weapons")
CITATION_PAIRS = (("us", "press"), ("china", "press"))

_CITATION_REQUIRED = (
    "url",
    "headline",
    "byline",
    "paragraph_id",
    "published",
    "retrieved_at",
    "quote_sha256",
)


def _word_key(token: str) -> str:
    return token.replace("\u2019", "'").casefold()


def _word_spans(text: str) -> list[tuple[str, int, int]]:
    return [(_word_key(match.group(0)), match.start(), match.end()) for match in _WORD_RE.finditer(text or "")]


def quote_word_count(text: str) -> int:
    """Count words after punctuation is removed. Ellipsis is not a word."""
    return len(_word_spans(text))


def press_word_count(text: str) -> int:
    return quote_word_count(text)


def match_press_span(model_quote: str, paragraph: str) -> str | None:
    """Return the exact source substring whose words match, or None.

    Words are compared with punctuation removed, in the same order.
    The returned text is the source paragraph's own characters.
    """
    wanted = [word for word, _, _ in _word_spans(model_quote)]
    if len(wanted) < 6 or len(wanted) > MAX_CITATION_WORDS:
        return None
    source = _word_spans(paragraph)
    source_words = [word for word, _, _ in source]
    last = len(source_words) - len(wanted) + 1
    for start in range(max(last, 0)):
        if source_words[start:start + len(wanted)] == wanted:
            char_start = source[start][1]
            char_end = source[start + len(wanted) - 1][2]
            return paragraph[char_start:char_end]
    return None


def quote_sha256(quote: str) -> str:
    return hashlib.sha256(quote.encode("utf-8")).hexdigest()


def paragraph_has_quote_hash(paragraph: str, digest: str) -> bool:
    """True when some 6-40 word span of the paragraph hashes to digest."""
    spans = _word_spans(paragraph)
    for length in range(6, MAX_CITATION_WORDS + 1):
        for start in range(0, len(spans) - length + 1):
            snippet = paragraph[spans[start][1]:spans[start + length - 1][2]]
            if quote_sha256(snippet) == digest:
                return True
    return False


def _now() -> float:
    return time.time()


def _cache_get(key: tuple):
    item = _cache.get(key)
    if item is None:
        return None
    stored_at, value = item
    if _now() - stored_at > PRESS_CACHE_SECONDS:
        _cache.pop(key, None)
        return None
    return value


def citation_record_errors(data: dict) -> list[str]:
    """Return errors for a citation record. Empty list means the record is valid.

    The record must not contain Guardian quote text. A quote field is an error.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["citation record must be a JSON object"]
    citations = data.get("citations")
    if not isinstance(citations, list):
        return ["citation record is missing a citations list"]
    for index, entry in enumerate(citations):
        tag = f"citation {index + 1}"
        if not isinstance(entry, dict):
            errors.append(f"{tag}: entry is not an object")
            continue
        if "quote" in entry:
            errors.append(f"{tag}: quote text must not be stored")
        unexpected = sorted(set(entry) - set(_CITATION_REQUIRED) - {"attributed_to"})
        if unexpected:
            errors.append(f"{tag}: unexpected fields {unexpected}")
        for field in _CITATION_REQUIRED:
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{tag}: missing {field}")
        if "attributed_to" not in entry:
            errors.append(f"{tag}: missing attributed_to")
        elif entry.get("attributed_to") is not None and not isinstance(entry.get("attributed_to"), str):
            errors.append(f"{tag}: attributed_to must be a string or null")
        digest = entry.get("quote_sha256")
        if isinstance(digest, str) and not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"{tag}: quote_sha256 is not a sha256 hex digest")
    return errors


def _unavailable(reason: str | None = None) -> dict:
    """Stable error for the model. reason is for logs in tests, not the API key."""
    result = {"error": UNAVAILABLE}
    if reason:
        result["reason"] = reason
    return result


def _load_api_key() -> str | None:
    try:
        secrets = load_secrets()
    except (OSError, tomllib.TOMLDecodeError):
        return None
    key = secrets.get("guardian_api_key") if isinstance(secrets, dict) else None
    if not isinstance(key, str) or not key.strip():
        return None
    return key


def _extract_paragraphs(body_html: str) -> list[str]:
    soup = BeautifulSoup(body_html or "", "lxml")
    paragraphs = []
    for node in soup.find_all("p"):
        text = node.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)
    return paragraphs


def _fetch_article(content_api: str, article_id: str, show_fields: str, api_key: str) -> dict | None:
    """Fetch one curated article. Returns None on any failure. Never raises."""
    url = content_api.rstrip("/") + "/" + article_id.lstrip("/")
    try:
        response = requests.get(
            url,
            params={"show-fields": show_fields, "api-key": api_key},
            headers={"User-Agent": USER_AGENT},
            timeout=FETCH_TIMEOUT,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    content = (payload.get("response") or {}).get("content") or {}
    fields = content.get("fields") or {}
    body = fields.get("body") or ""
    paragraphs = _extract_paragraphs(body)
    if not paragraphs:
        return None
    return {
        "article_id": content.get("id") or article_id,
        "type": content.get("type") or "",
        "headline": fields.get("headline") or "",
        "byline": (fields.get("byline") or "").strip(),
        "url": content.get("webUrl") or "",
        "published": content.get("webPublicationDate") or "",
        "paragraphs": paragraphs,
    }


def get_press_coverage(config: dict, case_id: str, *, refresh: bool = False) -> dict:
    """Fetch curated Guardian articles for a meeting case. In-memory cache only."""
    case = config["cases"].get(case_id)
    if not case:
        return {"error": f"Case '{case_id}' not found. Call list_cases to see supported cases."}
    if case.get("type") != "meeting":
        return {
            "error": (
                f"get_press_coverage requires a meeting case; "
                f"'{case_id}' is type '{case.get('type')}'."
            )
        }
    article_ids = list(case.get("press_articles") or [])
    if not article_ids:
        return _unavailable("no curated articles")

    guardian = config.get("guardian") or {}
    content_api = guardian.get("content_api")
    show_fields = guardian.get("show_fields")
    if not content_api or not show_fields:
        return _unavailable("guardian settings missing from config")

    cache_key = (case_id, tuple(article_ids))
    if not refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    api_key = _load_api_key()
    if not api_key:
        return _unavailable("secrets file unavailable")

    articles = []
    for index, article_id in enumerate(article_ids, start=1):
        fetched = _fetch_article(content_api, article_id, show_fields, api_key)
        if fetched is None:
            return _unavailable("article fetch failed")
        if fetched["type"] == "liveblog":
            continue
        label = f"A{index}"
        numbered = [
            {"id": f"{label}-P{paragraph_index}", "text": text}
            for paragraph_index, text in enumerate(fetched["paragraphs"], start=1)
        ]
        articles.append({
            "article_id": fetched["article_id"],
            "headline": fetched["headline"],
            "byline": fetched["byline"],
            "url": fetched["url"],
            "published": fetched["published"],
            "paragraphs": numbered,
        })

    if not articles:
        return _unavailable("no articles after liveblog exclusion")

    result = {"case_id": case_id, "side": "press", "articles": articles}
    _cache[cache_key] = (_now(), result)
    return result


def flatten_paragraphs(press_result: dict) -> list[dict]:
    """One record per paragraph, with the article citation fields copied on."""
    flat = []
    for article in press_result.get("articles") or []:
        for paragraph in article.get("paragraphs") or []:
            flat.append({
                "id": paragraph["id"],
                "text": paragraph["text"],
                "article_id": article.get("article_id"),
                "headline": article.get("headline"),
                "byline": article.get("byline"),
                "url": article.get("url"),
                "published": article.get("published"),
            })
    return flat


def _press_lookup(press_result: dict) -> dict:
    return {paragraph["id"]: paragraph for paragraph in flatten_paragraphs(press_result)}


def save_citations(config: dict, case_id: str, dest: Path | None = None) -> dict:
    """Write a content-free hash record of verified press quotes.

    compare_statements does not call this, and does not read the file back.
    The quote text is hashed and then discarded. It is not written.
    """
    from compare import compare_statements

    press_result = get_press_coverage(config, case_id)
    if "error" in press_result:
        return press_result
    lookup = _press_lookup(press_result)
    retrieved_at = datetime.now(NY_TZ).isoformat()

    seen: set[tuple] = set()
    citations: list[dict] = []
    for topic in CITATION_TOPICS:
        for left, right in CITATION_PAIRS:
            result = compare_statements(config, case_id, topic, left, right)
            if "error" in result:
                return {"error": f"compare_statements failed for {left} vs {right} topic {topic!r}: {result['error']}"}
            for row in result.get("rows") or []:
                if row.get("label") == "term_check":
                    continue
                for side_name in (left, right):
                    if side_name != "press":
                        continue
                    prefix = "left" if side_name == left else "right"
                    quote = row.get(f"{prefix}_quote")
                    paragraph_id = row.get(f"{prefix}_paragraph_id")
                    if not quote or not paragraph_id:
                        continue
                    meta = lookup.get(paragraph_id)
                    if not meta:
                        continue
                    if quote_word_count(quote) > MAX_CITATION_WORDS:
                        return {"error": f"refusing to store a hash of a span over {MAX_CITATION_WORDS} words"}
                    if quote not in (meta.get("text") or ""):
                        return {"error": f"refusing to hash a quote that is not an exact span of {paragraph_id}"}
                    digest = quote_sha256(quote)
                    key = (paragraph_id, digest, row.get("attributed_to"))
                    if key in seen:
                        continue
                    seen.add(key)
                    citations.append({
                        "url": meta.get("url"),
                        "headline": meta.get("headline"),
                        "byline": meta.get("byline"),
                        "paragraph_id": paragraph_id,
                        "published": meta.get("published"),
                        "retrieved_at": retrieved_at,
                        "attributed_to": row.get("attributed_to"),
                        "quote_sha256": digest,
                    })

    citations.sort(key=lambda entry: (entry["paragraph_id"], entry["quote_sha256"]))
    payload = {"case_id": case_id, "citations": citations}
    errors = citation_record_errors(payload)
    if errors:
        return {"error": "citation record failed validation: " + "; ".join(errors)}

    path = dest or (CITATIONS_DIR / f"{case_id}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"path": str(path), "count": len(citations)}


def verify_citations(config: dict, case_id: str, path: Path | None = None) -> dict:
    """Re-fetch the articles and confirm each stored hash is still in its paragraph."""
    path = path or (CITATIONS_DIR / f"{case_id}.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"error": f"could not read citation record: {exc}"}
    errors = citation_record_errors(data)
    if errors:
        return {"error": "citation record failed validation: " + "; ".join(errors)}

    press_result = get_press_coverage(config, case_id, refresh=True)
    if "error" in press_result:
        return press_result
    lookup = _press_lookup(press_result)

    mismatches: list[str] = []
    for index, entry in enumerate(data["citations"], start=1):
        paragraph = lookup.get(entry["paragraph_id"])
        if paragraph is None:
            mismatches.append(f"citation {index}: paragraph {entry['paragraph_id']} not in the re-fetched article")
            continue
        if paragraph.get("url") != entry.get("url"):
            mismatches.append(f"citation {index}: url does not match the re-fetched article")
            continue
        if not paragraph_has_quote_hash(paragraph.get("text") or "", entry["quote_sha256"]):
            mismatches.append(
                f"citation {index}: hash does not match a span of {entry['paragraph_id']}"
            )
    return {
        "path": str(path),
        "checked": len(data["citations"]),
        "ok": not mismatches,
        "mismatches": mismatches,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write or check the press citation record.")
    parser.add_argument("--save-citations", action="store_true")
    parser.add_argument("--verify-citations", action="store_true")
    parser.add_argument("--case-id", default="washington_2026_09")
    args = parser.parse_args(argv)
    if args.save_citations == args.verify_citations:
        parser.error("pass exactly one of --save-citations or --verify-citations")
    config = load_config()
    if args.verify_citations:
        result = verify_citations(config, args.case_id)
        if "error" in result:
            print(result["error"], file=sys.stderr)
            return 1
        if not result["ok"]:
            print("\n".join(result["mismatches"]), file=sys.stderr)
            return 1
        print(f"Verified {result['checked']} citation hashes in {result['path']}")
        return 0
    result = save_citations(config, args.case_id)
    if "error" in result:
        print(result["error"], file=sys.stderr)
        return 1
    print(f"Wrote {result['count']} citation hashes to {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
