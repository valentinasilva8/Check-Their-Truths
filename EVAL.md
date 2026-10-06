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

## Pass rates

Checked on October 6, 2026. `uv run pytest -q` runs 116 code tests. None of them call the AI. All 116 passed. They cover quote verification, Medicare math and verdicts, live-page and snapshot fallback, Guardian fetching, error cases, and the home page.

A separate script asks the real model to compare the statements, then checks each answer against an answer decided in advance. The model's wording can change from run to run, so each check was run 3 times. A check that failed stays in the table.

| Question | Pass rate |
|---|---|
| On AI terminology, do the US and China statements differ in wording rather than one side simply omitting the topic? | 2/3 |
| Does that US-China comparison mention "super intelligence"? | 3/3 |
| Does the US quote say both leaders agreed on the term? | 3/3 |
| Is China's coal import reported only in the US statement? | 3/3 |
| Are rare earths reported only in the US statement? | 3/3 |
| Asked narrowly about military crisis communication, is China's agreement reported only on the China side? | 3/3 |
| Asked broadly about the military, is that same agreement still reported only on the China side? | 6/6 |
| Does the broad military comparison avoid pairing that agreement with an unrelated US line? | 6/6 |
| Comparing the US statement with The Guardian on AI terminology, are both the leaders' agreement and Trump's wording shown? | 1/3 |
| In that comparison, is the US quote the sentence where both leaders agreed to use the term? | 1/3 |
| Is The Guardian's report of that wording credited to Donald Trump? | 1/3 |
| Comparing China with The Guardian on AI terminology, is The Guardian's report shown as press-only? | 1/3 |
| Does that comparison avoid treating Trump's wording and China's dialogue as the same item? | 3/3 |
| Is The Guardian's Taiwan report press-only when compared with the US statement? | 3/3 |
| Is that Taiwan report credited to Xi Jinping, citing a Xinhua readout? | 3/3 |
| Does the tool note that this Xinhua readout is not the China source used here? | 3/3 |
| Is the same Taiwan report press-only when compared with China's statement? | 3/3 |
| Does that China comparison also note that the Xinhua readout is not the China source used here? | 3/3 |
| Is Trump's weapons offer, reported only by The Guardian, labeled as press-only and credited to US ambassador David Perdue? | 3/3 |
| Is that weapons offer not labeled a contradiction of the US statement? | 3/3 |
| Is the same weapons offer press-only when compared with China's statement? | 3/3 |
| Is the US line that the two countries fought side by side in World War II never labeled a contradiction of The Guardian? | 3/3 |
| Asked what The Guardian reported that the official statements left out, is the weapons offer labeled press-only? | 3/3 |
| On that open question, is the weapons offer never called "the same" as an official sentence about a different event? | 3/3 |
| On that open question, if AI terminology comes up, does the press quote stay the sentence about Trump's wording? | 3/3 |
| On that open question, is each Guardian quote used only once? | 3/3 |

The open question, "What did The Guardian report that the official statements left out?", passed on all three of those points: the weapons offer stays press-only, it is not paired with a different official event, an AI row stays on Trump's wording, and no Guardian quote is reused. Taiwan, the weapons offer, the World War II line, and the coal, rare-earth, and narrow military comparisons are also 3/3. The two broad-military checks are 6/6: the first three runs plus three more on October 6, 2026. In a live chat, the broader question "How do the US and China statements differ on the military?" paired the US Indo-Pacific line with China's crisis communication agreement. The narrower crisis-communication question did not. The AI terminology comparisons vary. US versus China got the wording label 2 times out of 3. US versus The Guardian, and China versus The Guardian, got the expected AI row 1 time out of 3.

David Perdue is the US ambassador to China. On the weapons-offer row, "credited to David Perdue" means The Guardian article says he is the person who reported that Trump offered to sell US weapons to China. He did not write the article.

The Medicare checks use fixed rules and code math, so they give the same answer every time.

## Chat prompts

Each prompt below was asked in three fresh chats on October 6, 2026, with its follow-up. All three passed.

1. "can you compare the us coverage vs the china coverage of trumps last meeting with xi?"
   Compares the US and China statements. The follow-up "who's lying, the US or China?" does not name a liar. It explains where the statements differ.

2. "is trump telling the truth about medicare?"
   Checks all three claims. The count of seniors is supported, the "nearly $100" payment is imprecise because the official figure is $90, and the claim that premiums were reduced is contradicted because the Part B premium went up.

3. "what did the guardian catch that the white house left out?"
   The topic is the September 2026 Trump-Xi meeting, and what The Guardian reported about that meeting that the White House fact sheet left out. The weapons offer is only in The Guardian. The article attributes it to David Perdue, the US ambassador to China, who is the person the article says reported the offer. He did not write the article. The follow-up "ok now compare that with what china said" stays on that meeting and compares China with The Guardian.
