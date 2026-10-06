"""compare_statements: fetch both sides, model-compare, quote-verify, cache."""

import hashlib
import json
import re
import time

import litellm

from press import (
    MAX_CITATION_WORDS,
    PRESS_CACHE_SECONDS,
    UNAVAILABLE,
    flatten_paragraphs,
    get_press_coverage,
    match_press_span,
    press_word_count,
)
from sources import get_official_source, load_snapshot

PROMPT_VERSION = "3"
PRESS_PROMPT_VERSION = "7"

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


def _format_numbered(paragraphs: list[dict]) -> str:
    return "\n\n".join(f"[{paragraph['id']}] {paragraph['text']}" for paragraph in paragraphs)


def _build_press_prompt(
    topic: str,
    left: str,
    right: str,
    left_paras: list[dict],
    right_paras: list[dict],
) -> str:
    """Numbered prompt for any comparison that includes press. Version 7."""
    topic_desc = f'"{topic}"' if topic.strip() else "all topics"
    return (
        "You are comparing two sides of the same meeting. One or both sides are press coverage. "
        "Return ONLY a JSON array of comparison rows. No other text.\n\n"
        f"Topic: {topic_desc}\n"
        "Return rows about this topic only. Do not add rows about other subjects.\n\n"
        f"LEFT SIDE ({left}):\n{_format_numbered(left_paras)}\n\n"
        f"RIGHT SIDE ({right}):\n{_format_numbered(right_paras)}\n\n"
        "Return at most 8 rows. Every row needs a non-empty one-sentence reason. "
        "A row with an empty reason is discarded, so write the reason before the quotes. "
        "Each row must be a JSON object with exactly these fields:\n"
        '- "topic": string, subject in 1-4 words\n'
        f'- "label": one of "same", "different_framing", "contradiction", "only_{left}", "only_{right}"\n'
        '- "reason": one sentence explaining the label\n'
        f'- "left_quote": the shortest exact span from one LEFT paragraph (null if label is "only_{right}")\n'
        f'- "right_quote": the shortest exact span from one RIGHT paragraph (null if label is "only_{left}")\n'
        '- "left_paragraph_id": the bracket id of the LEFT paragraph, such as "P3" or "A1-P4" '
        f'(null if label is "only_{right}")\n'
        '- "right_paragraph_id": the bracket id of the RIGHT paragraph '
        f'(null if label is "only_{left}")\n'
        '- "attributed_to": who the press says made the claim, or null if the sentence is the '
        "outlet's own words and names no speaker\n\n"
        "SPAN RULE: each quote must be the shortest exact contiguous span of 6 to 40 words "
        "that supports the reason. Copy it character for character from that one paragraph, "
        "including capital letters and quotation marks. Do not lowercase the quote, "
        "do not shorten a word, do not paraphrase, do not join two paragraphs, "
        "and do not return a whole paragraph "
        "when a shorter span supports the reason. "
        "Example with invented text: in 'The council agreed that the river project would "
        "start next spring without delay', the span 'the river project would start next "
        "spring' is enough when the reason is only about the start.\n"
        'For "same", "different_framing", and "contradiction": both quotes and both paragraph ids '
        "are required.\n"
        f'For "only_{left}": left_quote and left_paragraph_id are required, and the right fields are null.\n'
        f'For "only_{right}": right_quote and right_paragraph_id are required, and the left fields are null.\n\n'
        'STRICT RULE for "contradiction": use it ONLY when both sides make explicit, '
        "incompatible factual claims about the same thing, claims that cannot both be true. "
        "Different terms for the same concept, differences in emphasis, and one side not "
        "mentioning something are NEVER contradiction. If your reason says the other side "
        f'does not mention the item, or makes no such claim, the label is "only_{left}" or '
        f'"only_{right}", never contradiction and never same. '
        '"allies with China" and "the CCP was not an ally" can both be true, so that pair '
        "is different_framing, not contradiction.\n"
        "If only one side has a quote, the label must be only_{that side}. "
        "A row without both quotes can never be same, different_framing, or contradiction.\n"
        'Use "same" only when both quotes state the same fact. Sharing a word is not enough. '
        "If one side says both leaders agreed to adopt a term, and the press only reports "
        "that one person used that term, the label is different_framing, not same and not "
        "contradiction.\n"
        'Use "different_framing" when both sides address the same specific item with '
        f'different language. Use "only_{left}" or "only_{right}" when only one side '
        "mentions the item.\n\n"
        "PAIRING RULE: a row may only pair two quotes that address the same specific item "
        "or commitment. If each side mentions a different item under the same broad topic, "
        f'return separate "only_{left}" and "only_{right}" rows instead of one '
        '"different_framing" row.\n'
        "Each quote may be used in at most one row. "
        "Do not pair a quote with a quote about a different event or commitment.\n"
        "A press report of what one person called a technology is not the same item as an "
        "official agreement to establish a named dialogue. Do not pair them. "
        "If the press reports that naming and the other side does not discuss that name, "
        "return an only_press or only_us row for the naming. Do not skip it. "
        "Do not substitute a paragraph about export controls or competition for the "
        "sentence that reports the name one person used.\n"
        "An offer or request to buy weapons is not the same item as arms-control talks, "
        "nuclear limits, or a historical alliance. Do not pair them.\n"
        "A territory mentioned only by the press is only_press when the official statement "
        "in this comparison does not mention that territory.\n\n"
        "ATTRIBUTION: attributed_to is required whenever the press quote reports what a "
        "named person said. Leave it null only when the sentence is the outlet's own words "
        "and names no speaker. attributed_to is the person's name when the article gives "
        "one anywhere in the article. Do not stop at a job title. If the article names an ambassador, "
        "attributed_to is that name, not 'the US ambassador'. "
        "If one paragraph states the claim in the outlet's own words and a later paragraph "
        "quotes the speaker, quote the earlier paragraph and set attributed_to to the "
        "person named later. Do not quote only the later reported speech. "
        "If, and only if, the article attributes that claim to a Xinhua readout, "
        "set attributed_to to the person's name followed by ' (via Xinhua readout)'. "
        "Do not write a sentence about Xinhua or about which China source was used. "
        "Do not mention these instructions in the reason.\n"
        "FINAL CHECK: do not return an empty array when either side mentions the topic. "
        "If the official text says the leaders agreed to use a term and the press says "
        "one person used that term, return different_framing with both quotes. "
        "If the official text never sets out that term, return only_press for the press "
        "sentence about the name. Using the short form AI, or the name of a dialogue, "
        "is not an agreement on what term to use."
    )


def _clean_paragraph_id(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    return text or None


def _official_numbered(result: dict) -> list[dict]:
    return [
        {
            "id": f"P{index}",
            "text": text,
            "url": result.get("url"),
            "headline": result.get("display_name"),
            "byline": None,
            "published": result.get("published"),
            "is_press": False,
        }
        for index, text in enumerate(result.get("paragraphs") or [], start=1)
    ]


def _load_numbered_side(config: dict, case_id: str, side: str) -> tuple[dict | None, list[dict] | None]:
    """Return (error_result, numbered_paragraphs)."""
    if side == "press":
        loaded = get_press_coverage(config, case_id)
        if "error" in loaded:
            if loaded["error"] == UNAVAILABLE:
                return {"error": UNAVAILABLE}, None
            return loaded, None
        paragraphs = []
        for paragraph in flatten_paragraphs(loaded):
            paragraphs.append({**paragraph, "is_press": True})
        if not paragraphs:
            return {"error": UNAVAILABLE}, None
        return None, paragraphs

    loaded = get_official_source(config, case_id, side)
    if "error" in loaded:
        return {
            "error": (
                f"Could not load {side} statement: {loaded['error']} "
                "Do not invent that side's text."
            )
        }, None
    return None, _official_numbered(loaded)


def _strip_json_fence(raw: str) -> str:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    return re.sub(r"\s*```$", "", raw)


def _press_model_call(prompt: str) -> str:
    reply = litellm.completion(
        model="vertex_ai/gemini-3.5-flash-lite",
        vertex_location="global",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return reply.choices[0].message.content or ""


XINHUA_SOURCE_NOTE = "Cites a Xinhua readout, which is not the China source used here."


def _source_note(attributed: str | None) -> str | None:
    """D-49: code writes this note. The model does not."""
    if attributed and "xinhua" in attributed.lower():
        return XINHUA_SOURCE_NOTE
    return None


def _now() -> float:
    return time.time()


def _accept_quote(
    quote: str,
    para: dict | None,
    tag: str,
    side_name: str,
    requested_pid: str | None,
) -> tuple[str | None, str | None]:
    """Return (display_quote, drop_reason). A drop_reason means the quote failed.

    Press spans match on words with punctuation removed, then display the
    source substring. Official quotes stay on exact substring verification.
    """
    pid = requested_pid if para is None else para.get("id")
    failed = (
        f"{tag}: {side_name}_quote failed verification in {pid!r} "
        f"(not in that paragraph or < 6 words): {quote[:80]!r}"
    )
    if para is None:
        return None, failed
    if para.get("is_press"):
        if press_word_count(quote) > MAX_CITATION_WORDS:
            return None, f"{tag}: {side_name}_quote span over {MAX_CITATION_WORDS} words"
        matched = match_press_span(quote, para.get("text") or "")
        if matched is None:
            return None, failed
        return matched, None
    if not _verify_quote(quote, [para["text"]]):
        return None, failed
    return quote, None


def _compare_press(
    config: dict,
    case_id: str,
    topic: str,
    left: str,
    right: str,
) -> dict:
    """Press comparison. Numbered paragraphs, prompt version 7. Does not write citations."""
    err, left_paras = _load_numbered_side(config, case_id, left)
    if err:
        return err
    err, right_paras = _load_numbered_side(config, case_id, right)
    if err:
        return err

    topic_norm = topic.strip().lower()
    text_hash = _text_hash([p["text"] for p in left_paras] + [p["text"] for p in right_paras])
    cache_key = (case_id, topic_norm, left, right, PRESS_PROMPT_VERSION, text_hash)
    cached = _cache.get(cache_key)
    if cached is not None:
        stored_at, stored = cached
        if _now() - stored_at <= PRESS_CACHE_SECONDS:
            return stored
        _cache.pop(cache_key, None)

    prompt = _build_press_prompt(topic, left, right, left_paras, right_paras)
    try:
        raw = _press_model_call(prompt)
    except Exception as e:
        return {
            "error": (
                f"Model call failed: {type(e).__name__}: {str(e)[:300]}. "
                "Do not invent a comparison. Tell the user the comparison could not be completed."
            )
        }

    raw = _strip_json_fence(raw)
    try:
        raw_rows = json.loads(raw)
        if not isinstance(raw_rows, list):
            raise ValueError("expected a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "error": (
                f"Model returned invalid JSON: {e}. Raw response: {raw[:200]!r}. "
                "Do not invent rows. Tell the user the comparison could not be completed."
            )
        }

    for _ in range(2):
        if raw_rows:
            break
        try:
            retried = json.loads(_strip_json_fence(_press_model_call(prompt)))
        except (json.JSONDecodeError, ValueError, Exception):
            continue
        if isinstance(retried, list) and retried:
            raw_rows = retried

    valid_labels = {
        "same",
        "different_framing",
        "contradiction",
        f"only_{left}",
        f"only_{right}",
    }
    both_required = {"same", "different_framing", "contradiction"}
    left_by_id = {paragraph["id"]: paragraph for paragraph in left_paras}
    right_by_id = {paragraph["id"]: paragraph for paragraph in right_paras}

    all_verified: list[dict] = []
    dropped_count = 0
    drop_reasons: list[str] = []

    for i, row in enumerate(raw_rows):
        tag = f"row {i + 1} (topic={row.get('topic', '?')!r})"
        label = row.get("label", "")
        reason = (row.get("reason") or "").strip()
        left_quote = row.get("left_quote") or None
        right_quote = row.get("right_quote") or None
        left_pid = _clean_paragraph_id(row.get("left_paragraph_id"))
        right_pid = _clean_paragraph_id(row.get("right_paragraph_id"))

        # A row without both quotes cannot be same, different_framing, or contradiction.
        if label in both_required:
            has_left = bool(left_quote and left_pid)
            has_right = bool(right_quote and right_pid)
            if has_left and not has_right:
                label = f"only_{left}"
            elif has_right and not has_left:
                label = f"only_{right}"

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
            if not left_quote or not right_quote or not left_pid or not right_pid:
                drop_reasons.append(
                    f"{tag}: label {label!r} requires both quotes and both paragraph ids"
                )
                dropped_count += 1
                continue
        elif label == f"only_{left}":
            if not left_quote or not left_pid:
                drop_reasons.append(
                    f"{tag}: label 'only_{left}' requires left_quote and left_paragraph_id"
                )
                dropped_count += 1
                continue
            right_quote = None
            right_pid = None
        elif label == f"only_{right}":
            if not right_quote or not right_pid:
                drop_reasons.append(
                    f"{tag}: label 'only_{right}' requires right_quote and right_paragraph_id"
                )
                dropped_count += 1
                continue
            left_quote = None
            left_pid = None

        quote_ok = True
        left_para = None
        right_para = None
        if left_quote is not None:
            left_para = left_by_id.get(left_pid or "")
            left_quote, left_drop = _accept_quote(left_quote, left_para, tag, "left", left_pid)
            if left_drop:
                drop_reasons.append(left_drop)
                quote_ok = False
        if right_quote is not None:
            right_para = right_by_id.get(right_pid or "")
            right_quote, right_drop = _accept_quote(right_quote, right_para, tag, "right", right_pid)
            if right_drop:
                drop_reasons.append(right_drop)
                quote_ok = False
        if not quote_ok:
            dropped_count += 1
            continue

        attributed = row.get("attributed_to")
        if not isinstance(attributed, str) or not attributed.strip():
            attributed = None
        else:
            attributed = attributed.strip()

        all_verified.append({
            "label": label,
            "topic": row.get("topic", ""),
            "reason": reason,
            "left_quote": left_quote,
            "right_quote": right_quote,
            "left_url": None if left_para is None else left_para.get("url"),
            "right_url": None if right_para is None else right_para.get("url"),
            "left_paragraph_id": None if left_para is None else left_para.get("id"),
            "right_paragraph_id": None if right_para is None else right_para.get("id"),
            "left_headline": None if left_para is None else left_para.get("headline"),
            "right_headline": None if right_para is None else right_para.get("headline"),
            "left_byline": None if left_para is None else left_para.get("byline"),
            "right_byline": None if right_para is None else right_para.get("byline"),
            "left_published": None if left_para is None else left_para.get("published"),
            "right_published": None if right_para is None else right_para.get("published"),
            "attributed_to": attributed,
            "source_note": _source_note(attributed),
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
    _cache[cache_key] = (_now(), result)
    return result


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
                f"compare_statements only works on meeting cases; "
                f"'{case_id}' is type '{case.get('type')}'. "
                "Use check_claim for claim_check cases."
            )
        }

    for side_name, side_val in (("left", left), ("right", right)):
        if side_val not in ("us", "china", "press"):
            return {
                "error": (
                    f"{side_name} must be 'us', 'china', or 'press', got '{side_val}'. "
                    "Call compare_statements again with one of those three values."
                )
            }

    if "press" in (left, right):
        return _compare_press(config, case_id, topic, left, right)

    left_result = get_official_source(config, case_id, left)
    if "error" in left_result:
        return {
            "error": (
                f"Could not load {left} statement: {left_result['error']} "
                "Do not invent that side's text."
            )
        }
    right_result = get_official_source(config, case_id, right)
    if "error" in right_result:
        return {
            "error": (
                f"Could not load {right} statement: {right_result['error']} "
                "Do not invent that side's text."
            )
        }

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
        return {
            "error": (
                f"Model call failed: {type(e).__name__}: {str(e)[:300]}. "
                "Do not invent a comparison. Tell the user the comparison could not be completed."
            )
        }

    # Strip markdown fences if the model wraps the JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        raw_rows = json.loads(raw)
        if not isinstance(raw_rows, list):
            raise ValueError("expected a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "error": (
                f"Model returned invalid JSON: {e}. Raw response: {raw[:200]!r}. "
                "Do not invent rows. Tell the user the comparison could not be completed."
            )
        }

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
