"""Error strings the model sees. Each one says what to do next."""

import json

from claim_check import check_claim, load_claims
from compare import compare_statements
from press import get_press_coverage
from sources import fetch_source_by_name, get_official_source, load_config
from tools import run_tool


def test_unknown_case_tells_the_model_to_list_cases():
    config = load_config()
    claims = load_claims()
    results = [
        get_official_source(config, "no_such_case", "us"),
        get_press_coverage(config, "no_such_case"),
        compare_statements(config, "no_such_case", "", "us", "china"),
        check_claim(config, claims, "no_such_case", "C1"),
    ]
    for result in results:
        assert "list_cases" in result["error"]


def test_wrong_case_type_names_the_other_tool():
    config = load_config()
    claims = load_claims()
    meeting = "washington_2026_09"
    claim_case = "medicare_checks_2026_10"

    official = get_official_source(config, claim_case, "us")
    press = get_press_coverage(config, claim_case)
    compared = compare_statements(config, claim_case, "military", "us", "china")
    claim = check_claim(config, claims, meeting, "C1")

    assert "check_claim" in official["error"]
    assert "check_claim" in press["error"]
    assert "check_claim" in compared["error"]
    assert "compare_statements" in claim["error"]


def test_bad_side_says_which_values_to_pass():
    config = load_config()
    official = get_official_source(config, "washington_2026_09", "press")
    compared = compare_statements(config, "washington_2026_09", "military", "us", "europe")
    assert "us" in official["error"] and "china" in official["error"]
    assert "press" in compared["error"]
    assert "Call compare_statements again" in compared["error"]


def test_unknown_claim_names_the_ids():
    config = load_config()
    claims = load_claims()
    result = check_claim(config, claims, "medicare_checks_2026_10", "C9")
    assert "C1" in result["error"] and "C2" in result["error"] and "C3" in result["error"]


def test_missing_named_source_says_not_to_invent_numbers():
    config = load_config()
    result = fetch_source_by_name(config, "medicare_checks_2026_10", "no_such_source")
    assert "Do not invent numbers" in result["error"]
    assert "cannot be checked" in result["error"]


def test_unknown_tool_and_bad_arguments_say_what_to_call():
    unknown = json.loads(run_tool("weather", {}))
    assert "Do not invent tool names" in unknown["error"]
    assert "compare_statements" in unknown["error"]
    assert "check_claim" in unknown["error"]

    missing = json.loads(run_tool("check_claim", {"case_id": "medicare_checks_2026_10"}))
    assert "Check the required arguments" in missing["error"]
    assert "claim_id" in missing["error"]
