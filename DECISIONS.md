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
| D-20 | 2026-10-05 | Guardian API approved; Thucydides article mentions both AI terms and Taiwan; weapons article mentions Taiwan | Active |
| D-21 | 2026-10-05 | Live blogs excluded from press_articles; identified by Guardian API type field "liveblog" | Active |
| D-22 | 2026-10-05 | Guardian paragraphs cached in memory only, never written to disk | Active |
| D-23 | 2026-10-05 | Guardian bodyText never stored in repo; press test fixtures use invented text only | Active |
| D-24 | 2026-10-05 | Press spans over 25 words trimmed with "..."; rows never dropped for length | Active |
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
- **Decision:** The Guardian API is approved as a press side for the washington_2026_09 case. Two curated article IDs are stored in config/sources.toml. The API is only called for those IDs; no search queries are issued at runtime. The Thucydides trap article (1075 words) mentions both AI naming terms (super intelligence, artificial intelligence) and Taiwan. The weapons article (613 words) mentions Taiwan.
- **Why:** Both curated articles are substantive and directly cover the meeting topics. Curated selection confirmed by manual review.
- **Alternatives rejected:** Live blog articles from the same search (live blog type confirmed via Guardian API; those articles aggregate many unrelated updates and are not suitable for topic-by-topic comparison).
- **Status:** Active

### D-21: Live blogs excluded from press_articles
- **Date:** 2026-10-05
- **Decision:** Live blogs are identified by the Guardian API `type` field value `"liveblog"` and excluded from press_articles. Curated IDs are manually reviewed before being added to config.
- **Why:** Live blog articles aggregate many unrelated updates into a single URL. A comparison against them would produce noisy, hard-to-attribute rows. Using the API type field is more reliable than a wordcount threshold.
- **Alternatives rejected:** Wordcount threshold (a long feature article would be excluded; a short live blog summary would pass); including all returned articles from a keyword search (returns live blogs, opinion pieces, and off-topic results).
- **Status:** Active

### D-22: Guardian paragraphs cached in memory only
- **Date:** 2026-10-05
- **Decision:** Fetched Guardian article paragraphs are cached in memory for the lifetime of the process. They are never written to disk, the repo, or any snapshot file.
- **Why:** A Cloud Run restart clears the cache, but that is acceptable -- the next request re-fetches from the API. Writing press text to disk would complicate copyright compliance.
- **Alternatives rejected:** Snapshot-style JSON files for press articles (copyright risk; the in-memory cache is sufficient for single-instance Cloud Run).
- **Status:** Active

### D-23: Guardian text never stored in the repo
- **Date:** 2026-10-05
- **Decision:** Guardian article bodyText is copyrighted and is never written to the repo, fixtures, or snapshots. Test fixtures for press tests use invented text only.
- **Why:** Storing copyrighted article text in a public repo would be a copyright violation. Invented fixtures are sufficient to test extraction logic.
- **Alternatives rejected:** Using real article excerpts in tests (copyright risk; unnecessary given that invented text can exercise all code paths).
- **Status:** Active

### D-24: Press spans trimmed at 25 words, never dropped for length
- **Date:** 2026-10-05
- **Decision:** Press spans returned by the model are trimmed to the first 25 words followed by "..." if they exceed 25 words. The row is never dropped for length alone. A prefix of a verified span is itself a verified substring of the source paragraph.
- **Why:** Dropping rows for length would reduce coverage without improving accuracy. Trimming to 25 words keeps the UI readable while preserving verifiability.
- **Alternatives rejected:** Dropping rows over 25 words (reduces coverage; the full span is still verifiable even if the displayed text is trimmed).
- **Status:** Active

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
- **Alternatives rejected:** Returning not_checkable when nouns differ (overcomplicates the rule; the numerical check is what the tool is for); ignoring the noun difference in the result (it is noted in the reason field).
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

### D-35: Post reference, claimed_phrase verification, and C3 cross-check
- **Date:** 2026-10-05
- **Decision:** Each claim in claims.toml references a named post by ID. Before applying any rule, code verifies that `claimed_phrase` is an exact substring of the post's `verbatim_text`. If not, verdict is `not_checkable` with reason "claimed_phrase not found in post text". For C3 (direction), code additionally extracts the increase amount CMS explicitly states in `anchor_after` using `regex_stated_change`, then verifies it matches the computed difference (after - before). If they differ, verdict is `not_checkable` with reason "stated and computed changes do not match". Phase M tests include: `test_claimed_phrase_not_in_post` (not_checkable), `test_c3_cross_check_mismatch` (not_checkable). Phase M test `test_c3_contradicted` checks for fields 2025_premium, 2026_premium, monthly_change, pct_change, annual_change (annual_net_of_payment is not returned).
- **Why:** Verifying claimed_phrase keeps the connection between the claim and its source text explicit and machine-checkable. The C3 cross-check catches the case where the CMS page is updated with corrected figures that no longer match the stored anchor sentence.
- **Alternatives rejected:** Trusting the claimed_phrase without checking (would silently pass claims whose source text was edited); skipping the cross-check (would not catch CMS page changes that affect the arithmetic).
- **Status:** Active
