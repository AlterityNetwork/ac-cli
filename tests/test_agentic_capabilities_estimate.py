"""`ac agentic capabilities estimate` prices one run before it starts."""

import json

import pytest

PATH = "/api/v1/agentic/capabilities/signals.search/estimate"
SEARCH_ID = "11111111-1111-1111-1111-111111111111"

ESTIMATE = {
    "priced": True,
    "unit": "company",
    "units": 12,
    "credits_per_unit": 90,
    "credits_per_run": 1080,
    "credits_enforced": True,
    "remaining_credits": 5000,
    "units_covered": 55,
    "schedule": None,
}


def _estimate(*args: str) -> list[str]:
    return ["agentic", "capabilities", "estimate", "signals.search", *args]


def test_units_send_the_count_and_print_the_json(invoke, mock_api):
    route = mock_api.post(PATH).respond(200, json=ESTIMATE)

    result = invoke([*_estimate("--units", "12"), "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == ESTIMATE
    assert json.loads(route.calls[0].request.content) == {"units": 12}


def test_a_saved_search_and_a_schedule_are_sent(invoke, mock_api):
    route = mock_api.post(PATH).respond(
        200,
        json={**ESTIMATE, "schedule": {"runs_per_month": 30, "credits_per_month": 32400}},
    )

    result = invoke(
        _estimate(
            "--saved-search-id",
            SEARCH_ID,
            "--cron",
            "0 9 * * *",
            "--timezone",
            "Europe/London",
        )
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "saved_search_id": SEARCH_ID,
        "schedule": {"cron": "0 9 * * *", "timezone": "Europe/London"},
    }
    assert "1080" in result.output
    assert "32400" in result.output


def test_an_input_is_sent_as_an_object(invoke, mock_api):
    route = mock_api.post(PATH).respond(200, json={**ESTIMATE, "units": 0})

    result = invoke(_estimate("--input", '{"source":"discovery"}'))

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"input": {"source": "discovery"}}


def test_the_human_output_names_the_price_and_the_cover(invoke, mock_api):
    mock_api.post(PATH).respond(200, json=ESTIMATE)

    result = invoke(_estimate("--units", "12"))

    assert result.exit_code == 0, result.output
    for text in ("1080", "90", "5000", "55"):
        assert text in result.output


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--units", "3", "--input", "{}"],
        ["--units", "3", "--saved-search-id", SEARCH_ID],
        ["--units", "-1"],
        ["--input", "[]"],
        ["--units", "3", "--timezone", "UTC"],
    ],
    ids=["nothing", "units-and-input", "units-and-search", "negative", "not-object", "zone-only"],
)
def test_an_unusable_request_is_refused_without_http(invoke, mock_api, args):
    result = invoke([*_estimate(*args), "--json"])

    assert result.exit_code == 2, result.output
    assert json.loads(result.output)["error"] is True
    assert not mock_api.calls


@pytest.mark.parametrize("status,exit_code", [(404, 3), (422, 2)])
def test_api_errors_keep_the_semantic_exit(invoke, mock_api, status, exit_code):
    mock_api.post(PATH).respond(status, json={"detail": "nope"})

    result = invoke([*_estimate("--units", "1"), "--json"])

    assert result.exit_code == exit_code, result.output
