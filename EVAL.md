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

## Press rows

Checks use the paragraph id, the label, attributed_to, and one to three keywords.
They do not copy article sentences. Press prompt version is 7 (D-44). US vs China stays on 3.

| Topic | Pair | Label | Paragraph | Keywords | attributed_to |
|---|---|---|---|---|---|
| AI naming | us vs press | different_framing | A1-P14 | super intelligence | names Trump |
| AI naming | china vs press | only_press | A1-P14 | super intelligence | names Trump |
| Taiwan | us vs press | only_press | A2-P8 | Xinhua | Xi Jinping (via Xinhua readout) |
| Taiwan | china vs press | only_press | A2-P8 | Xinhua | Xi Jinping (via Xinhua readout) |
| Weapons sale | us vs press | only_press | A2-P1 | Perdue | names David Perdue |
| Weapons sale | china vs press | only_press | A2-P1 | Perdue | names David Perdue |
| WWII | us vs press | not contradiction | A2-P13 vs the US "side by side" line | side by side | |

China vs press does not pair the naming line with the China-U.S. AI Dialogue (D-45).
When attributed_to mentions Xinhua, the row's source_note is exactly "Cites a Xinhua readout, which is not the China source used here." Code writes that note; the model does not (D-49).
A State Department denial row is allowed and not required.
The WWII row must never be contradiction: "allies with China" and "the CCP was not an ally" can both be true (D-44).

## How to verify

For each row, open the relevant snapshot file in `data/snapshots/` and confirm:
1. The partial quote above appears verbatim (or adjust the expected quote to match exactly).
2. The absent side's snapshot does not contain the term.
3. Run `uv run python eval.py` and confirm 0 dropped rows and the expected labels appear.
