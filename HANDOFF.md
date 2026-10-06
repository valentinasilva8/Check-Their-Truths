# HANDOFF: Check Their Truths (Agentic AI class project)

Read this file first. Then read CLAUDE.md, DESIGN.md, DECISIONS.md (D-01 to D-43), and EVAL.md in that order. DECISIONS.md is the source of truth when anything here disagrees with older text.

---

## 1. Project at a glance

- **What it is:** a web chat agent that (1) compares how the US, China, and The Guardian described the Sept 23-25, 2026 Trump-Xi Washington meeting, topic by topic with verified verbatim quotes, and (2) checks three claims from a Trump Truth Social post about Medicare against official White House and CMS numbers.
- **Course:** Columbia, Agentic AI. Solo project.
- **Deadline:** Wednesday Oct 7, 2026, 11:59pm ET.
- **Grading:** Basics 1, Functionality 11, Tools 8, Creativity 5 (25 total).
- **Requirements:** at least 3 tools (at least 1 external data, at least 1 original); `/chat` returns `response`, `session_id`, `tool_calls` (name, arguments, result); session memory with user separation; graceful errors; frontend visibly different from the starter; root files `app.py`, `pyproject.toml`, `uv.lock`, `README.md`, `submission.json` (deploy_url + authors).

## 2. Setup

| Item | Value |
|---|---|
| Repo | https://github.com/valentinasilva8/gemini-web-tool-calling (private) |
| Working branch | `feature/two-readouts` (all work happens here) |
| Local dir | `/Users/valentinasilva/Downloads/gemini-web-tool-calling` |
| Stack | Python, FastAPI, LiteLLM, Gemini via Vertex AI, uv |
| GCP project | `valentinas-project-ieor4570` |
| Cloud Run service | `gemini-web-tool-calling-git`, region `europe-west1` |
| Deployed URL | https://gemini-web-tool-calling-git-jq4klbcf7q-ew.a.run.app/ (Columbia Google sign-in required) |
| Deploy trigger | Push to `main` auto-deploys. NEVER push to `main` directly. PR from the feature branch, the owner merges. |

Run locally: `uv run app.py`. Tests: `uv run pytest -q`. Model eval (real Gemini calls, not pytest): `uv run python eval.py`.

## 3. Files

| File | Purpose |
|---|---|
| `app.py` | FastAPI app, SYSTEM_PROMPT, MAX_TOOL_ROUNDS = 8, sessions |
| `tools.py` | Tool schemas (TOOLS) and TOOL_MAP. Weather tool removed. |
| `sources.py` | Config loading, URL fetching (config URLs only), HTML extraction per site, snapshots, `normalize_text`, `_try_live`, `_try_snapshot`, `get_official_source`, `fetch_source_by_name` |
| `compare.py` | `compare_statements`: model call at temperature 0, label validation, quote verification, pairing rule, Chinese term check, in-memory cache keyed with PROMPT_VERSION (currently "3") |
| `claim_check.py` | `check_claim`: rule dispatch by claim_type, Decimal math, context note |
| `eval.py` | Runs EVAL rows against the real model and prints PASS/FAIL |
| `config/sources.toml` | Cases, sources, URLs, markers, selectors. Top-level key `cases`. |
| `config/claims.toml` | The post (defined once) and claims C1 to C3 |
| `config/secrets.toml` | Guardian API key. GITIGNORED. Never commit. |
| `data/snapshots/` | Committed JSON snapshots (Cloud Run filesystem resets, so these must be in the repo) |
| `tests/fixtures/` | Raw HTML fixtures for extraction tests (public-domain government pages only) |
| `spikes/`, `.Rhistory`, `DESIGN.html` | Local scratch, gitignored |

## 4. The two cases

1. `washington_2026_09` (type `meeting`): sides `us` (White House fact sheet), `china` (MFA English, then gov.cn mirror, then Embassy mirror, then snapshot; Chinese original used only for a term check), `press` (The Guardian, two curated articles).
2. `medicare_checks_2026_10` (type `claim_check`): sources `wh_medicare_fact_sheet` and `cms_2026_premiums`.

Key URLs:
- US fact sheet: https://www.whitehouse.gov/fact-sheets/2026/09/fact-sheet-president-donald-j-trump-advances-a-fair-and-reciprocal-relationship-with-china-while-hosting-historic-state-visit/
- China MFA English: https://www.fmprc.gov.cn/eng/xw/zyxw/202609/t20260926_12031663.html
- WH Medicare fact sheet: https://www.whitehouse.gov/fact-sheets/2026/10/fact-sheet-president-donald-j-trump-announces-medicare-improvement-fund-payments-for-seniors/
- CMS 2026 premiums: https://www.cms.gov/newsroom/fact-sheets/2026-medicare-parts-b-premiums-deductibles
- Guardian article IDs: `us-news/2026/sep/24/xi-jinping-trump-china-cooperation-thucydides-trap`, `world/2026/sep/28/trump-xi-jinping-china-buy-weapons`

## 5. Tools (5)

| # | Tool | Type | Status |
|---|---|---|---|
| 1 | `list_cases()` | helper | done |
| 2 | `get_official_source(case_id, source)` | external data | done |
| 3 | `get_press_coverage(case_id)` | external API (Guardian) | Built. Curated ids only. Paragraphs stay in memory. |
| 4 | `compare_statements(case_id, topic, left="us", right="china")` | ORIGINAL | done for us vs china |
| 5 | `check_claim(case_id, claim_id)` | ORIGINAL | done |

`track_commitments` was cut (D-28). Do not rebuild it.

## 6. Hard rules (do not break these)

**Quotes and labels (compare_statements)**
- Every quote must be an exact substring of the source after normalization (whitespace, curly quotes, non-breaking spaces) AND at least 6 words. Failing rows are dropped and counted in `dropped` and `drop_reasons`. Never silently drop.
- Labels: `same`, `different_framing`, `contradiction`, `only_{left}`, `only_{right}`. Invalid labels or empty reasons are dropped.
- `contradiction` is strict: both sides make explicit factual claims that cannot both be true. Different terms, emphasis, or omission is NEVER contradiction (D-25, D-36).
- Pairing rule: a row may only pair quotes about the same specific item. Unrelated items under one topic become separate `only_` rows (D-37).
- AI naming ("super intelligence" vs "China-U.S. AI Dialogue") is `different_framing`, not contradiction (D-36).
- `term_check` row (Chinese original contains 人工智能 YES, 超级智能 NO) is a special row outside the label set, not counted toward the 12-row cap, always last.
- Empty topic means compare everything, capped at 12 rows, `cap_hit` reported.
- Neutrality: meeting comparisons never judge which government is right (D-15).

**Claim checks (check_claim)**
- Verdicts: `supported`, `imprecise`, `contradicted`, `not_checkable`. Verdict follows the plain reading. Other readings go in `context_note` only (D-33).
- Rules by `claim_type` (D-31): `at_least` (official >= claimed), `approximately` (diff / claimed: <= 5% supported, <= 25% imprecise, > 25% contradicted, D-34), `direction` (sign must match; zero change is contradicted).
- No verdicts or expected values in config, ever.
- All money in `Decimal`, two decimals in output, pct_change ROUND_HALF_UP to one decimal (D-30).
- The model never does math or writes the context note. Context note = "CMS also states: " + verbatim verified sentence (D-39).
- Anchors AND markers contain no numbers. Regexes run only on the sentence containing the anchor (D-41).
- `claimed_phrase` must be a substring of the post text, else `not_checkable` (D-35).
- C3 cross-check: computed change must equal the CMS-stated change, else `not_checkable` with reason "stated and computed changes do not match".
- Claim cards show the source plainly ("Checked against: White House fact sheet, Oct 2, 2026" + link). The name and date come from display_name and published in config, not from the fetch time (D-40).

**Fetching**
- Tools only fetch URLs from config, never user or model input (D-16).
- Live page is usable only if HTTP 200, marker found, at least 1 paragraph, and every required anchor found. Otherwise fall back to snapshot with `live_changed: true` and note "live page changed or unavailable; showing snapshot" (D-43).
- Live fetches never overwrite snapshots. Only `python sources.py --refresh-snapshots` does.

**Press (Phase P)**
- Full article text is never committed. Paragraphs are cached in memory and expire after 23 hours. compare_statements cache entries that contain press quotes expire after 23 hours (D-22).
- `data/press_citations/` stores a hash of each verified quote, plus url, headline, byline, paragraph id, published, retrieved_at, and attributed_to. No quote text. Written only by `uv run python press.py --save-citations`. Checked by `uv run python press.py --verify-citations`, which re-fetches and confirms each hash. The file is not a fallback (D-22). Test mocks use invented text only.
- Article IDs are curated in config. No runtime search (D-27). Live blogs excluded by API `type` field (D-21). Paragraph ids are A1-P1 for the first curated article and A2-P1 for the second.
- A press span must be 6 to 40 words as returned. Longer spans are dropped and counted as "span over 40 words". There is no trim and no "..." (D-48, D-24 replaced). Verification compares words with punctuation removed, then displays the exact source substring (D-47). Official quotes stay on exact substring match (D-10).
- Press comparisons use prompt version "7". US vs China stays on "3" (D-44). Every press row shows headline, byline, and link. Official quotes take display_name and published from the source in config. `attributed_to` is required when a named person is reported (D-32). If attributed_to mentions Xinhua, code sets source_note; the model does not write it (D-49).
- The China side is the MFA Eight Deliverables statement only. A press row that cites a Xinhua readout must say that readout is not the China source used here (D-46).
- API key: read lazily inside the press tool. `/secrets/guardian.toml` on Cloud Run, `config/secrets.toml` locally. Never an env var. Missing file returns "press side unavailable", never crashes (D-26).

## 7. Expected results

**US vs China eval rows (all pass)**

| Topic | Label | Key quote |
|---|---|---|
| AI naming | different_framing | US: both leaders agreed to use "super intelligence"; China: "China-U.S. AI Dialogue" |
| Coal | only_us | "China will import at least 10 million metric tons..." |
| Rare earths | only_us | "rare earths and other critical minerals" |
| Military crisis communication | only_china | "memorandum of understanding on crisis communication" (must appear as only_china for both "military" and "military crisis communication" topics) |

**Medicare claims (post excerpt, Oct 2, 2026, quoted identically by Axios, Fox Business, NewsNation; `original_url` = TODO)**

| Claim | Phrase | Checked against | Verdict | Numbers |
|---|---|---|---|---|
| C1 | "over 20 MILLION wonderful Seniors" | WH: "more than 20 million enrollees" | supported | 20,000,000 >= 20,000,000 |
| C2 | "nearly $100" | WH: "$90 per person" | imprecise | official 90.00, claimed 100.00, 10.0% |
| C3 | "which we have already reduced by significant amounts" | CMS: "$202.90 for 2026, an increase of $17.90 from $185.00 in 2025" | contradicted | +17.90/month, +9.7%, +214.80/year |

C3 context note: "CMS also states: If the Trump Administration had not taken action to address unprecedented spending on skin substitutes, the Part B premium increase would have been about $11 more a month."

## 8. Status (as of Oct 6, 2026)

Committed and pushed on `feature/two-readouts`: Phase A through Phase M, Phase P, the assignment alignment (64527b1), and Phase E. The page is `frontend/`, served at `/`, with the tool trail and evidence panel. README and `submission.json` are in place.

The service account is `655901547612-compute@developer.gserviceaccount.com` (the default compute account). Secret `guardian-secrets` is mounted at `/secrets/guardian.toml`. Max instances is 1. Revision `gemini-web-tool-calling-git-00004-l6s` is serving. Pull request 1 is open and not merged: https://github.com/valentinasilva8/gemini-web-tool-calling/pull/1

## 9. Next steps, in order

1. **Owner merges PR 1.** After the auto-deploy, confirm the new revision still has the secret mounted. Test the live URL with a second Columbia account.
2. **Phase E is on `feature/two-readouts`.** Do not merge to main. The page reads tool results only. It does not add a side selector.
3. **Phase F remainder:** known limits and the three grader queries are in the README. `submission.json` uses `vt2450`. Still open: a short "why I built this" paragraph (the README has a placeholder), and whether the assignment wants a UNI or an email in `authors`.
4. **Phase G remainder:** the secret is mounted and max instances is 1 (D-52). After the owner merges, confirm the new revision still has `/secrets/guardian.toml` mounted. Do not mount the secret inside `/app/config/`.

## 10. Owner's open to-dos

- Find the original Truth Social post URL and fill `original_url` in `config/claims.toml`.
- Confirm the `authors` format for `submission.json`.

## 11. Working agreements and things to watch

- **Plan first, then build.** Show a plan, wait for approval.
- **Show results before committing:** full pytest summary, eval.py output, full JSON (no "..."), smoke test via POST `/chat` with full `tool_calls`, `git diff --stat`. Then wait.
- **Never weaken a test to make it pass.** Watch for `==` changed to `>=`, exact values replaced by "not empty", tests deleted or skipped, comments that disagree with assertions, or fake fixtures with planted values. If a test and the spec disagree, report it.
- **Run the smoke test at the end of every phase.** Unit tests do not prove the agent calls the tools.
- **Check summaries against diffs.** Previous tools reported work as matching the plan when it did not.
- **Log every design decision in DECISIONS.md**, each number once, in order.
- **Docs drift:** after context compaction, coding tools reread the docs. Keep CLAUDE.md, DESIGN.md, and EVAL.md current or stale names come back.
- **The Medicare design is frozen.** Change it only for bugs.
- **Copyright:** China MFA content is copyrighted (fine in a private repo; check before making it public). Guardian text never enters the repo.
- Writing style for any user-facing copy: plain language, no em dashes.
- Always run tests with `uv run pytest -q`. `python -m pytest` uses the system Python, cannot import litellm, and silently skips 26 tests in test_compare.py.
