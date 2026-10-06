# Two Readouts

Two Readouts compares the official US and China statements about the September 2026 Trump-Xi meeting, and it checks those statements against Guardian coverage. It also fact-checks three Medicare claims from a Trump post against White House and CMS numbers. The quotes are checked against the source before they are shown.

The app is deployed at https://gemini-web-tool-calling-git-jq4klbcf7q-ew.a.run.app

## How to use it

Ask one question at a time, in plain English. The page keeps the conversation, so a follow-up such as "now compare that with The Guardian" stays on the same topic. A new visit is a new conversation.

The answer is the model's summary. Under it, the page shows each tool the agent called, with the arguments and the result. The result is the part that was checked against a source.

## Three sample queries

These three were reliable in repeated checks. Each one passed every time it was run.

1. "Did Trump accurately describe the Medicare payments and premiums?"
   A correct answer checks all three claims: the count of seniors is supported, the "nearly $100" payment is imprecise because the official figure is $90, and the claim that premiums were reduced is contradicted because the Part B premium went up.

2. "What did The Guardian report that the official statements left out?"
   A correct answer includes Trump's offer to sell US weapons to China, labels it as press-only, and credits US ambassador David Perdue. It does not treat that offer as the same event as an official sentence about something else.

3. "How do the US and China statements differ on military crisis communication?"
   A correct answer reports China's agreement on crisis communication as something only the China statement says.

A bonus question, "How do the US and China statements differ on AI terminology?", is less consistent. The comparison is sometimes a wording difference and sometimes a one-sided report. The three questions above are the ones to grade.

## Why I built this

PLACEHOLDER: I will write this section myself.

## The tools

Five tools. Two of them use external data. Two of them are original. One reads the local config.

- `list_cases` reads the local config and returns the case ids. It does not use the network.
- `get_official_source` uses external data. It fetches a live official page, or a saved copy if the live page fails.
- `get_press_coverage` uses external data. It fetches the two curated Guardian articles.
- `compare_statements` is original. It asks the model to compare two sides, then keeps a quote only when that quote is in the source.
- `check_claim` is original. It applies fixed rules and code math to official numbers. The model does not do the arithmetic.

## What's ambitious here

A quote is shown only when it really appears in the source. Claim verdicts use fixed rules and code math, so the AI never does the arithmetic. The same meeting can be compared three ways: US and China, US and The Guardian, or China and The Guardian. Guardian text is refreshed within 24 hours, and the saved citation file stores a hash of each quote rather than the quote. The reliability of each finding was measured by asking the real model the same question three times.

## Testing and reliability

This project is tested in two ways.

**Automated code tests.** `uv run pytest -q` runs 115 tests. None of them call the AI. All 115 passed. Each area, in one line:

- Quote verification: a quote is kept only when it really appears in the source, and a press quote is shown with the source's own punctuation.
- Medicare math and verdict rules: the three claims come out supported, imprecise, or contradicted from the official numbers, including the boundary cases.
- Fetching and snapshot fallback: a live page is used when it is valid, and a saved copy is used when the live page fails or no longer contains the sentence we need.
- Guardian handling: the two chosen articles are fetched, numbered, and kept in memory; a saved citation file stores a hash of each quote, not the quote itself.
- Error cases: a wrong case type, a missing key, or a failed fetch returns a clear error instead of crashing.

**AI behavior checks.** A separate script asks the real model to compare the statements, then checks each answer against an answer we decided in advance. The model's wording can change from run to run even when the question is the same, so each check was run 3 times on October 6, 2026. A check that failed stays in the table.

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

**What this means.** The open question, "What did The Guardian report that the official statements left out?", is fully reliable in these three runs: the weapons offer stays press-only, it is not paired with a different official event, an AI row stays on Trump's wording, and no Guardian quote is reused. Taiwan, the weapons offer, the World War II line, and the coal, rare-earth, and narrow military comparisons are also 3/3. The two broad-military checks are 6/6: the first three runs plus three more on October 6, 2026. In a live chat, the broader question "How do the US and China statements differ on the military?" paired the US Indo-Pacific line with China's crisis communication agreement. The narrower crisis-communication question did not. The AI terminology comparisons vary. US versus China got the wording label 2 times out of 3. US versus The Guardian, and China versus The Guardian, got the expected AI row 1 time out of 3. We put the work into the open-ended question because that is the most common use, and that made the narrower AI terminology question less consistent.

The Medicare checks use fixed rules and code math, so they give the same answer every time.

## Known limits

- Conversations are stored in memory on one instance. A restart clears them, and a second instance would not see them.
- The post text is a press-quoted excerpt. The original link is still pending.
- The China side excludes the Xinhua readout.
- Guardian articles can be amended. A changed article can make a press quote fail verification.
- In a press row, "attributed to" is the AI's reading and can be wrong. The quotes themselves are always verified.
- Comparisons sometimes pair loosely related items (for example, arms control and the weapons offer) as different framing. The quotes are always verified; the pairing is the AI's judgment.
- The Guardian key is the non-commercial tier.

## How to run locally

```
uv sync
uv run app.py
```

Then open http://127.0.0.1:8000

```
uv run pytest -q
```
