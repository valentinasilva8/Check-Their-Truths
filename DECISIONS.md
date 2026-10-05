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
| D-15 | 2026-10-05 | Neutrality: report differences, never judge who is right | Active |
| D-16 | 2026-10-05 | Safety: tools only fetch URLs from config/sources.toml | Active |

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
- **Decision:** The comparison model call uses temperature 0, and results are cached per meeting (keyed by meeting_id and a hash of the source texts).
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

### D-15: Neutrality
- **Date:** 2026-10-05
- **Decision:** The tool reports what each side says and where the texts differ. It never judges who is right, uses loaded words, or speculates about motives.
- **Why:** The intended users are journalists, students, and analysts who need the raw comparison, not an editorial opinion.
- **Alternatives rejected:** None
- **Status:** Active

### D-16: URL safety
- **Date:** 2026-10-05
- **Decision:** Tools only fetch URLs listed in config/sources.toml. They never fetch URLs from user input or model output.
- **Why:** Allowing arbitrary URL fetches would let a user (or a prompt-injected model response) cause the server to make outbound requests to arbitrary hosts.
- **Alternatives rejected:** Allowlist checked at runtime from user input (adds complexity without benefit; config/ is the right place for trusted URLs).
- **Status:** Active
