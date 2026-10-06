# HANDOFF: Two Readouts (Agentic AI class project)

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
| 3 | `get_press_coverage(case_id)` | external API (Guardian) | NOT BUILT (Phase P). `compare_statements` currently returns "press side not available yet" for press. |
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
- Claim cards show the source plainly ("Checked against: White House fact sheet, Oct 2, 2026" + link), no editorial notes (D-40).

**Fetching**
- Tools only fetch URLs from config, never user or model input (D-16).
- Live page is usable only if HTTP 200, marker found, at least 1 paragraph, and every required anchor found. Otherwise fall back to snapshot with `live_changed: true` and note "live page changed or unavailable; showing snapshot" (D-43).
- Live fetches never overwrite snapshots. Only `python sources.py --refresh-snapshots` does.

**Press (Phase P)**
- Guardian text is NEVER written to the repo, fixtures, or snapshots. In-memory cache only. Test mocks use invented text (D-22, D-23).
- Article IDs are curated in config. No runtime search (D-27). Live blogs excluded by API `type` field (D-21).
- Press spans over 25 words are trimmed to the first 25 words plus "..." for display, never dropped for length (D-24).
- Press rows carry `attributed_to` (D-32).
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

Committed and pushed on `feature/two-readouts`: Phase A through Phase M, including Phase M fixes (c8b6caf). 81 tests pass (`uv run pytest -q`).

Next phase is Phase P (Guardian press coverage).

## 9. Next steps, in order

1. **Resolve the test count, commit, push** the feature branch (not main).
2. **Phase P (press):**
   - Build `get_press_coverage(case_id)` (Guardian Open Platform API, `show-fields=body,headline,byline`, extract `<p>`).
   - Replace the press stub in `compare_statements`. Give the model numbered paragraphs; it returns paragraph number + exact span; verify the span is in that paragraph.
   - Before writing code, fetch both articles and PROPOSE expected EVAL rows for AI naming, Taiwan, and the weapons sale. The owner confirms them. Do not guess labels.
   - Tests: mocked API with invented text, API 500 -> "press side unavailable", missing secrets file -> unavailable, 25-word trim with "...", paragraph numbering, span not in paragraph -> dropped.
   - Note: most Guardian articles were published before the official statements came out.
3. **Phase E (frontend, built in v0):**
   - Push the branch first. Point v0 at `feature/two-readouts`, never `main`. Do not run v0 and another coding tool on the branch at the same time.
   - Output must be plain HTML/CSS/JS served by FastAPI (one `index.html`), or static files FastAPI can serve. Not a separate Next.js deploy.
   - Everything renders from `tool_calls` in the `/chat` JSON, never from model prose. Give v0 real sample JSON (a compare_statements result with a term_check row, and a check_claim result with a context note).
   - Comparison view: side selector (US vs China, US vs Press, China vs Press), LIVE/SNAPSHOT badges, "N rows hidden because quotes could not be verified", term_check row, source links.
   - Claim cards: verdict badge (supported / imprecise / contradicted / not_checkable), rule and thresholds shown, numbers, arithmetic string, evidence quote, "Checked against" source line, separate Context box (only when context_note is not null), "excerpt" label on the post, "original link pending" while `original_url` is TODO.
4. **Phase F:** README with 3 grader queries (one US vs China, one press, one Medicare), known limits (in-memory sessions, max-instances 1, hard-coded post excerpt, original link pending, Guardian articles predate official statements, Guardian key is non-commercial tier), next steps (discovery tool for new statements, automated claim extraction). Do NOT mention soybeans. `submission.json` with deploy_url and authors (confirm whether the assignment wants UNI or email).
5. **Phase G (deploy):**
   ```
   gcloud secrets create guardian-secrets --project=valentinas-project-ieor4570 --replication-policy=automatic
   gcloud secrets versions add guardian-secrets --project=valentinas-project-ieor4570 --data-file=config/secrets.toml
   gcloud secrets add-iam-policy-binding guardian-secrets --project=valentinas-project-ieor4570 --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" --role="roles/secretmanager.secretAccessor"
   gcloud run services update gemini-web-tool-calling-git --project=valentinas-project-ieor4570 --region=europe-west1 --update-secrets=/secrets/guardian.toml=guardian-secrets:latest
   ```
   Mount at `/secrets/guardian.toml`, NOT inside `/app/config/` (a secret volume would hide sources.toml and claims.toml). Set max-instances 1. Open a PR to main; the owner merges. After the auto-deploy, confirm the new revision still has the secret mounted. Test the live URL with a second Columbia account. Confirm cms.gov and the Guardian API are reachable from Cloud Run (untested). For one-off Cloud Run checks use a Dockerfile (`FROM python:3.12-slim`, `CMD ["python","-u","check.py"]`) run as a Cloud Run job with no command override.

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
