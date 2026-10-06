# gemini-web-tool-calling

`qwen-tool-calling` behind a web server, pointed at Gemini.

- The harness loop is the same one from `qwen-tool-calling`, wrapped in `run_agent()`.
- The session store and `/chat` endpoint are the ones from `qwen-web-chat`.
- Only the model changed: `vertex_ai/gemini-3.5-flash-lite` in the `global` location.
- `/chat` also returns the tool calls the harness made, and the page shows them
  above the assistant's answer.

## Setup

1. A GCP project with billing and the Agent Platform API enabled
   (older docs and the endpoint itself still call it Vertex AI)
2. `gcloud auth application-default login`. The app uses your gcloud default
   project, so run `gemini-hello-world` first to check it.
3. `uv run app.py`, then open http://localhost:8000

Try: "Is it nice enough to go for a walk in New York?"

The weather comes from Open-Meteo, which needs no API key.

## Testing and reliability

This project is tested in two ways.

**Automated code tests.** `uv run pytest -q` runs 106 tests. None of them call the AI. All 106 passed. Each area, in one line:

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
| Asked broadly about the military, is that same agreement still reported only on the China side? | 3/3 |
| Does the broad military comparison avoid pairing that agreement with an unrelated US line? | 3/3 |
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

**What this means.** The open question, "What did The Guardian report that the official statements left out?", is fully reliable in these three runs: the weapons offer stays press-only, it is not paired with a different official event, an AI row stays on Trump's wording, and no Guardian quote is reused. Taiwan, the weapons offer, the World War II line, and the coal, rare-earth, and military comparisons are also 3/3. The AI terminology comparisons vary. US versus China got the wording label 2 times out of 3. US versus The Guardian, and China versus The Guardian, got the expected AI row 1 time out of 3. We put the work into the open-ended question because that is the most common use, and that made the narrower AI terminology question less consistent.

The Medicare checks use fixed rules and code math, so they give the same answer every time.

## Known limits

Draft for Phase F. The rest of this README is still the starter text.

- The China side does not include the Xinhua talks readout, which mentioned Taiwan.
- Articles can be amended. A changed article can make a press row fail verification. `data/press_citations/` keeps a dated hash of each verified quote, not the quote text.
- The Guardian key is the non-commercial developer tier.
