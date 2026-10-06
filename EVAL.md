# EVAL.md

Expected rows for the September 23-25, 2026 Washington meeting.
Each row confirmed against committed snapshots and live eval run on 2026-10-05.

| Topic | Expected label | US quote (partial) | China quote (partial) | Verified |
|---|---|---|---|---|
| AI naming | different_framing | "super intelligence" | "China-U.S. AI Dialogue" | [x] |
| Coal / energy | only_us | "China will import at least 10 million metric tons of coal" | (absent from China MFA English) | [x] |
| Rare earths | only_us | "rare earths and other critical minerals" | (absent from China MFA English) | [x] |
| Military crisis communication | only_china | (absent from White House fact sheet) | "memorandum of understanding on crisis communication" | [x] |

Note: AI naming is different_framing, not contradiction. China's statement uses "AI" throughout
without making any claim about terminology. Omission plus different wording is not contradiction
(see D-36).

## Chinese term check (AI topic)

| Term | Expected in Chinese original | Verified |
|---|---|---|
| 人工智能 | YES | [x] |
| 超级智能 | NO | [x] |

## How to verify

For each row, open the relevant snapshot file in `data/snapshots/` and confirm:
1. The partial quote above appears verbatim (or adjust the expected quote to match exactly).
2. The absent side's snapshot does not contain the term.
3. Run `uv run python eval.py` and confirm 0 dropped rows and the expected labels appear.
