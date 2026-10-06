"""compare_statements: fetch both sides, model-compare, quote-verify, cache."""

import hashlib
import json
import re

import litellm

from sources import get_official_source, load_snapshot

PROMPT_VERSION = "3"

MAX_ROWS = 12

_cache: dict = {}

_AI_TOPIC_TERMS = frozenset({
    "ai",
    "artificial intelligence",
    "super intelligence",
    "superintelligence",
    "intelligence",
})


def _normalize(text: str) -> str:
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def _verify_quote(quote: str, paragraphs: list[str]) -> bool:
    """Exact substring in any paragraph, after normalization, at least 6 words."""
    norm_q = _normalize(quote)
    if len(norm_q.split()) < 6:
        return False
    for para in paragraphs:
        if norm_q in _normalize(para):
            return True
    return False


def _is_ai_topic(topic: str) -> bool:
    """True when topic is empty (compare-all) or contains an AI-related term."""
    t = topic.strip().lower()
    if t == "":
        return True
    return any(term in t for term in _AI_TOPIC_TERMS)


def _text_hash(paragraphs: list[str]) -> str:
    return hashlib.sha256("\n".join(paragraphs).encode()).hexdigest()


def _chinese_term_check(case_id: str) -> dict | None:
    """Check the Chinese original for 人工智能 and 超级智能. No model call."""
    snapshot = load_snapshot(case_id, "china_mfa_chinese_original")
    if not snapshot:
        return None
    combined = "".join(snapshot["paragraphs"])
    has_rengong = "人工智能" in combined
    has_chaoji = "超级智能" in combined
    return {
        "label": "term_check",
        "topic": "chinese_term_check",
        "reason": (
            f"Chinese original contains 人工智能 (artificial intelligence): "
            f"{'yes' if has_rengong else 'no'}. "
            f"Contains 超级智能 (super intelligence): "
            f"{'yes' if has_chaoji else 'no'}."
        ),
        "left_quote": None,
        "right_quote": None,
        "left_url": None,
        "right_url": None,
        "attributed_to": None,
    }


def _build_prompt(
    topic: str,
    left: str,
    right: str,
    left_paras: list[str],
    right_paras: list[str],
) -> str:
    topic_desc = f'"{topic}"' if topic.strip() else "all topics"
    left_text = "\n\n".join(left_paras)
    right_text = "\n\n".join(right_paras)
    return (
        "You are comparing two official statements. "
        "Return ONLY a JSON array of comparison rows. No other text.\n\n"
        f"Topic: {topic_desc}\n\n"
        f"LEFT SIDE ({left}):\n{left_text}\n\n"
        f"RIGHT SIDE ({right}):\n{right_text}\n\n"
        f"Return at most {MAX_ROWS + 3} rows. "
        "Each row must be a JSON object with exactly these fields:\n"
        '- "topic": string, subject in 1-4 words\n'
        f'- "label": one of "same", "different_framing", "contradiction", "only_{left}", "only_{right}"\n'
        '- "reason": one sentence explaining the label\n'
        f'- "left_quote": verbatim quote from the LEFT text (null if label is "only_{right}")\n'
        f'- "right_quote": verbatim quote from the RIGHT text (null if label is "only_{left}")\n\n'
        "Quotes must be copied character-for-character. Do not paraphrase or change any character.\n"
        'For "same", "different_framing", "contradiction": both quotes required.\n'
        f'For "only_{left}": left_quote required, right_quote must be null.\n'
        f'For "only_{right}": right_quote required, left_quote must be null.\n\n'
        'STRICT RULE for "contradiction": use it ONLY when both sides make explicit, '
        "incompatible factual claims about the same thing -- claims that cannot both be true. "
        "Different terms for the same concept, differences in emphasis, and one side not "
        'mentioning something are NEVER contradiction. Use "different_framing" when both '
        'sides address a topic but with different language or focus. Use "only_{left}" or '
        '"only_{right}" when only one side mentions the topic.\n\n'
        "PAIRING RULE: A row may only pair two quotes that address the same specific item "
        "or commitment. If each side mentions a different item under the same broad topic, "
        f'return separate "only_{left}" and "only_{right}" rows instead of a single '
        '"different_framing" row.'
    )


def compare_statements(
    config: dict,
    case_id: str,
    topic: str,
    left: str,
    right: str,
) -> dict:
    """Compare two sides of a meeting case. Returns a result dict (never raises)."""
    case = config["cases"].get(case_id)
    if not case:
        return {"error": f"Case '{case_id}' not found. Call list_cases to see supported cases."}
    if case.get("type") != "meeting":
        return {
            "error": (
                f"compare_statements requires a meeting case; "
                f"'{case_id}' is type '{case.get('type')}'."
            )
        }

    if "press" in (left, right):
        return {"error": "press side not available yet"}

    for side_name, side_val in (("left", left), ("right", right)):
        if side_val not in ("us", "china"):
            return {"error": f"{side_name} must be 'us', 'china', or 'press', got '{side_val}'."}

    left_result = get_official_source(config, case_id, left)
    if "error" in left_result:
        return {"error": f"Could not load {left} statement: {left_result['error']}"}
    right_result = get_official_source(config, case_id, right)
    if "error" in right_result:
        return {"error": f"Could not load {right} statement: {right_result['error']}"}

    left_paras: list[str] = left_result["paragraphs"]
    right_paras: list[str] = right_result["paragraphs"]

    topic_norm = topic.strip().lower()
    text_hash = _text_hash(left_paras + right_paras)
    cache_key = (case_id, topic_norm, left, right, PROMPT_VERSION, text_hash)
    if cache_key in _cache:
        return _cache[cache_key]

    prompt = _build_prompt(topic, left, right, left_paras, right_paras)

    try:
        reply = litellm.completion(
            model="vertex_ai/gemini-3.5-flash-lite",
            vertex_location="global",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = reply.choices[0].message.content
    except Exception as e:
        return {"error": f"Model call failed: {type(e).__name__}: {str(e)[:300]}"}

    # Strip markdown fences if the model wraps the JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        raw_rows = json.loads(raw)
        if not isinstance(raw_rows, list):
            raise ValueError("expected a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        return {"error": f"Model returned invalid JSON: {e}. Raw response: {raw[:200]!r}"}

    valid_labels = {
        "same",
        "different_framing",
        "contradiction",
        f"only_{left}",
        f"only_{right}",
    }
    both_required = {"same", "different_framing", "contradiction"}

    all_verified: list[dict] = []
    dropped_count = 0
    drop_reasons: list[str] = []

    for i, row in enumerate(raw_rows):
        tag = f"row {i + 1} (topic={row.get('topic', '?')!r})"

        label = row.get("label", "")
        reason = (row.get("reason") or "").strip()
        left_quote = row.get("left_quote") or None
        right_quote = row.get("right_quote") or None

        if label not in valid_labels:
            drop_reasons.append(
                f"{tag}: invalid label {label!r}; must be one of {sorted(valid_labels)}"
            )
            dropped_count += 1
            continue
        if not reason:
            drop_reasons.append(f"{tag}: empty reason")
            dropped_count += 1
            continue
        if label in both_required:
            if not left_quote or not right_quote:
                drop_reasons.append(
                    f"{tag}: label {label!r} requires both left_quote and right_quote"
                )
                dropped_count += 1
                continue
        elif label == f"only_{left}":
            if not left_quote:
                drop_reasons.append(f"{tag}: label 'only_{left}' requires left_quote")
                dropped_count += 1
                continue
        elif label == f"only_{right}":
            if not right_quote:
                drop_reasons.append(f"{tag}: label 'only_{right}' requires right_quote")
                dropped_count += 1
                continue

        quote_ok = True
        if left_quote is not None:
            if not _verify_quote(left_quote, left_paras):
                drop_reasons.append(
                    f"{tag}: left_quote failed verification "
                    f"(not in source or < 6 words): {left_quote[:80]!r}"
                )
                quote_ok = False
        if right_quote is not None:
            if not _verify_quote(right_quote, right_paras):
                drop_reasons.append(
                    f"{tag}: right_quote failed verification "
                    f"(not in source or < 6 words): {right_quote[:80]!r}"
                )
                quote_ok = False
        if not quote_ok:
            dropped_count += 1
            continue

        all_verified.append({
            "label": label,
            "topic": row.get("topic", ""),
            "reason": reason,
            "left_quote": left_quote,
            "right_quote": right_quote,
            "left_url": left_result.get("url"),
            "right_url": right_result.get("url"),
            "attributed_to": None,
        })

    cap_hit = len(all_verified) > MAX_ROWS
    verified_rows = all_verified[:MAX_ROWS]

    if "china" in (left, right) and _is_ai_topic(topic):
        term_row = _chinese_term_check(case_id)
        if term_row:
            verified_rows.append(term_row)

    result = {
        "case_id": case_id,
        "topic": topic,
        "left": left,
        "right": right,
        "rows": verified_rows,
        "dropped": dropped_count,
        "drop_reasons": drop_reasons,
        "cap_hit": cap_hit,
    }
    _cache[cache_key] = result
    return result
