# DECISIONS.md

A running log of every project decision, so we can refer back to why things are the way they are.

| ID | Date | Decision | Status |
|---|---|---|---|
| D-01 | 2026-10-05 | Purpose: compare US and China official statements topic by topic | Active |
| D-02 | 2026-10-05 | Feasibility verified from Cloud Run europe-west1 | Active |
| D-03 | 2026-10-05 | China sources: official English only, priority order with snapshot fallback | Active |
| D-04 | 2026-10-05 | Chinese term check: exact text match only, no translation | Active |
| D-05 | 2026-10-05 | Branches: build on feature/two-readouts, main requires explicit OK | Active |
| D-06 | 2026-10-05 | Config: URLs and settings in TOML files under config/ | Active |
| D-07 | 2026-10-05 | Sessions: in-memory, Cloud Run max instances 1 | Active |
| D-08 | 2026-10-05 | MAX_TOOL_ROUNDS raised from 5 to 8 | Active |
| D-09 | 2026-10-05 | Snapshots: JSON in data/snapshots/, committed to repo | Active |
| D-10 | 2026-10-05 | Quote verification: exact substring after normalization, minimum 6 words | Active |
| D-11 | 2026-10-05 | Comparison labels: same, different_framing, contradiction, only_us, only_china | Active |
| D-12 | 2026-10-05 | Comparison call: temperature 0, cached per meeting | Active |
| D-13 | 2026-10-05 | Commitments: hand-curated with exact quote, deadline wording, and snapshot test | Active |
| D-14 | 2026-10-05 | Dropped rows reported to the user, never hidden silently | Active |
| D-15 | 2026-10-05 | Neutrality: report differences for meetings, never judge; claim checks use fixed rules only | Active |
| D-16 | 2026-10-05 | Safety: tools only fetch URLs from config/sources.toml | Active |
| D-17 | 2026-10-05 | HTML parsing: beautifulsoup4 with lxml parser | Active |
| D-18 | 2026-10-05 | Two cases: washington_2026_09 (meeting) and medicare_checks_2026_10 (claim_check) | Active |
| D-19 | 2026-10-05 | Medicare claim check approved; Guardian Medicare search returned false positives only | Active |
| D-20 | 2026-10-05 | Guardian API approved for two curated articles; word counts are not used in any logic | Active |
| D-21 | 2026-10-05 | Live blogs excluded from press_articles; identified by Guardian API type field "liveblog" | Active |
| D-22 | 2026-10-06 | Replaced: content-free citation hashes; press caches expire after 23 hours; no Guardian quote text stored | Active |
| D-23 | 2026-10-06 | Replaced: press spans over the word limit are dropped; every press row shows headline, byline, and link | Active |
| D-24 | 2026-10-05 | Replaced: the 25-word trim with "..." is withdrawn because Guardian terms forbid editing content | Replaced |
| D-25 | 2026-10-05 | compare_statements uses same/different_framing/contradiction/only_{side} for every pair | Active |
| D-26 | 2026-10-05 | Guardian API key loaded lazily; /secrets/guardian.toml on Cloud Run, config/secrets.toml locally | Active |
| D-27 | 2026-10-05 | Press articles are curated in config, never searched at runtime | Active |
| D-28 | 2026-10-05 | check_claim replaces track_commitments | Active |
| D-29 | 2026-10-05 | Truth Social post (source for C1, C2, C3) hard-coded verbatim in claims.toml; original_url = "TODO" | Active |
| D-30 | 2026-10-05 | Python Decimal arithmetic for dollar amounts; expressions stored as strings | Active |
| D-31 | 2026-10-05 | Claim rules general (at_least, approximately, direction); verdicts never in config | Active |
| D-32 | 2026-10-05 | Press rows carry attributed_to (named person or null for outlet's own reporting) | Active |
| D-33 | 2026-10-05 | check_claim verdicts: supported, imprecise, contradicted, not_checkable; context_note for other reasonable readings | Active |
| D-34 | 2026-10-05 | approximately thresholds: 5% supported, 25% imprecise, >25% contradicted; denominator is claimed value | Active |
| D-35 | 2026-10-05 | Claims reference a named post; claimed_phrase verified as substring; C3 cross-checks CMS stated vs computed change | Active |
| D-36 | 2026-10-05 | AI naming is different_framing; contradiction requires explicit incompatible claims from both sides | Active |
| D-37 | 2026-10-05 | Pairing rule: a row may only pair quotes about the same specific item or commitment | Active |
| D-38 | 2026-10-05 | C1 supported: noun differences (enrollees vs Seniors) are outside the at_least rule | Active |
| D-39 | 2026-10-05 | context_note format: fixed lead-in "CMS also states:" + verbatim verified CMS sentence; model never writes it | Active |
| D-40 | 2026-10-05 | Claim cards show source name plainly with link; no editorial notes | Active |
| D-41 | 2026-10-05 | Anchors and markers are number-free; regexes run on the sentence containing the anchor, not the full paragraph | Active |
| D-42 | 2026-10-05 | C1 checks label renamed from senior_enrollment_count to enrollee_count | Active |
| D-43 | 2026-10-05 | Internal helpers _try_live and _try_snapshot replace duplicate live-first logic | Active |
| D-44 | 2026-10-06 | Press comparisons use numbered-paragraph prompt version 7; us vs china stays on version 3 | Active |
| D-45 | 2026-10-06 | AI naming: us vs china pairs the SI agreement with the AI Dialogue; china vs press is only_press | Active |
| D-46 | 2026-10-06 | China side is the MFA Eight Deliverables statement only; Xinhua talks readout is not a source | Active |
| D-47 | 2026-10-06 | Press spans match on words with punctuation removed, then display the exact source substring | Active |
| D-48 | 2026-10-06 | Press span limit is 40 words; longer spans are dropped, never trimmed | Active |
| D-49 | 2026-10-06 | Xinhua source_note is written by code, not by the model | Active |
| D-50 | 2026-10-06 | Cloud Run from europe-west1 can reach the White House, CMS, and the Guardian API; the Guardian secret is ready to mount | Active |
| D-51 | 2026-10-06 | Evidence quotes are the anchor sentence, and tool errors tell the model what to do next | Active |
| D-52 | 2026-10-06 | Guardian secret is mounted, max instances is 1, PR 1 is open, and answers render as Markdown | Active |
| D-53 | 2026-10-06 | Comparison results carry source metadata, claim results carry the post text, and term_check carries a terms map | Active |
| D-54 | 2026-10-06 | Display name changed to Check Their Truths (previously Two Readouts); internal names unchanged | Active |

---

### D-01: Purpose
- **Date:** 2026-10-05
- **Decision:** Two Readouts compares the official US and China statements about the same Trump-Xi meeting, topic by topic, with verbatim quotes, and tracks dated commitments.
- **Why:** Journalists, students, and analysts need to see where the two official accounts agree and differ without reading both in full.
- **Alternatives rejected:** None
- **Status:** Active

### D-02: Feasibility verification
- **Date:** 2026-10-05
- **Decision:** Verified that Cloud Run in europe-west1 can fetch the White House fact sheet, China MFA English page, and gov.cn mirror (HTTP 200, expected content), using a one-time Cloud Run job.
- **Why:** Confirmed the sources are reachable from the deployment region before building around them.
- **Alternatives rejected:** None
- **Status:** Active

### D-03: China sources
- **Date:** 2026-10-05
- **Decision:** Use China's own official English text, never our own translation. Source priority order: MFA English, then gov.cn mirror, then Embassy mirror, then saved snapshot.
- **Why:** Using China's own English text is more accurate and avoids translation bias. The priority order reflects availability confidence from Cloud Run.
- **Alternatives rejected:** Xinhua search (returned HTTP 405, and the same official text is available directly from the mirrors).
- **Status:** Active

### D-04: Chinese term check
- **Date:** 2026-10-05
- **Decision:** Exact text match only for specific terms (for example 人工智能 vs 超级智能), no translation. Live fetch of the Chinese original from Cloud Run is not yet confirmed, so the committed snapshot covers it.
- **Why:** A live fetch of the Chinese original has not been confirmed from Cloud Run europe-west1. Exact matching avoids any ambiguity a translation would introduce.
- **Alternatives rejected:** Machine translation of the Chinese original (introduces ambiguity and cannot be verified word for word).
- **Status:** Active

### D-05: Branch strategy
- **Date:** 2026-10-05
- **Decision:** Build on feature/two-readouts. Nothing goes to main without explicit owner approval, because pushing to main auto-deploys the graded app.
- **Why:** An accidental push to main would immediately overwrite the live graded deployment.
- **Alternatives rejected:** None
- **Status:** Active

### D-06: Config storage
- **Date:** 2026-10-05
- **Decision:** URLs and settings live in TOML files under config/, not environment variables or hardcoded strings.
- **Why:** TOML files are version-controlled, reviewable, and easy to audit. Hardcoded strings scatter config across the codebase.
- **Alternatives rejected:** Environment variables (not version-controlled, harder to audit for a class project).
- **Status:** Active

### D-07: Session storage
- **Date:** 2026-10-05
- **Decision:** Keep sessions in memory and run Cloud Run with max instances set to 1. A restart clears conversations; this is documented in the README Known limits.
- **Why:** Adding a database would be out of scope for the assignment deadline. One instance avoids cross-instance session loss.
- **Alternatives rejected:** Redis or Firestore session store (out of scope for the deadline).
- **Status:** Active

### D-08: MAX_TOOL_ROUNDS
- **Date:** 2026-10-05
- **Decision:** Raise MAX_TOOL_ROUNDS from 5 to 8.
- **Why:** A full comparison (list_meetings, get_official_statement x2, compare_statements, track_commitments) can require 5 tool calls. 5 rounds left no margin.
- **Alternatives rejected:** Keeping 5 (would cut off before finishing a full comparison).
- **Status:** Active

### D-09: Snapshot format and storage
- **Date:** 2026-10-05
- **Decision:** Snapshots are stored as JSON at data/snapshots/{meeting_id}_{source_name}.json, containing url, retrieved_at (ISO-8601), language, and clean paragraphs (not raw HTML). Committed to the repo, never gitignored.
- **Why:** Cloud Run's filesystem resets on restart. If snapshots are not in the repo, fallback fails in production. JSON with clean paragraphs is easier to test against than raw HTML.
- **Alternatives rejected:** Cloud Storage bucket (out of scope for the deadline); gitignoring snapshots (would break Cloud Run fallback).
- **Status:** Active

### D-10: Quote verification rules
- **Date:** 2026-10-05
- **Decision:** A quote passes only if it is an exact substring of one source paragraph after normalizing whitespace and quote marks, AND it is at least 6 words long.
- **Why:** Exact substring matching ensures no paraphrasing reaches the user. The 6-word minimum prevents trivially short matches (single words, short phrases) from passing as meaningful quotes.
- **Alternatives rejected:** Fuzzy matching (could pass near-misses and misrepresent the source).
- **Status:** Active

### D-11: Comparison labels
- **Date:** 2026-10-05
- **Decision:** Use five labels: same, different_framing, contradiction (claims that cannot both be true), only_us, only_china. Each row includes a one-sentence reason. Code verifies quotes; the label and reason are the model's judgment.
- **Why:** Four original labels (both, only_us, only_china, contradiction) did not distinguish cases where both sides address a topic with different emphasis from cases where their claims are logically incompatible.
- **Alternatives rejected:** Original four-label set (both / only_us / only_china / contradiction) -- too coarse for framing differences.
- **Status:** Active

### D-12: Comparison consistency
- **Date:** 2026-10-05
- **Decision:** The comparison model call uses temperature 0, and results are cached per meeting (keyed by meeting_id, topic normalized to lowercase with empty string for no topic, and a sha256 hash of both source texts).
- **Why:** Temperature 0 gives deterministic output. Caching means every user sees the same table and avoids redundant model calls.
- **Alternatives rejected:** No caching (each request would re-run the model call and potentially produce slightly different results).
- **Status:** Active

### D-13: Commitment data
- **Date:** 2026-10-05
- **Decision:** Commitments are hand-curated for reliability. Each entry stores the exact quote, the original deadline wording, the interpreted deadline date, and the source URL. A test confirms each quote exists in the snapshot.
- **Why:** Extracting commitments automatically from statement text is unreliable for a deadline-driven project. Hand curation with exact quotes and a test gives a verifiable baseline.
- **Alternatives rejected:** Automatic extraction via model (harder to verify, risk of invented dates or misquotes).
- **Status:** Active

### D-14: Dropped row transparency
- **Date:** 2026-10-05
- **Decision:** Rows dropped by quote verification are reported to the user ("N rows hidden because quotes could not be verified"), never hidden silently.
- **Why:** Silent drops would make the tool appear more complete than it is and could hide bugs in the verification logic.
- **Alternatives rejected:** Silent drop with only a server log (hides failures from the user).
- **Status:** Active

### D-15: Neutrality (amended)
- **Date:** 2026-10-05
- **Decision:** For meeting comparisons, the tool reports what each side says and where the texts differ. It never judges which government is right, uses loaded words, or speculates about motives. Claim checks are the exception: check_claim returns a verdict, but only by applying the fixed rules in D-31, D-33, and D-34 to official source data. The verdict follows the plain reading of the claim; no editorial judgment is involved.
- **Why:** The intended users are journalists, students, and analysts who need the raw comparison, not an editorial opinion. Claim checks are different in kind: the verdict is a mechanical comparison of a stated number against an official source, not a political judgment.
- **Alternatives rejected:** Applying neutrality equally to claim checks (would prevent ever saying a number is wrong, even when official data clearly contradicts it).
- **Status:** Active

### D-17: HTML parsing library
- **Date:** 2026-10-05
- **Decision:** Use beautifulsoup4 with the lxml parser for HTML extraction.
- **Why:** Real government HTML from whitehouse.gov and the Chinese MFA sites has inconsistent structure and occasional malformed markup. lxml handles these more robustly than stdlib html.parser.
- **Alternatives rejected:** stdlib html.parser (less robust on real-world government HTML; no CSS selector support).
- **Status:** Active

### D-16: URL safety
- **Date:** 2026-10-05
- **Decision:** Tools only fetch URLs listed in config/sources.toml. They never fetch URLs from user input or model output.
- **Why:** Allowing arbitrary URL fetches would let a user (or a prompt-injected model response) cause the server to make outbound requests to arbitrary hosts.
- **Alternatives rejected:** Allowlist checked at runtime from user input (adds complexity without benefit; config/ is the right place for trusted URLs).
- **Status:** Active

### D-18: Two cases
- **Date:** 2026-10-05
- **Decision:** The app covers exactly two cases: `washington_2026_09` (type = "meeting") and `medicare_checks_2026_10` (type = "claim_check"). The top-level key in sources.toml is `cases`, with a `type` field per case. The `meetings` key used in Phase A is renamed to `cases` in Phase B when sources.py is updated.
- **Why:** A single config key with a type field is cleaner than separate `[meetings.*]` and `[cases.*]` sections, and it keeps list_cases trivial to implement.
- **Alternatives rejected:** Separate top-level keys per case type (redundant structure; list_cases would need to merge them).
- **Status:** Active

### D-19: Medicare claim check approved
- **Date:** 2026-10-05
- **Decision:** The Medicare Part B premium case is approved for Phase M. Three claims (C1 at_least, C2 approximately, C3 direction) will be checked against official CMS and WH sources. Anchor sentences and exact URLs are confirmed during the Phase M feasibility check; sources.toml and claims.toml use "TODO" placeholders until then.
- **Why:** The Guardian Medicare search returned only false positives (no articles about the specific premium claims), confirming there is no viable press side for this case. The checkable numbers are unambiguous in the official sources.
- **Alternatives rejected:** Soybeans case (Guardian search returned only keyword false positives; no article mentioned the claimed figures).
- **Status:** Active

### D-20: Guardian API approved for washington_2026_09
- **Date:** 2026-10-05
- **Decision:** The Guardian API is approved as a press side for the washington_2026_09 case. Two curated article IDs are stored in config/sources.toml. The API is only called for those IDs; no search queries are issued at runtime. The first curated article mentions both AI naming terms and Taiwan. The second mentions Taiwan and a reported weapons offer. Word counts change when articles are amended and are not used in any logic. Revised 2026-10-06.
- **Why:** Both curated articles are substantive and directly cover the meeting topics. Curated selection confirmed by manual review.
- **Alternatives rejected:** Live blog articles from the same search (live blog type confirmed via Guardian API; those articles aggregate many unrelated updates and are not suitable for topic-by-topic comparison).
- **Status:** Active

### D-21: Live blogs excluded from press_articles
- **Date:** 2026-10-05
- **Decision:** Live blogs are identified by the Guardian API `type` field value `"liveblog"` and excluded from press_articles. Curated IDs are manually reviewed before being added to config.
- **Why:** Live blog articles aggregate many unrelated updates into a single URL. A comparison against them would produce noisy, hard-to-attribute rows. Using the API type field is more reliable than a wordcount threshold.
- **Alternatives rejected:** Wordcount threshold (a long feature article would be excluded; a short live blog summary would pass); including all returned articles from a keyword search (returns live blogs, opinion pieces, and off-topic results).
- **Status:** Active

### D-22: Content-free press citation record, 23-hour cache (replaced)
- **Date:** 2026-10-05, revised 2026-10-06
- **Decision:** Guardian developer terms (Open Platform terms, section 5 Lifecycle) require replacing or deleting all Open Platform content at least every 24 hours, and they forbid editing that content. They also require attribution: headline, byline, and link. Fetched paragraphs stay in memory and expire after 23 hours, as does any compare_statements cache entry that contains press quotes. data/press_citations/ stores, per verified quote, the article url, headline, byline, paragraph id, published, retrieved_at, attributed_to, and a SHA-256 hash of the exact displayed quote. It stores no Guardian quote text. The only writer is `uv run python press.py --save-citations`. `uv run python press.py --verify-citations` re-fetches the articles and confirms each hash still matches a span of its paragraph. compare_statements does not read or write the file. Test mocks still use invented text only.
- **Why:** Storing the quote, or trimming it with an ellipsis, keeps or edits Open Platform content past the terms. A hash can be checked against a fresh fetch without keeping the sentence. 23 hours is inside the 24-hour replacement window.
- **Alternatives rejected:** Keeping quotes of 25 words or fewer (still Open Platform content); using the file as a fallback when the API is down (it would freeze an amended article); a process-lifetime cache (it can outlive 24 hours).
- **Status:** Active

### D-23: Press spans over the word limit are dropped; rows show attribution (replaced)
- **Date:** 2026-10-05, revised 2026-10-06
- **Decision:** A press span must be 6 words up to the limit in D-48. A longer span is dropped and counted. There is no trim and no "...". Every press row shows the article headline, byline, and link. Official-side quotes take headline (display_name) and published from that source in config. Eval checks use paragraph id, label, attributed_to, and 1 to 3 keywords. They do not copy Guardian phrases.
- **Why:** An ellipsis edits the sentence, which the developer terms forbid. Dropping the long span leaves the source untouched. Headline, byline, and link are the attribution the terms require.
- **Alternatives rejected:** Trimming to 25 words plus "..." (that edits the content; see D-24, now replaced).
- **Status:** Active

### D-24: Press spans trimmed at 25 words, never dropped for length
- **Date:** 2026-10-05, replaced 2026-10-06
- **Decision:** Withdrawn. Press spans are not trimmed. See D-23.
- **Why:** The Guardian developer terms forbid altering Open Platform content. Adding "..." is an edit.
- **Alternatives rejected:** Keeping the trim.
- **Status:** Replaced

### D-25: compare_statements label set applies to every pair
- **Date:** 2026-10-05
- **Decision:** compare_statements uses the same five labels for every left/right pair: same, different_framing, contradiction, only_{left}, only_{right}. When comparing us vs china the labels are only_us and only_china (as in D-11). When either side is press, the labels become only_{side} (for example, only_press or only_us depending on which side is missing the topic). The left and right side names are substituted literally into the label string. "contradiction" requires both sides to make explicit, incompatible factual claims about the same thing -- claims that cannot both be true. Different terms for the same concept, differences in emphasis, and one side not mentioning something are never contradiction.
- **Why:** A single label set works for any pair. Hardcoding only_us and only_china into the label set would require adding new labels every time a new side is introduced. The strict contradiction definition prevents the model from overusing it when "different_framing" or "only_{side}" is more accurate.
- **Alternatives rejected:** Separate label sets per pair type (adds complexity with no benefit; the meaning is identical); loose contradiction definition (would label naming differences as contradictions, which misrepresents the texts).
- **Status:** Active

### D-26: Guardian API key loaded lazily
- **Date:** 2026-10-05
- **Decision:** The Guardian API key is read lazily inside the press tool, never at import time or app startup. The app reads `/secrets/guardian.toml` on Cloud Run (mounted via Secret Manager) or `config/secrets.toml` locally (gitignored). If neither file exists, the press tool returns `{"error": "press side unavailable"}` rather than raising an exception.
- **Why:** Lazy loading means the app starts and serves other tools even if the secrets file is absent. Mounting at `/secrets/guardian.toml` (not inside `/app/config/`) avoids shadowing `config/sources.toml` and `config/claims.toml`.
- **Alternatives rejected:** Environment variable (not version-controllable; harder to audit); eager load at startup (crashes the whole app if the secrets file is missing).
- **Status:** Active

### D-27: Press articles are curated, never searched
- **Date:** 2026-10-05
- **Decision:** Article IDs for the press side are hand-curated and stored in `press_articles` in config/sources.toml. The app never issues a Guardian search query at runtime. Adding a new meeting requires adding curated IDs manually after review.
- **Why:** Runtime search returns live blogs, opinion pieces, and off-topic results. Curation ensures only substantive, relevant articles appear in the comparison.
- **Alternatives rejected:** Runtime keyword search (unpredictable results; live blogs and false positives confirmed in the feasibility spike).
- **Status:** Active

### D-28: check_claim replaces track_commitments
- **Date:** 2026-10-05
- **Decision:** The original `track_commitments` tool (honest status based on today's date) is replaced by `check_claim` (fact-check a specific numerical claim against an official source with verified arithmetic).
- **Why:** check_claim is more verifiable (code checks the number, not the model), more original, and satisfies the assignment's "at least 1 original tool" requirement more clearly. track_commitments as originally designed would require hand-curating commitment dates, which is high-maintenance for minimal benefit.
- **Alternatives rejected:** Keeping track_commitments alongside check_claim (scope creep; two original tools are not required).
- **Status:** Active

### D-29: Truth Social post text hard-coded in claims.toml
- **Date:** 2026-10-05
- **Decision:** The verbatim text of the Trump Truth Social post that is the source for claims C1, C2, and C3 is stored in `config/claims.toml`. The `original_url` field is set to "TODO" pending manual lookup. The UI and README disclose that the post text is hard-coded and the URL is pending.
- **Why:** The post cannot be fetched reliably. Hard-coding the verbatim text is the only option. A "TODO" URL is honest; an invented URL would violate the rule against inventing URLs.
- **Alternatives rejected:** Fetching the post at runtime (not reliably possible); omitting the post and using a speech transcript instead (the Truth Social post makes specific, unambiguous numerical claims that map directly to the at_least, approximately, and direction rules).
- **Status:** Active

### D-30: Python Decimal arithmetic for all dollar amounts
- **Date:** 2026-10-05
- **Decision:** All dollar arithmetic in claim_check.py uses `decimal.Decimal` to avoid floating-point errors. Arithmetic expressions are generated as strings by code (not by the model) and stored in the result for transparency. `pct_change` is rounded to one decimal place using `ROUND_HALF_UP` (for example, 9.675% rounds to 9.7%).
- **Why:** `185.00 + 17.90` in float arithmetic can produce `202.89999...`. Decimal gives exact results. Storing the expression string lets the UI show how numbers were derived. ROUND_HALF_UP matches the conventional rounding expectation for displayed percentages.
- **Alternatives rejected:** Float arithmetic (rounding errors in dollar amounts); asking the model to compute the arithmetic (model arithmetic is unreliable and unverifiable); ROUND_HALF_EVEN (less intuitive for percentages displayed to users).
- **Status:** Active

### D-31: Claim rules are general, dispatched by claim_type
- **Date:** 2026-10-05
- **Decision:** Each claim in claims.toml has a `claim_type` field: `at_least`, `approximately`, or `direction`. claim_check.py implements one named function per type. No verdict string ever appears in config. `direction("decrease", 0)` returns "contradicted" (zero change does not confirm a decrease).
- **Why:** General rules are testable with synthetic numbers independent of the specific claims. Keeping verdicts out of config prevents anyone from hard-coding a desired outcome.
- **Alternatives rejected:** Per-claim verdict logic in code (not reusable; harder to test); including expected verdicts in config (would make the tool a lookup, not a computation).
- **Status:** Active

### D-32: Press rows carry attributed_to
- **Date:** 2026-10-05
- **Decision:** Every press comparison row includes an `attributed_to` field. When the press article reports that a specific person or official made the claim in the row, `attributed_to` names that person. When the row reflects the outlet's own reporting or synthesis, `attributed_to` is null.
- **Why:** Press articles often paraphrase officials. Showing who the press attributes the claim to lets users distinguish "the outlet's analysis" from "official X said this, per the outlet".
- **Alternatives rejected:** Always null (loses attribution information); always the article byline (the byline is the author, not the claim's source).
- **Status:** Active

### D-33: check_claim verdict set and context_note rules
- **Date:** 2026-10-05
- **Decision:** check_claim returns one of four verdicts: supported, imprecise, contradicted, not_checkable. The verdict follows the plain reading of the claim as stated. Any other reasonable reading of the claim that would change the verdict goes in an optional `context_note`, never in the verdict itself. A context_note must cite a verified source sentence, subject to the same verification rules as comparison quotes (exact substring, minimum 6 words, after normalization).
- **Why:** A single plain-reading verdict is unambiguous and reproducible. Burying alternative interpretations in the verdict would make the verdict depend on editorial judgment. A verified context_note lets users see the nuance without it overriding the result.
- **Alternatives rejected:** Multiple verdicts per claim (confusing; the rule is meant to give one answer); unverified context_notes (could introduce invented or misquoted context).
- **Status:** Active

### D-34: approximately thresholds
- **Date:** 2026-10-05
- **Decision:** The approximately rule uses the claimed value as the denominator. Thresholds: difference <= 5% of claimed value is supported; <= 25% is imprecise; > 25% is contradicted. A difference of exactly 5% is supported; exactly 25% is imprecise. These thresholds are shown on the claim card in the UI.
- **Why:** Using the claimed value as denominator measures how far off the claim is from its own stated number, which is the natural reading. Displaying the thresholds lets users see why the verdict was assigned without having to read the code.
- **Alternatives rejected:** Official value as denominator (measures how far the official is from the claim, which is harder to interpret); hiding thresholds from the UI (users cannot verify the verdict without them).
- **Status:** Active

### D-35: Post reference, claimed_phrase verification, and C3 cross-check
- **Date:** 2026-10-05
- **Decision:** Each claim in claims.toml references a named post by ID. Before applying any rule, code verifies that `claimed_phrase` is an exact substring of the post's `verbatim_text`. If not, verdict is `not_checkable` with reason "claimed_phrase not found in post text". For C3 (direction), code additionally extracts the increase amount CMS explicitly states using `regex_stated_change` on the anchor sentence, then verifies it matches the computed difference (after - before). If they differ, verdict is `not_checkable` with reason "stated and computed changes do not match". Phase M tests include: `test_claimed_phrase_not_in_post` (not_checkable), `test_c3_cross_check_mismatch` (not_checkable). Phase M test `test_c3_contradicted` checks for fields 2025_premium, 2026_premium, monthly_change, pct_change, annual_change (annual_net_of_payment is not returned).
- **Why:** Verifying claimed_phrase keeps the connection between the claim and its source text explicit and machine-checkable. The C3 cross-check catches the case where a regex extracts the wrong number from the anchor sentence -- for example, a number from an adjacent sentence that slips into the match.
- **Alternatives rejected:** Trusting the claimed_phrase without checking (would silently pass claims whose source text was edited); skipping the cross-check (would not catch CMS page changes that affect the arithmetic).
- **Status:** Active

### D-36: AI naming is different_framing; contradiction definition
- **Date:** 2026-10-05
- **Decision:** The AI naming row for washington_2026_09 is labeled "different_framing", not "contradiction". The US statement says both leaders agreed to use "super intelligence"; China's English statement says nothing about terminology and uses "AI" throughout. That is omission plus different wording, not an explicit incompatible claim. "contradiction" in compare_statements is reserved for cases where both sides make explicit factual claims that cannot both be true (see D-25). check_claim's "contradicted" verdict (Medicare C3) is separate and follows D-31/D-33; that verdict is mechanically derived from numbers, not from the label set here.
- **Why:** Calling the AI naming row a contradiction would imply China's text denies the US claim. It does not -- China's text simply uses "AI" without addressing the terminology question.
- **Alternatives rejected:** contradiction label (misrepresents China's text as a denial); ignoring the naming difference (would hide the most newsworthy divergence in the statements).
- **Status:** Active

### D-37: Pairing rule added to compare_statements prompt
- **Date:** 2026-10-05
- **Decision:** The compare_statements prompt includes a pairing rule: a row may only pair two quotes that address the same specific item or commitment. If each side mentions a different item under the same broad topic, the model must return separate only_{left} and only_{right} rows instead of a single different_framing row. This rule is part of the prompt text and enforced at PROMPT_VERSION="3".
- **Why:** Without this rule, broad topics (e.g., "military") caused the model to pair unrelated items as different_framing -- for example, the US Indo-Pacific line paired with China's MOU on crisis communication. That pairing is wrong: the two quotes are about different commitments, not different framings of the same commitment.
- **Alternatives rejected:** Post-hoc heuristic to split paired rows (too fragile; depends on quote content); keeping v2 prompt (eval confirmed the broad-military eval row fails without this rule).
- **Status:** Active

### D-38: C1 noun difference is outside the at_least rule
- **Date:** 2026-10-05
- **Decision:** C1 verdict is "supported". The at_least rule compares numbers only. The WH fact sheet says "more than 20 million enrollees"; the post says "over 20 MILLION wonderful Seniors". "Enrollees" and "Seniors" are different nouns. This difference is not evaluated by the at_least rule; the number (20,000,000) meets or exceeds the claimed value (20,000,000).
- **Why:** The rule is about the numerical claim, not the descriptive noun. The WH itself titles the section "IMPROVING MEDICARE FOR SENIORS", making clear the enrollees referred to are seniors. Expanding the rule to check noun alignment would require natural-language judgment that belongs in the model's response, not in the arithmetic rule.
- **Alternatives rejected:** Returning not_checkable when nouns differ (overcomplicates the rule; the numerical check is what the tool is for); ignoring the noun difference.
- **Status:** Active

### D-39: context_note format: fixed lead-in plus verbatim verified CMS sentence
- **Date:** 2026-10-05
- **Decision:** The context_note field in check_claim results uses a fixed lead-in ("CMS also states:") followed by the verbatim sentence from the source containing the context_note_check anchor. The sentence is extracted by code (splitting on sentence boundaries in the paragraph), verified as an exact substring of the source (same rules as comparison quotes), and concatenated with the lead-in. The model never writes or summarizes the context_note text. If the anchor is not found in the source, context_note is null and the reason includes "sentence not found in source".
- **Why:** A code-generated context_note from a verified source sentence cannot contain invented or misquoted text. Requiring the model to write the context_note would risk paraphrase and introduce a second model call with unverifiable output.
- **Alternatives rejected:** Model-written context_note (unverifiable; paraphrase risk); no context_note for C3 (users would see only "contradicted" with no nuance about the administration's framing of the increase).
- **Status:** Active

### D-40: Claim cards show source name plainly with link; no editorial notes
- **Date:** 2026-10-05
- **Decision:** The UI shows the source citation on claim cards as plain text with a link, for example "Checked against: White House fact sheet, Oct 2, 2026 [link]". No editorial notes (e.g., "published by the administration" or "as reported by CMS") are added. The source is described by its name and date only.
- **Why:** Editorial notes are subjective and can introduce bias. The user can follow the link and assess the source. The tool's job is to report what the source says, not to editorialize about who published it.
- **Alternatives rejected:** Adding editorial context to the source citation (introduces bias; violates the neutrality rule in CLAUDE.md); omitting the source link (users could not verify the claim).
- **Status:** Active

### D-41: Anchors and markers are number-free; regexes run on the sentence containing the anchor
- **Date:** 2026-10-05
- **Decision:** Anchors in claims.toml contain no numbers. An anchor locates the sentence; regex patterns extract numbers from that sentence only. `_extract_number` in claim_check.py calls `_extract_sentence` to scope regex search to the sentence, not the full paragraph. This means if a source updates a number, regexes pick it up from the live page; the anchor still matches because it does not contain the old number. Year labels in regexes ("for 2026", "in 2025") are fine; they are search constraints, not answers. Markers in sources.toml also contain no numbers for the same reason: a number-containing marker breaks if the source corrects a figure, causing the live page check to fail and the tool to fall back to the outdated snapshot.
- **Why:** Number-containing anchors break when the source corrects a figure: the anchor phrase is no longer on the page, so the claim returns not_checkable even if the correct data is present. Sentence-scoped regexes also prevent numbers in adjacent sentences (e.g., deductible amounts in the same paragraph) from being captured by mistake.
- **Alternatives rejected:** Number-containing anchors with a fallback mechanism (adds complexity without solving the root problem); paragraph-scoped regexes (risk of matching the wrong sentence's numbers).
- **Status:** Active

### D-42: C1 and C2 checks labels renamed to match source language
- **Date:** 2026-10-05
- **Decision:** The `label` field for C1's checks dict is `enrollee_count`, matching the word the official source uses ("enrollees"). The previous label was `senior_enrollment_count`. The `label` field for C2's checks dict is `payment_per_person_usd`, matching the source phrase "per person". The previous label was `payment_per_senior_usd`.
- **Why:** The WH fact sheet says "more than 20 million enrollees" and "payments of $90 per person". Labels should match the source language so the config is self-consistent and auditable.
- **Alternatives rejected:** Keeping old labels (inconsistent with source text; labels that differ from source phrasing require cross-referencing to understand).
- **Status:** Active

### D-43: One internal fetch function replaces duplicate live-first logic
- **Date:** 2026-10-05
- **Decision:** `get_official_source` and `fetch_source_by_name` now share two internal helpers: `_try_live(config, source, required_anchors=None)` and `_try_snapshot(case_id, source_name, required_anchors=None)`. A live page counts as usable only if: HTTP 200, marker found, at least one paragraph extracted, and every required anchor found. If the live page returns 200 but fails any check, `live_changed=True`. `check_claim` passes `required_anchors=[checks_anchor]` so that a live page lacking the anchor falls back to snapshot. If snapshot also lacks the anchor, `fetch_source_by_name` returns `{"anchor_missing": True, ...}` and `check_claim` converts that to not_checkable with reason "anchor not found in live page or snapshot". `get_official_source` (meeting cases) passes `required_anchors=None`.
- **Why:** The duplicate live-first logic in both functions was identical except for the anchor check. A single internal function reduces the surface area for bugs when the fetch validity rules change.
- **Alternatives rejected:** Keeping separate functions (maintenance burden; any rule change must be applied twice); merging into one public function (meeting and claim-check cases have different call signatures and return shapes).
- **Status:** Active

### D-44: Press prompt version is separate from us vs china
- **Date:** 2026-10-06
- **Decision:** Press comparisons use a numbered-paragraph prompt, PROMPT_VERSION "7". The model returns a paragraph id and a span of 6 to 40 words (D-48). Each quote may be used in at most one row, and a quote may not be paired with a quote about a different event or commitment. If only one side has a quote, the label must be only_{that side}. A row without both quotes is never same, different_framing, or contradiction. attributed_to is required when the press quote reports what a named person said. "allies with China" and "the CCP was not an ally" can both be true, so that pair is different_framing, not contradiction. US vs China stays on prompt version "3". The v3 prompt text and the paragraph strings it receives were not changed when display_name and published were added.
- **Why:** The press articles need paragraph ids that are unique across the two pieces (A1-P1, A2-P1). Changing the US vs China prompt would risk the rows that already pass.
- **Alternatives rejected:** One prompt version for every pair (would resend the US vs China rows through a new prompt); searching the span in any paragraph (a span can be true of the wrong paragraph).
- **Status:** Active

### D-45: AI naming pairs differ by who is speaking
- **Date:** 2026-10-06
- **Decision:** For us vs china, AI naming stays different_framing: the US super intelligence agreement paired with the China-U.S. AI Dialogue (D-36, unchanged). For china vs press, the row is only_press. The Guardian line is about what Trump called the technology, not about the dialogue's name, so the pairing rule forbids joining them.
- **Why:** Those are two items. Pairing them would repeat the broad-topic mistake D-37 already rejected.
- **Alternatives rejected:** different_framing for china vs press (pairs a name Trump used with a dialogue China announced); contradiction (China's statement does not deny the wording).
- **Status:** Active

### D-46: China source is the Eight Deliverables statement only
- **Date:** 2026-10-06
- **Decision:** The China side is the MFA English "Eight Deliverables" statement (and its gov.cn and Embassy mirrors, then the snapshot). China's separate Xinhua talks readout is not a source. When attributed_to mentions Xinhua, code adds the source_note in D-49. The model does not write that sentence.
- **Why:** The readout is a different document. Treating it as China's statement would make a press paraphrase look like the official text.
- **Alternatives rejected:** Adding the Xinhua readout as another China source (it was not fetched or snapshotted as an official source); ignoring the attribution and labeling the row as China's position.
- **Status:** Active

### D-47: Press verification compares words, then displays the source text
- **Date:** 2026-10-06
- **Decision:** A press span is verified by comparing word sequences with punctuation removed: the same words, in the same order, at least 6 words, inside the named paragraph. On a match, the displayed quote is the exact substring of the source paragraph, never the model's text. Official quote verification is unchanged: exact substring after normalize_text, minimum 6 words (D-10).
- **Why:** The model sometimes moves a comma inside a closing quotation mark. That is still the same words. Showing the model's text would display an edited sentence, which the Guardian developer terms forbid. Showing the source substring keeps the article's punctuation.
- **Alternatives rejected:** Exact character match for press spans (drops a quote when only a comma moved); displaying the model's text after a word match (that can differ from the article); applying the word match to official quotes (D-10 stays exact).
- **Status:** Active

### D-48: Press span limit is 40 words
- **Date:** 2026-10-06
- **Decision:** A press span must be 6 to 40 words as returned. A longer span is dropped and counted with the reason "span over 40 words". Spans are never trimmed and never shown with "...". That instruction is in the press prompt. US vs China stays on version "3".
- **Why:** The old 25-word cap was our own copyright caution, not a Guardian rule. Guardian developer terms forbid editing content, which is why a long span is dropped instead of cut. 40 words keeps a complete sentence that 25 often split.
- **Alternatives rejected:** Keeping 25 words (it dropped WWII and other rows that were a single sentence); trimming at 40 words (that would edit the sentence).
- **Status:** Active

### D-49: Xinhua source_note is written by code
- **Date:** 2026-10-06
- **Decision:** If a press row's attributed_to mentions "Xinhua", code sets source_note to "Cites a Xinhua readout, which is not the China source used here." Otherwise source_note is null. The model never writes this sentence. The eval check is that the row has this exact source_note. Same pattern as D-39: fixed text from code, not from the model.
- **Why:** The behavior moved from the model to code, so the check is deterministic, not looser. Asking the model to write the sentence produced a different reason on every run.
- **Alternatives rejected:** Leaving the sentence in the model's reason (the check failed whenever the model put Xinhua only in attributed_to); dropping the check (that would hide whether the note is present).
- **Status:** Active

### D-50: Cloud Run reachability and the Guardian secret
- **Date:** 2026-10-06
- **Decision:** From Cloud Run in europe-west1, the White House, CMS, and the Guardian API all returned HTTP 200, and the secret file mount works. Secret guardian-secrets version 1 already exists. The default compute service account (655901547612-compute@developer.gserviceaccount.com) has secretAccessor. Phase G only needs to mount that secret (`--update-secrets=/secrets/guardian.toml=guardian-secrets:latest`) and set max-instances to 1. Before the mount, confirm the service runs as that default compute service account.
- **Why:** The earlier deploy plan treated reachability and the secret as untested. Both are done. Recreating the secret or guessing the service account would be extra work.
- **Alternatives rejected:** Creating a new secret (version 1 is already there); mounting the secret over /app/config/ (that would hide sources.toml and claims.toml).
- **Status:** Active

### D-51: Sentence-length evidence and actionable tool errors
- **Date:** 2026-10-06
- **Decision:** check_claim evidence_quote is the sentence that contains the anchor, not the whole paragraph. C3's arithmetic string shows the monthly change and then the yearly change as 17.90 x 12. Every error a tool returns tells the model the next step, such as calling list_cases or using the other tool.
- **Why:** A real Medicare answer quoted the deductible sentence next to the premium sentence. A tool error that only says what failed does not tell the model how to recover.
- **Alternatives rejected:** Leaving the full paragraph (it mixes in numbers the claim does not use); keeping short errors such as "press side unavailable" with no next step.
- **Status:** Active

### D-52: Secret mount, instance cap, open pull request, and Markdown answers
- **Date:** 2026-10-06
- **Decision:** The Cloud Run service runs as 655901547612-compute@developer.gserviceaccount.com. Secret guardian-secrets is mounted at /secrets/guardian.toml, and max instances is 1. Revision gemini-web-tool-calling-git-00004-l6s is serving. Pull request 1 is open from feature/two-readouts to main and is not merged. The page renders the assistant answer as Markdown (bold and lists) and sanitizes it. The model is told to use short paragraphs and simple lists, with bold only for verdicts and key terms.
- **Why:** The service account is the default compute account, which already has secretAccessor, so the mount did not need a new binding. Graders were seeing raw asterisks instead of bold text and lists.
- **Alternatives rejected:** Merging the pull request from here (the owner merges); rendering Markdown without sanitizing it.
- **Status:** Active

### D-53: Source metadata, the post text, and the Chinese term flags
- **Date:** 2026-10-06
- **Decision:** After the comparison model call, each compare_statements result includes left_source and right_source with display_name, published, url, live, and live_changed. The prompt and the cache key stay the same. check_claim includes post.verbatim_text from config. A term_check row includes terms, a map of 人工智能 and 超级智能 to true or false. The page reads that map and does not read the reason text.
- **Why:** The page has to show dates, live or snapshot, the post with the claimed words highlighted, and the two Chinese terms. Those facts were either missing or only written inside a sentence.
- **Alternatives rejected:** Changing the comparison prompt to ask for dates (the dates are already in config); parsing the reason sentence in the browser.
- **Status:** Active

### D-54: Display name is Check Their Truths
- **Date:** 2026-10-06
- **Decision:** Display name changed to Check Their Truths (previously Two Readouts) because the project now compares three sources and checks claims, and 'readout' is unfamiliar jargon. Internal names unchanged so the deploy URL stays stable.
- **Why:** The old name described two official readouts. The project now also compares Guardian coverage and checks Medicare claims, and "readout" is jargon.
- **Alternatives rejected:** Renaming the repo, the branch, the Cloud Run service, or the deploy URL.
- **Status:** Active
