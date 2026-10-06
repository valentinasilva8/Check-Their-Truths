"""claim_check: verify numerical claims from named posts against official sources."""

import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import tomllib

from sources import fetch_source_by_name

_HERE = Path(__file__).parent
CLAIMS_PATH = _HERE / "config" / "claims.toml"


def load_claims(path: Path = CLAIMS_PATH) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalize whitespace, curly quotes, and non-breaking spaces."""
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def _find_paragraph(anchor: str, paragraphs: list[str]) -> str | None:
    """Return the first paragraph containing anchor text after normalization."""
    norm_anchor = _normalize(anchor)
    for para in paragraphs:
        if norm_anchor in _normalize(para):
            return para
    return None


def _extract_sentence(anchor: str, paragraph: str) -> str | None:
    """Return the sentence in paragraph containing anchor, with trailing period."""
    parts = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    norm_anchor = _normalize(anchor)
    for part in parts:
        if norm_anchor in _normalize(part):
            sentence = part.strip()
            if sentence and sentence[-1] not in ".!?":
                sentence += "."
            return sentence
    return None


def _verify_sentence(sentence: str, paragraphs: list[str]) -> bool:
    """True if sentence is a verbatim substring of a paragraph and >= 6 words."""
    norm_s = _normalize(sentence)
    if len(norm_s.split()) < 6:
        return False
    for para in paragraphs:
        if norm_s in _normalize(para):
            return True
    return False


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

def _parse_number(text: str) -> Decimal | None:
    """Parse a number, handling word forms like '20 million' -> 20000000."""
    text = text.strip()
    for word, mult in [
        ("million", Decimal("1000000")),
        ("billion", Decimal("1000000000")),
        ("trillion", Decimal("1000000000000")),
    ]:
        m = re.search(r"([\d,]+)\s+" + word, text, re.IGNORECASE)
        if m:
            return Decimal(m.group(1).replace(",", "")) * mult
    m = re.search(r"[\d,]+(?:\.\d+)?", text.replace(",", ""))
    if m:
        return Decimal(m.group(0))
    return None


def _extract_number(
    anchor: str, regex: str, paragraphs: list[str]
) -> tuple[Decimal | None, str | None]:
    """Find anchor paragraph and extract a number via regex.

    Returns (number, paragraph). Returns (None, None) when anchor is not found.
    Returns (None, paragraph) when anchor is found but regex does not match.
    """
    para = _find_paragraph(anchor, paragraphs)
    if para is None:
        return None, None
    m = re.search(regex, _normalize(para))
    if m:
        return _parse_number(m.group(1)), para
    return None, para


# ---------------------------------------------------------------------------
# Verdict rules (exposed for unit testing)
# ---------------------------------------------------------------------------

def verdict_at_least(official: Decimal, claimed: Decimal) -> str:
    return "supported" if official >= claimed else "contradicted"


def verdict_approximately(official: Decimal, claimed: Decimal) -> tuple[str, Decimal]:
    """Returns (verdict, pct_diff). Denominator is claimed_value (D-34)."""
    pct = (abs(official - claimed) / claimed * Decimal("100")).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    if pct <= Decimal("5"):
        return "supported", pct
    if pct <= Decimal("25"):
        return "imprecise", pct
    return "contradicted", pct


def verdict_direction(claimed_direction: str, before: Decimal, after: Decimal) -> str:
    """Returns supported or contradicted. Zero change is always contradicted (D-31)."""
    change = after - before
    if change == Decimal("0"):
        return "contradicted"
    if claimed_direction == "decrease":
        return "supported" if change < 0 else "contradicted"
    if claimed_direction == "increase":
        return "supported" if change > 0 else "contradicted"
    return "not_checkable"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_info(post: dict) -> dict:
    return {
        "speaker": post.get("speaker"),
        "platform": post.get("platform"),
        "date": post.get("date"),
        "is_excerpt": post.get("is_excerpt", False),
        "text_source": post.get("text_source"),
        "original_url": post.get("original_url"),
    }


def _not_checkable(
    case_id: str,
    claim_id: str,
    claimed_phrase: str,
    post_info: dict,
    claim_type: str | None,
    reason: str,
) -> dict:
    return {
        "case_id": case_id,
        "claim_id": claim_id,
        "claimed_phrase": claimed_phrase,
        "post": post_info,
        "verdict": "not_checkable",
        "rule_applied": claim_type,
        "numbers": {},
        "arithmetic": "",
        "evidence_quote": None,
        "source_name": None,
        "source_url": None,
        "source_date": None,
        "live": None,
        "live_changed": None,
        "reason": reason,
        "context_note": None,
    }


def _build_context_note(claim: dict, paragraphs: list[str]) -> str | None:
    """Extract and verify the context_note sentence (D-39). Returns None on failure."""
    ctx = claim.get("context_note_check")
    if not ctx:
        return None
    anchor = ctx.get("anchor", "")
    if not anchor:
        return None
    para = _find_paragraph(anchor, paragraphs)
    if para is None:
        return None
    sentence = _extract_sentence(anchor, para)
    if sentence is None or not _verify_sentence(sentence, paragraphs):
        return None
    return "CMS also states: " + sentence


# ---------------------------------------------------------------------------
# Per-type claim runners
# ---------------------------------------------------------------------------

def _run_at_least(
    case_id, claim_id, claimed_phrase, post_info, claim, checks,
    paragraphs, source_name, source_url, source_date, live, live_changed,
) -> dict:
    anchor = checks.get("anchor", "")
    regex = checks.get("regex", "")
    claimed_value = Decimal(str(checks.get("claimed_value", 0)))

    official, evidence_para = _extract_number(anchor, regex, paragraphs)
    if official is None:
        return _not_checkable(
            case_id, claim_id, claimed_phrase, post_info, "at_least",
            "anchor sentence not found in source"
            if evidence_para is None
            else "number not found via regex in source paragraph",
        )

    verdict = verdict_at_least(official, claimed_value)
    arithmetic = f"{official:,.0f} >= {claimed_value:,.0f}"
    reason = (
        f"Official count ({official:,.0f}) meets or exceeds claimed count ({claimed_value:,.0f})."
        if verdict == "supported"
        else f"Official count ({official:,.0f}) is less than claimed count ({claimed_value:,.0f})."
    )

    return {
        "case_id": case_id,
        "claim_id": claim_id,
        "claimed_phrase": claimed_phrase,
        "post": post_info,
        "verdict": verdict,
        "rule_applied": f"at_least: official ({official:,.0f}) >= claimed ({claimed_value:,.0f})",
        "numbers": {
            "official": str(int(official)),
            "claimed": str(int(claimed_value)),
        },
        "arithmetic": arithmetic,
        "evidence_quote": evidence_para,
        "source_name": source_name,
        "source_url": source_url,
        "source_date": source_date,
        "live": live,
        "live_changed": live_changed,
        "reason": reason,
        "context_note": None,
    }


def _run_approximately(
    case_id, claim_id, claimed_phrase, post_info, claim, checks,
    paragraphs, source_name, source_url, source_date, live, live_changed,
) -> dict:
    anchor = checks.get("anchor", "")
    regex = checks.get("regex", "")
    claimed_value = Decimal(str(checks.get("claimed_value", "0")))

    official, evidence_para = _extract_number(anchor, regex, paragraphs)
    if official is None:
        return _not_checkable(
            case_id, claim_id, claimed_phrase, post_info, "approximately",
            "anchor sentence not found in source"
            if evidence_para is None
            else "number not found via regex in source paragraph",
        )

    verdict, pct = verdict_approximately(official, claimed_value)
    threshold_desc = (
        "<= 5% -> supported"
        if verdict == "supported"
        else "> 5%, <= 25% -> imprecise"
        if verdict == "imprecise"
        else "> 25% -> contradicted"
    )
    arithmetic = f"|{official} - {claimed_value}| / {claimed_value} = {pct}% ({threshold_desc})"
    reason = (
        f"Official payment (${official}) is {pct}% from claimed (${claimed_value}); "
        f"threshold: <= 5% supported, <= 25% imprecise, > 25% contradicted."
    )

    return {
        "case_id": case_id,
        "claim_id": claim_id,
        "claimed_phrase": claimed_phrase,
        "post": post_info,
        "verdict": verdict,
        "rule_applied": f"approximately: |{official} - {claimed_value}| / {claimed_value} = {pct}%",
        "numbers": {
            "official": str(official),
            "claimed": str(claimed_value),
            "pct_diff": f"{pct}%",
        },
        "arithmetic": arithmetic,
        "evidence_quote": evidence_para,
        "source_name": source_name,
        "source_url": source_url,
        "source_date": source_date,
        "live": live,
        "live_changed": live_changed,
        "reason": reason,
        "context_note": None,
    }


def _run_direction(
    case_id, claim_id, claimed_phrase, post_info, claim, checks,
    paragraphs, source_name, source_url, source_date, live, live_changed,
) -> dict:
    anchor = checks.get("anchor", "")
    regex_before = checks.get("regex_before", "")
    regex_after = checks.get("regex_after", "")
    regex_stated = checks.get("regex_stated_change", "")
    claimed_direction = checks.get("claimed_direction", "")

    before, evidence_para = _extract_number(anchor, regex_before, paragraphs)
    if before is None:
        return _not_checkable(
            case_id, claim_id, claimed_phrase, post_info, "direction",
            "anchor sentence not found in source"
            if evidence_para is None
            else "before value not found via regex in source paragraph",
        )

    after_val, _ = _extract_number(anchor, regex_after, paragraphs)
    if after_val is None:
        return _not_checkable(
            case_id, claim_id, claimed_phrase, post_info, "direction",
            "after value not found via regex in source paragraph",
        )

    stated_change, _ = _extract_number(anchor, regex_stated, paragraphs)
    if stated_change is None:
        return _not_checkable(
            case_id, claim_id, claimed_phrase, post_info, "direction",
            "stated change not found via regex in source paragraph",
        )

    # Cross-check: computed change must equal stated change (D-35)
    computed = (after_val - before).quantize(Decimal("0.01"))
    stated = stated_change.quantize(Decimal("0.01"))
    if computed != stated:
        return _not_checkable(
            case_id, claim_id, claimed_phrase, post_info, "direction",
            f"stated and computed changes do not match: computed {computed}, stated {stated}",
        )

    verdict = verdict_direction(claimed_direction, before, after_val)

    # Derived numbers
    monthly_change = computed  # signed
    abs_monthly = abs(monthly_change)
    pct = (abs_monthly / before * Decimal("100")).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    annual = (abs_monthly * 12).quantize(Decimal("0.01"))

    sign = "+" if monthly_change >= 0 else ""
    monthly_str = f"{sign}{monthly_change}"
    pct_str = f"{sign}{pct}%"
    annual_str = str(annual)

    direction_desc = (
        "increase" if monthly_change > 0
        else "decrease" if monthly_change < 0
        else "no change"
    )
    arithmetic = (
        f"{after_val} - {before} = {monthly_str} "
        f"({pct_str} per month, {sign}{annual_str} per year)"
    )
    reason = (
        f"The Part B monthly premium {direction_desc}d from ${before} to ${after_val}. "
        f"The claim that premiums were {claimed_direction}d is "
        f"{'supported' if verdict == 'supported' else 'contradicted'}."
    )

    context_note = _build_context_note(claim, paragraphs)

    return {
        "case_id": case_id,
        "claim_id": claim_id,
        "claimed_phrase": claimed_phrase,
        "post": post_info,
        "verdict": verdict,
        "rule_applied": (
            f"direction: claimed_direction={claimed_direction}; "
            f"actual change={monthly_str} ({direction_desc})"
        ),
        "numbers": {
            "2025_premium": str(before),
            "2026_premium": str(after_val),
            "monthly_change": monthly_str,
            "pct_change": pct_str,
            "annual_change": annual_str,
        },
        "arithmetic": arithmetic,
        "evidence_quote": evidence_para,
        "source_name": source_name,
        "source_url": source_url,
        "source_date": source_date,
        "live": live,
        "live_changed": live_changed,
        "reason": reason,
        "context_note": context_note,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def check_claim(config: dict, claims: dict, case_id: str, claim_id: str) -> dict:
    """Verify a specific claim against an official source. Returns a result dict (never raises)."""
    case = config["cases"].get(case_id)
    if not case:
        return {"error": f"Case '{case_id}' not found. Call list_cases to see supported cases."}
    if case.get("type") != "claim_check":
        return {
            "error": (
                f"check_claim requires a claim_check case; "
                f"'{case_id}' is type '{case.get('type')}'. "
                "Use compare_statements for meeting cases."
            )
        }

    case_claims = claims.get("claims", {}).get(case_id, {})
    claim = case_claims.get(claim_id)
    if not claim:
        return {"error": f"Claim '{claim_id}' not found in case '{case_id}'."}

    post_id = claim.get("post")
    post = claims.get("posts", {}).get(post_id)
    if not post:
        return {"error": f"Post '{post_id}' not found in claims.toml."}

    claimed_phrase = claim.get("claimed_phrase", "")
    post_info = _post_info(post)
    claim_type = claim.get("claim_type")

    if claimed_phrase not in post.get("verbatim_text", ""):
        return _not_checkable(
            case_id, claim_id, claimed_phrase, post_info, claim_type,
            "claimed_phrase not found in post text",
        )

    checks = claim.get("checks", {})
    source_name = checks.get("source")
    source_result = fetch_source_by_name(config, case_id, source_name)
    if "error" in source_result:
        return {"error": f"Could not fetch source '{source_name}': {source_result['error']}"}

    paragraphs = source_result["paragraphs"]
    source_url = source_result.get("url", "")
    live = source_result.get("live", False)
    live_changed = source_result.get("live_changed", False)
    source_date = source_result.get("retrieved_at", "")[:10]

    shared = (
        case_id, claim_id, claimed_phrase, post_info, claim, checks,
        paragraphs, source_name, source_url, source_date, live, live_changed,
    )
    if claim_type == "at_least":
        return _run_at_least(*shared)
    if claim_type == "approximately":
        return _run_approximately(*shared)
    if claim_type == "direction":
        return _run_direction(*shared)
    return {"error": f"Unknown claim_type '{claim_type}' for claim '{claim_id}'."}
