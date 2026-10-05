# DESIGN.md

## 1. Folder structure

```
app.py                  existing -- raise MAX_TOOL_ROUNDS to 8, update SYSTEM_PROMPT
tools.py                existing -- replace weather tool with 4 new tools
index.html              existing -- update title, layout, comparison table
config/
  sources.toml          existing
data/
  snapshots/            committed to the repo; must be present before Cloud Run deploy
    washington_2026_09_us_fact_sheet.json
    washington_2026_09_china_mfa_english.json
    washington_2026_09_china_govcn_mirror.json
  commitments/
    washington_2026_09.json   manually curated commitment list for the meeting
tests/
  test_verify.py        quote normalization and verification logic
  test_tools.py         each tool: happy path, fallback, error cases
EVAL.md                 expected rows checklist for the September 2026 meeting
```

No new packages needed beyond the starter deps.

---

## 2. Data model (Python dataclasses, not ORM)

```
Paragraph      index: int, text: str

Statement      meeting_id: str, side: "us"|"china", source_name: str,
               url: str, retrieved_at: str (ISO-8601), live: bool,
               language: str, paragraphs: list[Paragraph]

ComparisonRow  label: "same"|"different_framing"|"contradiction"|"only_us"|"only_china",
               topic: str, reason: str (one sentence from the model),
               us_quote: str|None, us_url: str|None,
               china_quote: str|None, china_url: str|None

Commitment     description: str, side: "us"|"china"|"joint",
               exact_quote: str, original_deadline_wording: str|None,
               interpreted_deadline: str|None (ISO date),
               status: str, source_url: str
```

Tools serialize these to JSON strings (not dicts) before returning.

---

## 3. Tools

**list_meetings** -- no arguments
- Description for model: "List every meeting this agent supports, with IDs, names, and dates. Call this first when the user has not specified a meeting."
- Returns: `[{meeting_id, name, dates}]`
- Errors: "Config file not found at config/sources.toml." / "No meetings configured."

**get_official_statement(meeting_id: str, side: str)**
- Description: "Fetch the official statement for one side ('us' or 'china'). For China, tries MFA English, then gov.cn mirror, then Embassy mirror in priority order. Falls back to a saved snapshot if all live fetches fail, and says so. Returns paragraphs, source URL, retrieval time, and live/snapshot flag."
- Returns: serialized Statement
- Errors: "Meeting '{id}' not found. Call list_meetings to see supported meetings." / "side must be 'us' or 'china', got '{x}'." / "All live sources failed for {side}/{meeting_id} and no snapshot exists. Try again later."
- Snapshot path: `data/snapshots/{meeting_id}_{source_name}.json`
- Only fetches URLs listed in config/sources.toml -- never URLs from user input or model output.

**compare_statements(meeting_id: str, topic: str = "")**
- Description: "Compare the US and China official statements for a meeting topic by topic. If topic is given (e.g. 'AI', 'trade'), only that topic is analyzed. Returns rows labeled 'same' (both sides say the same thing), 'different_framing' (same event, different emphasis), 'contradiction' (claims that cannot both be true), 'only_us', or 'only_china'. Each row includes a one-sentence reason and verbatim quotes with source links. For the AI topic, also reports whether the Chinese original contains the terms 人工智能 and/or 超级智能. Unverifiable rows are reported to the user, not silently dropped. Only fetches URLs listed in config/sources.toml -- never URLs from user input."
- Returns: `{meeting_id, topic, rows: [ComparisonRow], dropped: int, drop_reasons: [str]}`
- Errors: "Could not load statements for '{meeting_id}': {reason}." / "No verifiable rows found for topic '{topic}'."

**track_commitments(meeting_id: str)**
- Description: "List commitments made at a meeting with honest statuses based on today's date: 'upcoming' (deadline in the future), 'deadline passed, not verified' (deadline has passed but fulfillment is unknown), or 'no date given'. Never claims a promise was kept or broken without evidence."
- Returns: `{meeting_id, as_of: today, commitments: [Commitment]}`
- Errors: "No commitment data found for '{meeting_id}'." / "Meeting '{meeting_id}' not found."

---

## 4. How compare_statements works

1. **Cache check**: build key `(meeting_id, topic.strip().lower(), sha256(us_paragraphs + china_paragraphs))`, where topic is an empty string when not provided. If a cached result exists for this key, return it immediately without a model call.
2. **Fetch**: call `get_official_statement` internally for both sides (not via the model). For the AI topic, also fetch the Chinese original (role=term_check_only) to run the term check in step 5.
3. **Model call (temperature=0)**: call the model once with a structured prompt that includes all paragraphs from both statements and the topic (if given). The prompt instructs the model to: group paragraphs by topic, select one verbatim quote per side per row, assign a label (same / different_framing / contradiction / only_us / only_china), and write one sentence explaining the label. The model must copy quotes character-for-character from the input -- it cannot rephrase.
4. **Verify every quote**: for each quote the model returns, normalize the quote and its source paragraphs (collapse whitespace, convert curly/smart quotes to straight, replace non-breaking spaces). The quote passes only if it is an exact substring of at least one normalized paragraph AND is at least 6 words long. Quotes that fail are logged to `drop_reasons` and the row is removed.
5. **Chinese term check (AI topic only)**: exact-match the normalized Chinese original for 人工智能 and 超级智能 and append a row reporting which terms are present. This row is not subject to quote verification (it is a term-presence check, not a quote).
6. **Report dropped rows**: include `dropped` count and `drop_reasons` in the return value. The frontend displays "N rows hidden because quotes could not be verified."
7. **Return** verified rows, the term-check row if applicable, dropped count, and drop reasons. Store result in cache.

---

## 5. track_commitments status logic

Commitment data is curated manually in `data/commitments/{meeting_id}.json` (quotes are sourced from the statements; no invented text). At runtime:

```
if commitment.deadline is None:
    status = "no date given"
elif date.fromisoformat(commitment.deadline) > today:
    status = "upcoming"
else:
    status = "deadline passed, not verified"
```

`today` is passed in at call time so tests can inject a fixed date. When called for real, `today` is derived from the current time in the America/New_York timezone.

---

## 6. Frontend wireframe

```
+--------------------------------------------------+
|  TWO READOUTS                                    |
|  Official statements, side by side               |
+--------------------------------------------------+
|  [tool call] list_meetings() -> ...         ^    |
|  [tool call] get_official_statement(...)    |    |
|  [tool call] compare_statements(...)       chat  |
|                                             |    |
|  ASSISTANT                                  |    |
|  Both sides addressed AI, but with          v    |
|  different names. See table below.               |
|                                                  |
|  +--------------------------------------------+ |
|  | TOPIC | LABEL         | US       | CHINA   | |
|  | AI    | contradiction | "super   | "China- | |
|  |       | US calls it   |  intelli-|  U.S.   | |
|  |       | "super intell-|  gence"  |  AI     | |
|  |       | igence"; China|  [src]   |  Dialog | |
|  |       | names a Dialog|          |  ue"    | |
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

`tests/test_verify.py`
- Normalization: curly quotes, non-breaking spaces, collapsed whitespace all pass
- Exact substring found: passes
- Quote trimmed by one character: fails
- Quote from wrong paragraph: fails
- Quote under 6 words: fails even if it is an exact substring
- Quote exactly 6 words: passes

`tests/test_tools.py`
- `list_meetings`: returns correct shape from real config file
- `get_official_statement`: returns Statement shape with mocked HTTP 200
- `get_official_statement`: falls back to snapshot with mocked HTTP 404; snapshot marked live=False
- `compare_statements`: drops row with bad quote; dropped count is 1, drop_reason present
- `compare_statements`: Chinese term check finds 人工智能, does not find 超级智能 in the saved snapshot
- `track_commitments`: future deadline -> "upcoming"; past deadline -> "deadline passed, not verified"; no date -> "no date given"
- `track_commitments`: every commitment's exact_quote is a substring of the corresponding snapshot (uses real snapshot files)

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
| Commitment data is stale or wrong | Hand-curated with source citations; status never says "kept" or "broken" |
| Single source of truth for "today" | Injected at call time; tests use a fixed date |
