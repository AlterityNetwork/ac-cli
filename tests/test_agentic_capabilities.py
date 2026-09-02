"""Capability starts keep the API contract and delivery key intact."""

import json

import pytest

from tests.test_agentic_runs import SAMPLE_RUN

ARGS = [
    "agentic",
    "capabilities",
    "start",
    "company.search",
    "--contract-version",
    "1",
    "--input",
    '{"query":"acme"}',
    "--idempotency-key",
    "delivery-42",
]
PATH = "/api/v1/agentic/capabilities/company.search/runs"


@pytest.mark.parametrize(
    "outcome,status",
    [
        ("started", "queued"),
        ("duplicate", "succeeded"),
        ("started", "waiting"),
        ("started", "failed"),
    ],
)
def test_start_preserves_request_and_run_response(invoke, mock_api, outcome, status):
    run = {
        **SAMPLE_RUN,
        "outcome": outcome,
        "status": status,
        "capability_id": "company.search",
        "contract_version": 1,
    }
    route = mock_api.post(PATH).respond(200, json=run)
    result = invoke([*ARGS, "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == run
    request = route.calls[0].request
    assert json.loads(request.content) == {"contract_version": 1, "input": {"query": "acme"}}
    assert request.headers["Idempotency-Key"] == "delivery-42"


def test_human_response_shows_capability_and_status(invoke, mock_api):
    mock_api.post(PATH).respond(
        200,
        json={
            **SAMPLE_RUN,
            "status": "waiting",
            "capability_id": "company.search",
            "contract_version": 1,
        },
    )
    result = invoke(ARGS)
    assert result.exit_code == 0, result.output
    assert "company.search" in result.output
    assert "waiting" in result.output


@pytest.mark.parametrize("flag", ["--contract-version", "--input", "--idempotency-key"])
def test_required_flags_cannot_default(invoke, mock_api, flag):
    args = ARGS.copy()
    index = args.index(flag)
    del args[index : index + 2]
    result = invoke(args)
    assert result.exit_code == 2
    assert not mock_api.calls


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--input", '{"query":"\\ud800"}'),
        ("--input", "[]"),
        ("--input", "null"),
        ("--input", "{"),
        ("--input", ""),
        ("--input", '{"limit":NaN}'),
        ("--input", '{"limit":Infinity}'),
        ("--idempotency-key", " "),
        ("--idempotency-key", "x" * 201),
        ("--idempotency-key", "line\nbreak"),
        ("--idempotency-key", "é"),
    ],
)
def test_bad_local_input_is_a_json_error_without_http(invoke, mock_api, flag, value):
    args = ARGS.copy()
    args[args.index(flag) + 1] = value
    result = invoke([*args, "--json"])
    assert result.exit_code == 2, result.output
    assert json.loads(result.output)["error"] is True
    assert not mock_api.calls


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "true"])
def test_version_is_a_positive_integer(invoke, mock_api, value):
    args = ARGS.copy()
    args[args.index("--contract-version") + 1] = value
    assert invoke(args).exit_code == 2
    assert not mock_api.calls


@pytest.mark.parametrize(
    "status,code,exit_code",
    [
        (400, "invalid_key", 1),
        (403, "capability_unauthorized", 4),
        (404, "capability_not_found", 3),
        (409, "capability_unavailable", 5),
        (409, "idempotency_conflict", 5),
        (409, "contract_version_conflict", 5),
        (413, "input_too_large", 1),
        (422, "invalid_input", 2),
        (429, "budget_denied", 1),
        (503, "principal_unavailable", 1),
    ],
)
def test_api_errors_keep_code_and_semantic_exit(invoke, mock_api, status, code, exit_code):
    detail = {"code": code}
    mock_api.post(PATH).respond(status, json={"detail": detail})
    result = invoke([*ARGS, "--json"])
    assert result.exit_code == exit_code, result.output
    assert json.loads(result.output) == {"error": True, "status_code": status, "detail": detail}
