"""Tools the chat agent can call.

Two Readouts compares the official US and China statements about the
September 2026 Trump-Xi meeting, compares those statements with Guardian
coverage, and fact-checks three Medicare claims from a Trump post.

Five tools:

- list_cases reads the local config. It does not use the network.
- get_official_source uses external data. It fetches a live official page,
  or a saved snapshot when the live page fails.
- get_press_coverage uses external data. It fetches the two curated
  Guardian articles.
- compare_statements is original. It asks the model to compare two sides,
  then keeps a quote only when that quote is in the source text.
- check_claim is original. It applies fixed arithmetic rules to official
  numbers. The model does not do the math.

app.py sends TOOLS to the model so the model knows each tool's name and
arguments. When the model asks for a tool, app.py calls run_tool. run_tool
looks the name up in TOOL_MAP and runs that function. An unknown name or
bad arguments comes back as an error string. It does not crash the loop.
"""

import json

from claim_check import check_claim as _check_claim, load_claims
from compare import compare_statements as _compare_statements
from press import get_press_coverage as _get_press_coverage
from sources import get_official_source as _fetch_official_source, load_config


def list_cases() -> str:
    """List the cases the agent can work on.

    Arguments: none.

    Returns a JSON string with each case id, type (meeting or claim_check),
    name, and dates.

    Data comes from config/sources.toml. No network call.

    Errors: a missing or unreadable config file raises. A valid config with
    no cases returns an empty list.
    """
    config = load_config()
    cases = [
        {
            "case_id": case_id,
            "type": case["type"],
            "name": case["name"],
            "dates": case["dates"],
        }
        for case_id, case in config["cases"].items()
    ]
    return json.dumps({"cases": cases}, ensure_ascii=False)


def get_official_source(case_id: str, source: str) -> str:
    """Fetch one side of an official meeting statement.

    Arguments: case_id (a meeting case from list_cases) and source
    ("us" or "china").

    Returns a JSON string with the paragraphs, the page URL, when it was
    retrieved, and whether the text is live or from a saved snapshot.

    Data comes from the live page listed in config/sources.toml. If that
    page fails, the saved snapshot in data/snapshots/ is used instead.

    Errors: an unknown case id, or a claim-check case, returns a clear
    error. It does not crash. A side that cannot be loaded returns the
    error from the fetcher.
    """
    config = load_config()
    case = config["cases"].get(case_id)
    if not case:
        return json.dumps({"error": f"Case '{case_id}' not found. Call list_cases to see supported cases."})
    if case.get("type") != "meeting":
        return json.dumps({
            "error": (
                f"get_official_source requires a meeting case; "
                f"'{case_id}' is type '{case.get('type')}'. "
                "Use check_claim for claim_check cases."
            )
        })
    result = _fetch_official_source(config, case_id, source)
    return json.dumps(result, ensure_ascii=False)


def get_press_coverage(case_id: str) -> str:
    """Fetch the curated Guardian articles for a meeting case.

    Arguments: case_id (a meeting case from list_cases).

    Returns a JSON string with each article's headline, byline, link,
    published time, and numbered paragraphs.

    Data comes from the Guardian Content API, using the article ids in
    config/sources.toml and the key in the local secrets file. Article
    text stays in memory. It is not written to disk.

    Errors: a missing key, a failed fetch, a claim-check case, or an
    unknown case returns "press side unavailable" or a clear error. It
    does not crash, and the error does not include the API key.
    """
    config = load_config()
    result = _get_press_coverage(config, case_id)
    return json.dumps(result, ensure_ascii=False)


def compare_statements(
    case_id: str,
    topic: str = "",
    left: str = "us",
    right: str = "china",
) -> str:
    """Compare two sides of a meeting and keep only quotes that match the source.

    Arguments: case_id (a meeting case), topic (empty string means every
    topic), and left and right, each "us", "china", or "press".

    Returns a JSON string of rows. Each row has a label, a one-sentence
    reason, and the quotes that passed verification. Rows whose quotes
    could not be verified are counted in "dropped" and are not shown.
    At most 12 comparison rows are returned. An empty topic is capped
    the same way.

    Data comes from get_official_source for "us" and "china", and from
    get_press_coverage for "press". The model proposes the rows. This
    function checks each quote against the source text before returning it.

    Errors: an unknown case, a claim-check case, or a bad side name returns
    a clear error. It does not crash. If the press side cannot be loaded,
    the result is "press side unavailable".
    """
    config = load_config()
    result = _compare_statements(config, case_id, topic, left, right)
    return json.dumps(result, ensure_ascii=False)


def check_claim(case_id: str, claim_id: str) -> str:
    """Fact-check one Medicare claim with fixed rules and code math.

    Arguments: case_id (a claim-check case from list_cases) and claim_id
    ("C1", "C2", or "C3").

    Returns a JSON string with the verdict (supported, imprecise,
    contradicted, or not_checkable), the numbers, the arithmetic, the
    evidence quote, a "Checked against" line, and a context note when
    one applies.

    Data comes from config/claims.toml for the claim and the post text,
    and from the official White House or CMS page named in that claim.
    If the live page fails, the saved snapshot is used. The model does
    not calculate the result.

    Errors: a meeting case, an unknown claim, or a claim whose phrase is
    not in the post returns a clear error or not_checkable. It does not
    crash.
    """
    config = load_config()
    claims = load_claims()
    result = _check_claim(config, claims, case_id, claim_id)
    return json.dumps(result, ensure_ascii=False)


# Schemas sent to the model. app.py passes this list as the tools argument.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_claim",
            "description": (
                "Fact-check a specific numerical claim from a named post against "
                "official source data. Verifies the claimed_phrase is a substring "
                "of the post text. Applies the claim_type rule (at_least, "
                "approximately, direction) using Python Decimal arithmetic. Returns "
                "verdict (supported, imprecise, contradicted, not_checkable), "
                "numbers dict, arithmetic string, evidence quote, and optional "
                "context_note. Use list_cases to see available claim_check cases "
                "and their claim IDs. Claim_check cases only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": (
                            "Claim_check case ID from list_cases, "
                            "e.g. 'medicare_checks_2026_10'."
                        ),
                    },
                    "claim_id": {
                        "type": "string",
                        "description": (
                            "Claim ID within the case, e.g. 'C1', 'C2', 'C3'."
                        ),
                    },
                },
                "required": ["case_id", "claim_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_cases",
            "description": (
                "List all supported cases. Returns case IDs, types "
                "(meeting or claim_check), names, and dates. Call this first "
                "if you are unsure which case IDs are available."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_statements",
            "description": (
                "Compare two sides of a meeting case topic by topic. "
                "left and right can be 'us', 'china', or 'press'. "
                "Returns rows labeled same, different_framing, contradiction, "
                "only_{left}, or only_{right}. Each row has a reason and verified "
                "verbatim quotes. For the AI topic on washington_2026_09, also "
                "reports whether the Chinese original contains 人工智能 and/or "
                "超级智能. topic='' compares all topics (capped at 12 rows). "
                "Meeting cases only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Meeting case ID from list_cases.",
                    },
                    "topic": {
                        "type": "string",
                        "description": (
                            "Topic to compare, e.g. 'AI', 'trade', 'military'. "
                            "Empty string compares all topics."
                        ),
                    },
                    "left": {
                        "type": "string",
                        "enum": ["us", "china", "press"],
                        "description": "Left side: 'us', 'china', or 'press'.",
                    },
                    "right": {
                        "type": "string",
                        "enum": ["us", "china", "press"],
                        "description": "Right side: 'us', 'china', or 'press'.",
                    },
                },
                "required": ["case_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_official_source",
            "description": (
                "Retrieve the official statement for one side of a meeting case. "
                "Returns paragraphs, source URL, retrieved_at, and a live flag. "
                "Only works for meeting cases (not claim_check)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Meeting case ID from list_cases, e.g. 'washington_2026_09'.",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["us", "china"],
                        "description": "Which side to retrieve: 'us' or 'china'.",
                    },
                },
                "required": ["case_id", "source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_press_coverage",
            "description": (
                "Fetch Guardian press coverage for a meeting case. Returns headline, "
                "byline, url, published date, and numbered paragraphs for each curated "
                "article. Paragraph ids look like A1-P1. Does not search. Returns an "
                "error if the press side is unavailable. Meeting cases only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Meeting case ID from list_cases, e.g. 'washington_2026_09'.",
                    },
                },
                "required": ["case_id"],
            },
        },
    },
]

# Name to function. run_tool uses this. The model never calls these directly.
TOOL_MAP = {
    "list_cases": list_cases,
    "get_official_source": get_official_source,
    "get_press_coverage": get_press_coverage,
    "compare_statements": compare_statements,
    "check_claim": check_claim,
}


def run_tool(name: str, args: dict) -> str:
    """Run one tool call. Models invent tool names and arguments; never let that crash the loop."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool '{name}'. Available: {list(TOOL_MAP)}"})
    try:
        return TOOL_MAP[name](**args)
    except TypeError as e:
        return json.dumps({"error": f"Bad arguments for {name}: {e}"})
