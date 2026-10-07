# DESIGN.md

## 1. Folder structure

```
app.py                  existing -- MAX_TOOL_ROUNDS=8, updated SYSTEM_PROMPT
tools.py                existing -- list_cases, get_official_source, compare_statements,
                                    get_press_coverage (Phase P), check_claim (Phase M)
index.html              existing -- update title, layout, comparison table
config/
  sources.toml          cases config (meeting + claim_check types)
  claims.toml           claim definitions for check_claim
data/
  snapshots/            committed to the repo; must be present before Cloud Run deploy
    washington_2026_09_us_fact_sheet.json
    washington_2026_09_china_mfa_english.json
    washington_2026_09_china_govcn_mirror.json
    washington_2026_09_china_embassy_mirror.json
    washington_2026_09_china_mfa_chinese_original.json
tests/
  test_sources.py       config loading, HTML extraction, fallback, URL safety
  test_compare.py       compare_statements: quote verification, label validation, cache
  test_claim_check.py   check_claim: verdict rules, Decimal arithmetic (Phase M)
  test_press.py         get_press_coverage: Guardian fetch, secrets, cache (Phase P)
docs/EVAL.md            expected rows checklist for the September 2026 meeting
```

No new packages needed beyond the starter deps.

---

## 2. Data model (Python dataclasses, not ORM)

```
Paragraph      index: int, text: str

Statement      case_id: str, side: str ("us", "china", or "press"),
               source_name: str, url: str, retrieved_at: str (ISO-8601),
               live: bool, live_changed: bool (True when a live 200 returned
               but the marker was absent; snapshot used instead),
               live_changed_note: str|None, language: str,
               paragraphs: list[Paragraph]

ComparisonRow  label: "same"|"different_framing"|"contradiction"|
                      "only_{left}"|"only_{right}",
               topic: str, reason: str (one sentence from the model),
               left_quote: str|None, left_url: str|None,
               right_quote: str|None, right_url: str|None,
               attributed_to: str|None (press rows: who the press says
               made the claim; null for the outlet's own reporting)
```

Tools serialize these to JSON strings (not dicts) before returning.

---

## 3. Tools

**list_cases** -- no arguments
- Description for model: "List every case this agent supports, with IDs, types (meeting or claim_check), names, and dates. Call this first when the user has not specified a case."
- Returns: `[{case_id, type, name, dates}]`
- Errors: "Config file not found at config/sources.toml." / "No cases configured."

**get_official_source(case_id: str, source: str)**
- Description: "Fetch the official statement for one side ('us' or 'china') of a meeting case. For China, tries MFA English, then gov.cn mirror, then Embassy mirror in priority order. Falls back to a saved snapshot if all live fetches fail, and says so. If a live 200 response returns but the marker is absent, falls back to the snapshot and sets live_changed=True."
- Returns: serialized Statement
- Errors: "Case '{id}' not found. Call list_cases to see supported cases." / "source must be 'us' or 'china', got '{x}'." / "get_official_source requires a meeting case." / "All live sources failed for {side}/{case_id} and no snapshot exists. Try again later."
- Snapshot path: `data/snapshots/{case_id}_{source_name}.json`
- Only fetches URLs listed in config/sources.toml -- never URLs from user input or model output.

**get_press_coverage(case_id: str)** -- added in Phase P
- Description: "Fetch Guardian press coverage for a meeting case. Returns headline, byline, url, published, and paragraphs for each curated article. Returns error if the API key is unavailable."
- Meeting cases only. Paragraphs cached in memory. Full article text is never committed (D-22).
- A content-free hash record is written only by `uv run python press.py --save-citations` into `data/press_citations/{case_id}.json` (url, headline, byline, paragraph id, published, retrieved_at, attributed_to, quote_sha256). `uv run python press.py --verify-citations` re-fetches and checks the hashes. compare_statements does not read or write that file. Press caches expire after 23 hours (D-22, D-23).

**compare_statements(case_id: str, topic: str = "", left: str = "us", right: str = "china")**
- Description: "Compare two sides' coverage of a case topic by topic. left and right can be 'us', 'china', or 'press'. Returns rows labeled 'same', 'different_framing', 'contradiction', 'only_{left}', or 'only_{right}'. Each row includes a reason, verified quotes, and attributed_to (press rows only). For the AI topic on washington_2026_09 also reports 人工智能 / 超级智能 presence. Unverifiable rows are reported, not dropped silently. Meeting cases only."
- Returns: `{case_id, topic, left, right, rows: [ComparisonRow], dropped: int, drop_reasons: [str]}`
- Errors: "compare_statements requires a meeting case." / "Could not load statements for '{case_id}': {reason}." / "No verifiable rows found for topic '{topic}'."

**check_claim(case_id: str, claim_id: str)** -- added in Phase M
- Description: "Fact-check a specific claim from a named post against official source data. Verifies the claimed_phrase is a substring of the post text. Applies the claim_type rule (at_least, approximately, direction) using Python Decimal arithmetic. Returns verdict (supported, imprecise, contradicted, not_checkable), numbers dict, arithmetic string, and optional context_note. Claim_check cases only."
- Returns: `{case_id, claim_id, verdict, numbers, arithmetic, context_note, source_url, live, live_changed}`
- Errors: "check_claim requires a claim_check case." / "Claim '{id}' not found." / "claimed_phrase not found in post text."

---

## 4. How compare_statements works

1. **Cache check**: build key `(case_id, topic.strip().lower(), left, right, PROMPT_VERSION, sha256(left_paragraphs + right_paragraphs))`. `PROMPT_VERSION` is a module-level constant in compare.py; bump it whenever the prompt changes. If a cached result exists for this key, return it immediately without a model call.
2. **Fetch**: call `get_official_source` internally for both sides (not via the model). For the AI topic, also load the Chinese original snapshot to run the term check in step 5.
3. **Model call (temperature=0)**: call the model once with a structured prompt that includes all paragraphs from both statements and the topic (if given). The prompt instructs the model to: group paragraphs by topic, select one verbatim quote per side per row, assign a label (same / different_framing / contradiction / only_{left} / only_{right}), and write one sentence explaining the label. The model must copy quotes character-for-character from the input -- it cannot rephrase. The prompt includes a strict definition of "contradiction": both sides must make explicit, incompatible factual claims; different terms, emphasis, or omission is never contradiction.
4. **Verify every quote**: for each quote the model returns, normalize the quote and its source paragraphs (collapse whitespace, convert curly/smart quotes to straight, replace non-breaking spaces). The quote passes only if it is an exact substring of at least one normalized paragraph AND is at least 6 words long. Quotes that fail are logged to `drop_reasons` and the row is removed.
5. **Chinese term check (AI topic or empty topic, china side involved)**: exact-match the Chinese original snapshot for 人工智能 and 超级智能 and append a special `term_check` row. This row is outside the regular label set, is not subject to quote verification, and is not counted toward the 12-row cap. It is always the last row in the result.
6. **Report dropped rows**: include `dropped` count and `drop_reasons` in the return value. The frontend displays "N rows hidden because quotes could not be verified."
7. **Return** verified rows, the term-check row if applicable, dropped count, and drop reasons. Store result in cache.

---

## 5. check_claim logic (Phase M)

Claims are defined in `config/claims.toml`. Each claim has a `claim_type` field: `at_least`, `approximately`, or `direction`. Before applying any rule, code verifies `claimed_phrase` is an exact substring of the post's `verbatim_text`; if not, verdict is `not_checkable`.

Rules (see D-31, D-33, D-34):
- `at_least`: official >= claimed_value -> supported; else contradicted
- `approximately`: |official - claimed_value| / claimed_value: <= 5% supported, <= 25% imprecise, > 25% contradicted
- `direction`: sign(after - before) matches claimed_direction -> supported; zero change or opposite sign -> contradicted

All arithmetic uses `decimal.Decimal` (see D-30). Arithmetic expressions are stored as strings for display. An optional `context_note` cites a verified source sentence providing another reasonable reading (see D-33). For C3, code additionally verifies the computed change matches the CMS-stated change; mismatch -> not_checkable (see D-35).

---

## 6. Frontend wireframe

```
+--------------------------------------------------+
|  TWO READOUTS                                    |
|  Official statements, side by side               |
+--------------------------------------------------+
|  [tool call] list_cases() -> ...            ^    |
|  [tool call] get_official_source(...)       |    |
|  [tool call] compare_statements(...)       chat  |
|                                             |    |
|  ASSISTANT                                  |    |
|  Both sides addressed AI, but with          v    |
|  different names. See table below.               |
|                                                  |
|  +--------------------------------------------+ |
|  | TOPIC | LABEL         | US       | CHINA   | |
|  | AI    | diff_framing  | "super   | "China- | |
|  |       | US uses       |  intelli-|  U.S.   | |
|  |       | "super intell-|  gence"  |  AI     | |
|  |       | igence"; China|  [src]   |  Dialog | |
|  |       | uses "AI"     |          |  ue"    | |
|  |       |               |          |  [src]  | |
|  +--------------------------------------------+ |
|  Chinese original: 人工智能 YES / 超级智能 NO        |
|  1 row hidden -- quotes could not be verified    |
|  [LIVE] whitehouse.gov  [SNAPSHOT Oct 5] MFA    |
+--------------------------------------------------+
|  Type a message...                    [Send]     |
+--------------------------------------------------+
```

The comparison table is rendered by the frontend directly from the `compare_statements` result inside `tool_calls`. The model's text response is the summary only -- the table content comes from the tool result, not from parsing the model's prose.

Tool calls collapse/expand. Each statement carries a green LIVE or yellow SNAPSHOT badge with date. Comparison table only appears when compare_statements runs.

---

## 7. Test plan

**pytest (automated)**

`tests/test_sources.py`
- Config loading, both case types present
- HTML extraction per site; boilerplate absent
- Snapshot fallback on network failure; live_changed flag when marker absent
- URL safety: non-config URLs refused

`tests/test_compare.py`
- `_normalize` and `_verify_quote` unit tests
- `compare_statements`: drops row with bad quote (dropped=1, drop_reasons has one entry per failed quote)
- `compare_statements`: 5-word quote dropped; 6-word quote kept
- `compare_statements`: invalid label dropped; contradiction missing right_quote dropped
- `compare_statements`: model returns invalid JSON -> error in result, no crash
- `compare_statements`: wrong case type -> error mentions "meeting"
- `compare_statements`: press side unavailable when the fetch fails; a span is kept only when its words match the named paragraph; spans over 40 words are dropped; a moved comma still verifies and the row shows the source punctuation
- Chinese term check fires for topic="ai", "artificial intelligence", empty; not for "coal trade"
- term_check row not counted toward 12-row cap; cap_hit reported
- Cache: second call with same inputs does not call model

`tests/test_claim_check.py` (Phase M)
- Verdict rules: at_least, approximately, direction with synthetic numbers
- Decimal arithmetic, ROUND_HALF_UP for pct_change
- claimed_phrase not in post -> not_checkable
- C3 cross-check mismatch -> not_checkable
- Million-word parsing for C1

`tests/test_press.py` (Phase P)
- Guardian fetch with mocked API and invented text; paragraph ids A1-P1, A2-P1; in-memory cache
- Secrets absent or API 500 -> "press side unavailable"
- Live blogs excluded
- Citation record rejects stored quote text, or a missing url, headline, byline, paragraph id, published, retrieved_at, or hash
- compare_statements does not write the citation file

**Manual**
- "Compare the Washington 2026 statements on AI" -- confirm "super intelligence" and "Eight Deliverables" appear as verbatim quotes with source links
- Block one China URL in /etc/hosts, confirm fallback to next source (or snapshot)
- Open two browser tabs; confirm separate sessions (different session_ids in network tab)
- Grader queries from README work end to end

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| Source URL goes down permanently | Snapshot fallback; badge tells user the date of the saved copy |
| Model returns a paraphrased quote | Verification drops it; drop_reasons reports the failure |
| Cloud Run restart wipes sessions | max instances=1; documented in README Known limits |
| compare_statements internal model call fails | Caught, returned as tool error JSON; harness surfaces as chat text |
| Claims anchors go stale after page update | C3 cross-check catches CMS figure changes; verdict becomes not_checkable |
| Model invents a label outside the valid set | Code validates label; invalid rows dropped and counted in drop_reasons |
