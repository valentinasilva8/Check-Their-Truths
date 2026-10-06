"""eval.py -- run compare_statements against the real model and print results.

Not part of pytest. Run: uv run python eval.py
Review actual quotes and verification status before committing Phase C.
"""

from sources import load_config
from compare import compare_statements

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
                # With a broad topic both sides have military content, so the model may
                # produce different_framing rather than only_china. The MOU quote should
                # appear in either case.
                "MOU quote present in military rows (any label)",
                lambda rows: any(
                    "memorandum" in (r.get("right_quote") or "").lower()
                    for r in rows if r.get("label") != "term_check"
                ),
            ),
        ],
    ),
]


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
            lq = row.get("left_quote")
            rq = row.get("right_quote")
            if lq:
                print(f"    left_quote  ({left}): {lq!r}")
            if rq:
                print(f"    right_quote ({right}): {rq!r}")

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
