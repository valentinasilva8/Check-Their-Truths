# Check Their Truths

Check Their Truths compares the official US and China statements about the September 2026 Trump-Xi meeting, and it checks those statements against Guardian coverage. It also fact-checks three Medicare claims from a Trump post against White House and CMS numbers. The quotes are checked against the source before they are shown.

The app is deployed at https://gemini-web-tool-calling-git-jq4klbcf7q-ew.a.run.app

## How to use it

Ask one question at a time, in plain English. The page keeps the conversation, so a follow-up such as "now compare that with The Guardian" stays on the same topic. A new visit is a new conversation.

The answer is the model's summary. Under it, the page shows each tool the agent called, with the arguments and the result. The result is the part that was checked against a source.

## Sample prompts and expected behavior

These are the three questions on the empty state.

1. "compare what the US and China said about trump's last meeting with xi."
   A correct answer compares the official US and China statements about the September 2026 Trump-Xi meeting. If the user then asks who is lying, the answer does not name a liar. It explains where the statements differ.

2. "is trump telling the truth about medicare?"
   A correct answer checks all three claims: the count of seniors is supported, the "nearly $100" payment is imprecise because the official figure is $90, and the claim that premiums were reduced is contradicted because the Part B premium went up.

3. "what did the guardian catch about trump's xi meeting that the white house left out?"
   A correct answer is about the September 2026 Trump-Xi meeting, and about what The Guardian reported on that meeting that the White House fact sheet left out. It includes Trump's offer to sell US weapons to China and labels it as press-only. It says the article attributes that offer to David Perdue, the US ambassador to China. He is the person the article says reported the offer. He did not write the article. The answer does not treat that offer as the same event as an official sentence about something else. If the user then says to compare that with what China said, the answer stays on that meeting and compares China with The Guardian.

## Why I built this

I started this project because I wanted an easier way to keep up with AI developments between the US and China by looking at both sides before forming an opinion. When both governments publish their own summary of the same conversation, they often don't fully match. The White House said both leaders agreed to call AI "super intelligence." China's statement just said "AI," and its Chinese version never uses the term at all. That made me curious about everything else that didn't line up, and what the press actually saw that neither summary even mentioned. The Guardian reported that Trump offered to sell weapons to China, which isn't in any official statement. From there, I wanted to try checking a claim against the government's own numbers, so I added Trump's Medicare post and compared it with CMS data. For example, the post said premiums had already been reduced by significant amounts, but CMS shows the standard Part B premium rose from $185.00 in 2025 to $202.90 in 2026. The tool is not meant to decide who's lying, but it shows me exactly where the stories differ, with every quote checked against its source to help me visualize all sides of a story in the most unbiased way as possible (if that's even possible).

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

The full pass-rate table with tested prompts and agent behaviors is in docs/EVAL.md.

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
