# Check Their Truths

Check Their Truths compares the official US and China statements about the September 2026 Trump-Xi meeting, and it checks those statements against Guardian coverage. It also fact-checks three Medicare claims from a Trump post against White House and CMS numbers. The quotes are checked against the source before they are shown.

The app is deployed at https://gemini-web-tool-calling-git-jq4klbcf7q-ew.a.run.app

## How to use it

Ask one question at a time, in plain English. The page keeps the conversation, so a follow-up such as "now compare that with The Guardian" stays on the same topic. A new visit is a new conversation.

Above each answer, the page shows the steps the agent took (the tools it called). Click a step to see its arguments and result. The evidence panel shows the quotes, labels, and verdicts, each checked against its source.

## Sample prompts and expected behavior

These are the three questions on the empty state. For each one, the agent decides on its own which tools to call. The agent may call `list_cases` first to look up the case. The step trail above each answer shows the calls it actually made.

1. "compare what the US and China said about trump's last meeting with xi."

   **Tools called:** `compare_statements` (US vs China, all topics). The "who is lying" follow-up may call `compare_statements` again or answer from the earlier comparison.

   **Correct answer:** compares the official US and China statements about the September 2026 Trump-Xi meeting and highlights where they differ: points framed differently, points only in the US statement, and points only in China's. If the user then asks who is lying, the answer does not name a liar. It explains where the statements differ, showing how each government emphasizes the points that serve its own interests.

2. "is trump telling the truth about medicare?"

   **Tools called:** `check_claim`, three times (once per claim).

   **Correct answer:** checks all three claims. The count of seniors is supported. The "nearly $100" payment is imprecise: the official figure is $90, a 10% gap, which is more than the 5% allowed for a claim to count as supported (anything over 25% would be contradicted). The claim that premiums were reduced is contradicted because the Part B premium went up.

3. "what did the guardian catch about trump's xi meeting that the white house left out?"

   **Tools called:** `compare_statements` (US vs The Guardian). The follow-up calls `compare_statements` again (China vs The Guardian), which shows the agent remembered the topic.

   **Correct answer:** includes Trump's offer to sell US weapons to China and labels it as press-only. It says the article attributes that offer to David Perdue, the US ambassador to China. If the user then says to compare that with what China said, the answer stays on that meeting and compares China with The Guardian.

## More to try

- "show me what china's official statement actually says" (calls `get_official_source`)
- "show me the guardian articles about the meeting" (calls `get_press_coverage`)

## Why I built this

I started this project because I wanted an easier way to keep up with AI developments between the US and China by looking at both sides before forming an opinion.

When both governments publish their own summary of the same conversation, they often don't fully match. The White House said both leaders agreed to call AI "super intelligence." China's statement just said "AI," and its Chinese version never uses the term at all.

That made me curious about everything else that didn't line up, and what the press actually saw that neither summary even mentioned. The Guardian reported that Trump offered to sell weapons to China, which isn't in any official statement. From there, I wanted to try checking a claim against the government's own numbers, so I added Trump's Medicare post and compared it with CMS data. For example, the post said premiums had already been reduced by significant amounts, but CMS shows the standard Part B premium rose from $185.00 in 2025 to $202.90 in 2026.

The tool isn't meant to decide who's lying, but it shows me exactly where the stories differ, with every quote checked against its source, to help me see all sides of a story in the least biased way possible (if that's even possible).

## The tools

Five tools. Two of them use external data. Two of them are original. One reads the local config.

- `list_cases` reads the local config and returns the case ids. It does not use the network.
- `get_official_source` uses external data. It fetches the official statements live: the White House fact sheets, China's Ministry of Foreign Affairs statement, and the CMS Medicare fact sheet. If a live page fails, it uses a saved copy.
- `get_press_coverage` uses external data. It fetches articles from The Guardian.
- `compare_statements` is original. It compares any two sides of the meeting (US, China, or The Guardian) topic by topic, and labels each point as the same, framed differently, a contradiction, or mentioned by only one side. The AI picks the quotes, but code checks every quote word for word against its source and hides any it can't verify.
- `check_claim` is original. It fact-checks a claim from Trump's Medicare post against official numbers. Code finds the right sentence in the official source, pulls out the numbers, does the math, and applies a fixed rule (for example, within 5% counts as supported), so the verdict is the same every time. The AI only explains the result.

`compare_statements` and `check_claim` also fetch the live sources themselves, so every sample prompt uses external data. `get_official_source` and `get_press_coverage` are for when you want to read a source directly.

## Testing and reliability

The code is covered by 116 automated tests that don't call the AI. The reliability of each finding was measured by asking the real model the same question three times. The Medicare checks and the "what did The Guardian catch" question passed every time. The AI terminology comparisons were less consistent between responses.

The full pass-rate table, with tested prompts and agent behaviors, is in [docs/EVAL.md](docs/EVAL.md).

## Known limits

- Quotes are always verified, but labels are the AI's judgment. Whether two quotes count as "different framing" or get paired together is the AI's call, and it can vary between runs.
- "Attributed to" is the AI's reading of the article and can be wrong. The quote itself is always checked.
- The press side is The Guardian only, and the China side is the Foreign Ministry statement only, not China's separate Xinhua readout

## How to run locally

```
uv sync
uv run app.py
```

Then open http://127.0.0.1:8000

```
uv run pytest -q
```
