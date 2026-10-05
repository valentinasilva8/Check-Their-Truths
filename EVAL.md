# EVAL.md

Expected rows for the September 23-25, 2026 Washington meeting.
Each row must be confirmed against the committed snapshots before submission.

| Topic | Expected label | US quote (partial) | China quote (partial) | Verified |
|---|---|---|---|---|
| AI naming | contradiction | "super intelligence" | "China-U.S. AI Dialogue" | [ ] |
| Coal / energy | only_us | (White House mentions coal; confirm exact phrase) | (absent from China MFA English) | [ ] |
| Rare earths | only_us | (White House mentions rare earth; confirm exact phrase) | (absent from China MFA English) | [ ] |
| Military crisis communication | only_china | (absent from White House fact sheet) | (China MFA mentions crisis communication memo; confirm exact phrase) | [ ] |

## Chinese term check (AI topic)

| Term | Expected in Chinese original | Verified |
|---|---|---|
| 人工智能 | YES | [ ] |
| 超级智能 | NO | [ ] |

## How to verify

For each row, open the relevant snapshot file in `data/snapshots/` and confirm:
1. The partial quote above appears verbatim (or adjust the expected quote to match exactly).
2. The absent side's snapshot does not contain the term.
3. Update the "Verified" column and record the exact quote phrase to use in `data/commitments/`.

These checks must pass before `compare_statements` is considered correct for this meeting.
