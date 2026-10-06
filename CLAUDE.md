# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Two Readouts

## What this project is
A web chat agent for my Columbia Agentic AI class (solo project). For a given Trump-Xi meeting, it fetches the official US statement and China's official English statement, compares them topic by topic with verbatim quotes, and tracks dated commitments. Example finding: the White House says both leaders agreed to say "super intelligence" instead of "artificial intelligence", while China's statement names a "China-U.S. AI Dialogue", and China's Chinese original uses 人工智能 and not 超级智能.

Users: journalists, students, and analysts who want to see where the two official accounts agree and differ, without reading both in full.

## Verified facts (do not re-test unless something breaks)
- From Cloud Run in europe-west1: White House fact sheet, China MFA English page, and the gov.cn English mirror all returned HTTP 200 with the expected content (Oct 5, 2026).
- Not yet confirmed from Cloud Run: the China Embassy mirror and the Chinese original.
- All source URLs live in config/sources.toml.

## Stack and deployment
Python, FastAPI, LiteLLM, Gemini via Vertex AI. Google Cloud Run service gemini-web-tool-calling-git, region europe-west1, project valentinas-project-ieor4570. Pushing to main auto-deploys the graded app. The deployment requires Columbia Google sign-in.

## Hard rules
1. Never commit to, push to, or merge into main without my explicit OK. Work on feature/two-readouts.
2. URLs, source lists, and settings go in TOML files under config/, not environment variables or hardcoded strings.
3. Never invent URLs, quotes, dates, statuses, or meetings. Every quote shown to a user must appear word for word in a fetched or saved source, and code checks this, not the model.
4. Explain design decisions in plain language. I must understand and defend every line.
5. Before any change touching more than one file, show me a plan and wait for my OK.
6. Every new function gets a test. Run the full test suite before saying a step is done.
7. Never use em dashes in UI text, README, or comments.
8. When I approve a decision (design, scope, tool behavior, data, deployment), add or update an entry in DECISIONS.md in the same commit as the change it describes.

## Assignment requirements (never break these)
- /chat returns `response`, `session_id`, and `tool_calls`; each tool call includes name, arguments, and result.
- Conversation memory per session, with different users' sessions kept separate.
- At least 3 tools, at least 1 calling external data, at least 1 original tool.
- Clear tool and argument names and descriptions.
- Errors return actionable messages to the model.
- Frontend visibly different from the starter, showing tool calls, making the purpose clear.
- Repo root contains app.py, pyproject.toml, uv.lock, README.md, submission.json (deploy_url, authors).
- README explains the project and gives 3 sample queries for graders.
- Deadline: Wednesday Oct 7, 2026, 11:59 p.m. ET.

## Tools
1. list_cases(): returns all case IDs, types (meeting or claim_check), names, and dates.
2. get_official_source(case_id, source): source is "us" or "china". Meeting cases only. For China, tries MFA English, then gov.cn mirror, then Embassy mirror, then snapshot. Returns paragraphs, source URL, retrieved_at, live flag, and live_changed flag if the page marker was missing on a live 200 response.
3. get_press_coverage(case_id): meeting cases only. Fetches the two curated Guardian articles for the case. Returns headline, byline, url, published, and paragraphs. API key loaded lazily from /secrets/guardian.toml (Cloud Run) or config/secrets.toml (local). Returns error if unavailable.
4. compare_statements(case_id, topic, left, right): ORIGINAL. left and right are "us", "china", or "press". Returns rows labeled same, different_framing, contradiction, only_{left}, or only_{right}. Each row has a one-sentence reason, verified quotes, and attributed_to (for press rows). For the AI topic on washington_2026_09 also reports whether the Chinese original contains 人工智能 and/or 超级智能 as a special term_check row (outside the label set, not counted toward the 12-row cap). Unverifiable rows are dropped and the count is reported. Temperature 0; cached per (case_id, topic, left, right, PROMPT_VERSION, sha256 of source paragraphs).
5. check_claim(case_id, claim_id): ORIGINAL. claim_check cases only. Verifies the claimed_phrase is a substring of the named post. Applies the claim_type rule (at_least, approximately, direction) against official source data using Python Decimal arithmetic. Returns verdict (supported, imprecise, contradicted, not_checkable), numbers dict, arithmetic string, and optional context_note (verified source sentence only).

## Quote verification rules
Before comparing, normalize whitespace, curly vs straight quotes, and non-breaking spaces. A quote passes only if it is an exact substring of one paragraph from the cited source after normalization, and is at least 6 words long.

## Translation honesty
China quotes come from China's own official English release, never our translation. Label them "Official English text, China Ministry of Foreign Affairs" and link the Chinese original. The only Chinese-language check is an exact text match for specific terms (for example 人工智能 vs 超级智能).

## Neutrality
Report what each side says and where the texts differ. Never judge who is right, never use loaded words, never speculate about motives.

## Known limits (state these in the README)
- Sessions are stored in memory, so Cloud Run runs with max instances set to 1 and a restart clears conversations.
- Official statements are summaries, not transcripts, so "only one side mentions X" means only one statement mentions it, not that it wasn't discussed.
