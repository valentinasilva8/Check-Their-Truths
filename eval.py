"""eval.py -- run compare_statements against the real model and print results.

Not part of pytest. Run: uv run python eval.py
Review actual quotes and verification status before committing Phase C.
"""

import re

from compare import _normalize, compare_statements
from press import MAX_CITATION_WORDS, quote_word_count
from sources import load_config


def _press_row(rows, label, paragraph_id, keywords):
    """Match on paragraph id, label, and 1-3 keywords. No article phrases."""
    if not 1 <= len(keywords) <= 3:
        raise ValueError(f"press check needs 1-3 keywords, got {keywords}")

    def hit(row):
        if row.get("label") != label or row.get("right_paragraph_id") != paragraph_id:
            return False
        quote = row.get("right_quote") or ""
        if "..." in quote:
            return False
        count = quote_word_count(quote)
        if count < 6 or count > MAX_CITATION_WORDS:
            return False
        if not row.get("right_headline") or not row.get("right_byline") or not row.get("right_url"):
            return False
        blob = " ".join([
            quote,
            row.get("reason") or "",
            row.get("attributed_to") or "",
        ]).lower()
        return all(keyword.lower() in blob for keyword in keywords)

    return any(hit(row) for row in rows if row.get("label") != "term_check")

EVAL_ROWS = [
    # (name, case_id, topic, left, right, extra_checks)
    # extra_checks: list of (description, predicate) to run on the row list
    (
        "AI naming",
        "washington_2026_09", "ai", "us", "china",
        [
            (
                "AI row label is different_framing",
                lambda rows: any(
                    r["label"] == "different_framing"
                    for r in rows if r.get("label") != "term_check"
                ),
            ),
            (
                "AI row reason mentions 'super intelligence'",
                lambda rows: any(
                    "super intelligence" in (r.get("reason") or "").lower()
                    for r in rows if r.get("label") != "term_check"
                ),
            ),
            (
                "AI row left_quote contains US claim about both leaders agreeing",
                lambda rows: any(
                    "agreed" in (r.get("left_quote") or "").lower()
                    for r in rows if r.get("label") != "term_check"
                ),
            ),
        ],
    ),
    (
        "Coal / energy",
        "washington_2026_09", "coal", "us", "china",
        [
            (
                "coal row label is only_us",
                lambda rows: any(
                    r["label"] == "only_us"
                    for r in rows if r.get("label") != "term_check"
                ),
            ),
        ],
    ),
    (
        "Rare earths",
        "washington_2026_09", "rare earths", "us", "china",
        [
            (
                "rare earths row label is only_us",
                lambda rows: any(
                    r["label"] == "only_us"
                    for r in rows if r.get("label") != "term_check"
                ),
            ),
        ],
    ),
    (
        "Military crisis communication (narrow topic)",
        "washington_2026_09", "military crisis communication", "us", "china",
        [
            (
                "only_china MOU row present",
                lambda rows: any(
                    r["label"] == "only_china"
                    and "memorandum" in (r.get("right_quote") or "").lower()
                    for r in rows
                ),
            ),
        ],
    ),
    (
        "Military (broad topic)",
        "washington_2026_09", "military", "us", "china",
        [
            (
                "MOU row is only_china (pairing rule prevents different_framing with unrelated US item)",
                lambda rows: any(
                    r["label"] == "only_china"
                    and "memorandum" in (r.get("right_quote") or "").lower()
                    for r in rows
                ),
            ),
            (
                "No different_framing row pairs unrelated item with MOU",
                lambda rows: not any(
                    r["label"] == "different_framing"
                    and "memorandum" in (r.get("right_quote") or "").lower()
                    for r in rows
                ),
            ),
        ],
    ),
    (
        "AI naming, us vs press",
        "washington_2026_09", "AI naming", "us", "press",
        [
            (
                "different_framing on A1-P14",
                lambda rows: _press_row(
                    rows, "different_framing", "A1-P14", ["super intelligence"]
                ),
            ),
            (
                "US quote is the agreement to use the term",
                lambda rows: any(
                    r.get("label") == "different_framing"
                    and "agreed" in (r.get("left_quote") or "").lower()
                    and "super intelligence" in _normalize(r.get("left_quote") or "")
                    for r in rows
                ),
            ),
            (
                "attributed_to names Trump",
                lambda rows: any(
                    r.get("right_paragraph_id") == "A1-P14"
                    and "trump" in (r.get("attributed_to") or "").lower()
                    for r in rows
                ),
            ),
        ],
    ),
    (
        "AI naming, china vs press",
        "washington_2026_09", "AI naming", "china", "press",
        [
            (
                "only_press on A1-P14, not paired with the dialogue",
                lambda rows: _press_row(
                    rows, "only_press", "A1-P14", ["super intelligence"]
                ),
            ),
            (
                "no different_framing row pairs the press naming line",
                lambda rows: not any(
                    r.get("label") == "different_framing"
                    and "super intelligence" in _normalize(r.get("right_quote") or "")
                    for r in rows
                ),
            ),
        ],
    ),
    (
        "Taiwan, us vs press",
        "washington_2026_09", "taiwan", "us", "press",
        [
            (
                "only_press on A2-P8",
                lambda rows: _press_row(
                    rows, "only_press", "A2-P8", ["Xinhua"]
                ),
            ),
            (
                "attributed_to is Xi Jinping via Xinhua readout",
                lambda rows: any(
                    (r.get("attributed_to") or "") == "Xi Jinping (via Xinhua readout)"
                    and r.get("right_paragraph_id") == "A2-P8"
                    for r in rows
                ),
            ),
            (
                "row has this exact source_note",
                lambda rows: any(
                    r.get("right_paragraph_id") == "A2-P8"
                    and r.get("source_note") == (
                        "Cites a Xinhua readout, which is not the China source used here."
                    )
                    for r in rows
                ),
            ),
        ],
    ),
    (
        "Taiwan, china vs press",
        "washington_2026_09", "taiwan", "china", "press",
        [
            (
                "only_press on A2-P8",
                lambda rows: _press_row(
                    rows, "only_press", "A2-P8", ["Xinhua"]
                ),
            ),
            (
                "row has this exact source_note",
                lambda rows: any(
                    r.get("right_paragraph_id") == "A2-P8"
                    and r.get("source_note") == (
                        "Cites a Xinhua readout, which is not the China source used here."
                    )
                    for r in rows
                ),
            ),
        ],
    ),
    (
        "Weapons sale, us vs press",
        "washington_2026_09", "weapons", "us", "press",
        [
            (
                "only_press on A2-P1",
                lambda rows: _press_row(
                    rows, "only_press", "A2-P1", ["Perdue"]
                ),
            ),
            (
                "attributed_to names David Perdue",
                lambda rows: any(
                    r.get("right_paragraph_id") == "A2-P1"
                    and "david perdue" in (r.get("attributed_to") or "").lower()
                    for r in rows
                ),
            ),
            (
                "not labeled contradiction",
                lambda rows: not any(
                    r.get("label") == "contradiction"
                    and "weapon" in (r.get("right_quote") or "").lower()
                    for r in rows
                ),
            ),
        ],
    ),
    (
        "Weapons sale, china vs press",
        "washington_2026_09", "weapons", "china", "press",
        [
            (
                "only_press on A2-P1",
                lambda rows: _press_row(
                    rows, "only_press", "A2-P1", ["Perdue"]
                ),
            ),
        ],
    ),
    (
        "WWII, us vs press",
        "washington_2026_09", "WWII", "us", "press",
        [
            (
                "A2-P13 vs fought side by side is not contradiction",
                lambda rows: not any(
                    r.get("label") == "contradiction"
                    and r.get("right_paragraph_id") == "A2-P13"
                    and "side by side" in (r.get("left_quote") or "").lower()
                    for r in rows
                ),
            ),
        ],
    ),
    (
        "Empty topic, us vs press",
        "washington_2026_09", "", "us", "press",
        [
            (
                "A2-P1 weapons quote appears only as only_press",
                lambda rows: any(
                    r.get("label") == "only_press" and r.get("right_paragraph_id") == "A2-P1"
                    for r in rows
                )
                and not any(
                    r.get("right_paragraph_id") == "A2-P1" and r.get("label") != "only_press"
                    for r in rows
                ),
            ),
            (
                "no row labeled same uses A2-P1",
                lambda rows: not any(
                    r.get("label") == "same" and r.get("right_paragraph_id") == "A2-P1"
                    for r in rows
                ),
            ),
            (
                "an AI row's press quote is A1-P14",
                lambda rows: all(
                    r.get("right_paragraph_id") == "A1-P14"
                    for r in rows
                    if r.get("label") != "term_check"
                    and r.get("right_quote")
                    and _is_ai_press_row(r)
                ),
            ),
            (
                "no press quote appears in more than one row",
                lambda rows: _press_quotes_are_unique(rows),
            ),
        ],
    ),
]


def _is_ai_press_row(row: dict) -> bool:
    """True when the row is about AI naming. Vacuous if no such row exists."""
    blob = f"{row.get('topic') or ''} {row.get('reason') or ''}".lower()
    if "super intelligence" in blob or "artificial intelligence" in blob:
        return True
    return bool(re.search(r"\bai\b", blob))


def _press_quotes_are_unique(rows) -> bool:
    quotes = [
        r.get("right_quote")
        for r in rows
        if r.get("label") != "term_check" and r.get("right_quote")
    ]
    return len(quotes) == len(set(quotes))


def main():
    config = load_config()
    all_checks_passed = True

    for name, case_id, topic, left, right, checks in EVAL_ROWS:
        print(f"\n{'=' * 66}")
        print(f"EVAL: {name}")
        print(f"  topic={topic!r}  left={left}  right={right}")
        print()

        result = compare_statements(config, case_id, topic, left, right)

        if "error" in result:
            print(f"  ERROR: {result['error']}")
            all_checks_passed = False
            continue

        rows = result["rows"]
        dropped = result["dropped"]
        cap_hit = result.get("cap_hit", False)
        non_term = [r for r in rows if r["label"] != "term_check"]
        term_rows = [r for r in rows if r["label"] == "term_check"]

        print(f"  verified rows: {len(non_term)}  dropped: {dropped}  cap_hit: {cap_hit}")
        if dropped:
            for dr in result["drop_reasons"]:
                print(f"  DROP: {dr}")

        for row in non_term:
            print(f"\n  [{row['label']}] topic={row['topic']!r}")
            print(f"    reason: {row['reason']}")
            if row.get("attributed_to"):
                print(f"    attributed_to: {row['attributed_to']}")
            lq = row.get("left_quote")
            rq = row.get("right_quote")
            if lq:
                pid = row.get("left_paragraph_id")
                suffix = f" [{pid}]" if pid else ""
                print(f"    left_quote  ({left}){suffix}: {lq!r}")
            if rq:
                pid = row.get("right_paragraph_id")
                suffix = f" [{pid}]" if pid else ""
                print(f"    right_quote ({right}){suffix}: {rq!r}")

        for row in term_rows:
            print(f"\n  [term_check] {row['reason']}")

        for desc, predicate in checks:
            ok = predicate(rows)
            status = "PASS" if ok else "FAIL"
            print(f"\n  CHECK [{status}]: {desc}")
            if not ok:
                all_checks_passed = False

    print(f"\n{'=' * 66}")
    if all_checks_passed:
        print("eval complete -- all checks passed")
    else:
        print("EVAL COMPLETE -- SOME CHECKS FAILED, review above")


if __name__ == "__main__":
    main()
