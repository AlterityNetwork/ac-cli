"""Tests for the launchpad dismissed-companies commands."""

import json

_PATH = "/api/v1/launchpad/dismissed-companies"
_RESTORE_PATH = "/api/v1/launchpad/dismissed-companies/restore"

COMPANY_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
COMPANY_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def test_clear(invoke, mock_api):
    route = mock_api.post(_PATH).respond(200, json={"dismissed_count": 2})
    result = invoke(
        ["launchpad", "dismissed-companies", "clear", "--ids", f"{COMPANY_A},{COMPANY_B}", "--yes"]
    )
    assert result.exit_code == 0
    assert "2" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body["ids"] == [COMPANY_A, COMPANY_B]


def test_clear_json(invoke, mock_api):
    mock_api.post(_PATH).respond(200, json={"dismissed_count": 1})
    result = invoke(
        ["launchpad", "dismissed-companies", "clear", "--ids", COMPANY_A, "--yes", "--json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["dismissed_count"] == 1


def test_clear_aborts_without_confirmation(invoke, mock_api):
    result = invoke(["launchpad", "dismissed-companies", "clear", "--ids", COMPANY_A], input="n\n")
    assert result.exit_code == 1
    assert not mock_api.calls


def test_clear_confirmed_interactively(invoke, mock_api):
    mock_api.post(_PATH).respond(200, json={"dismissed_count": 1})
    result = invoke(["launchpad", "dismissed-companies", "clear", "--ids", COMPANY_A], input="y\n")
    assert result.exit_code == 0


def test_restore(invoke, mock_api):
    route = mock_api.post(_RESTORE_PATH).respond(200, json={"restored_count": 1})
    result = invoke(["launchpad", "dismissed-companies", "restore", "--ids", COMPANY_A])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["ids"] == [COMPANY_A]


def test_restore_json(invoke, mock_api):
    mock_api.post(_RESTORE_PATH).respond(200, json={"restored_count": 2})
    result = invoke(
        [
            "launchpad",
            "dismissed-companies",
            "restore",
            "--ids",
            f"{COMPANY_A},{COMPANY_B}",
            "--json",
        ]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["restored_count"] == 2


def test_clear_validation_error_exits_2(invoke, mock_api):
    mock_api.post(_PATH).respond(422, json={"detail": "not a uuid"})
    result = invoke(["launchpad", "dismissed-companies", "clear", "--ids", "bogus", "--yes"])
    assert result.exit_code == 2


def test_restore_not_found_exits_3(invoke, mock_api):
    mock_api.post(_RESTORE_PATH).respond(404, json={"detail": "nope"})
    result = invoke(["launchpad", "dismissed-companies", "restore", "--ids", COMPANY_A])
    assert result.exit_code == 3


def test_clear_dedupes_and_trims_ids(invoke, mock_api):
    route = mock_api.post(_PATH).respond(200, json={"dismissed_count": 2})
    result = invoke(
        [
            "launchpad",
            "dismissed-companies",
            "clear",
            "--ids",
            f" {COMPANY_A} , {COMPANY_B},{COMPANY_A} ,",
            "--yes",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["ids"] == [COMPANY_A, COMPANY_B]


def test_clear_rejects_empty_ids_before_request(invoke, mock_api):
    result = invoke(["launchpad", "dismissed-companies", "clear", "--ids", " , ", "--yes"])
    assert result.exit_code == 1
    assert "No IDs" in result.output
    assert not mock_api.calls


def test_clear_rejects_oversized_batch_before_request(invoke, mock_api):
    too_many = ",".join(f"aaaaaaaa-aaaa-aaaa-aaaa-{i:012d}" for i in range(201))
    result = invoke(["launchpad", "dismissed-companies", "clear", "--ids", too_many, "--yes"])
    assert result.exit_code == 1
    assert "Too many IDs" in result.output
    # Fails locally rather than sending a batch the API will reject with a 422.
    assert not mock_api.calls


def test_clear_rejects_empty_ids_json(invoke, mock_api):
    # Client-side validation runs before any request, so it never reaches the
    # shared error handler; it still has to honour --json.
    result = invoke(
        ["launchpad", "dismissed-companies", "clear", "--ids", " , ", "--yes", "--json"]
    )
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert "No IDs" in parsed["detail"]
    assert not mock_api.calls


def test_clear_rejects_oversized_batch_json(invoke, mock_api):
    too_many = ",".join(f"aaaaaaaa-aaaa-aaaa-aaaa-{i:012d}" for i in range(201))
    result = invoke(
        ["launchpad", "dismissed-companies", "clear", "--ids", too_many, "--yes", "--json"]
    )
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert "Too many IDs" in parsed["detail"]
    assert not mock_api.calls


def test_restore_rejects_empty_ids_json(invoke, mock_api):
    result = invoke(["launchpad", "dismissed-companies", "restore", "--ids", " , ", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"] is True
    assert not mock_api.calls
