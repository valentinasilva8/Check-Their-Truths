"""Tool functions, JSON schemas, and the dispatcher the harness uses."""

import json

from sources import get_official_source as _fetch_official_source, load_config


def list_cases() -> str:
    """List all supported cases with their IDs, types, names, and dates."""
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
    """Retrieve the official statement for one side of a meeting case.

    Returns paragraphs, source URL, retrieved_at, and whether the text is
    live or from a saved snapshot.
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


TOOLS = [
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
]

TOOL_MAP = {
    "list_cases": list_cases,
    "get_official_source": get_official_source,
}


def run_tool(name: str, args: dict) -> str:
    """Run one tool call. Models invent tool names and arguments; never let that crash the loop."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool '{name}'. Available: {list(TOOL_MAP)}"})
    try:
        return TOOL_MAP[name](**args)
    except TypeError as e:
        return json.dumps({"error": f"Bad arguments for {name}: {e}"})
