"""Tests for the CRM saved-filters commands."""

import json

SAMPLE_FILTER = {
    "id": "f1",
    "organization_id": "org-456",
    "profile_id": "u-1",
    "member_type": "company",
    "visibility": "private",
    "name": "FinTech London",
    "description": None,
    "criteria": {"industry": "FinTech"},
    "created_at": "2026-05-18T00:00:00Z",
    "updated_at": "2026-05-18T00:00:00Z",
}


def test_list(invoke, mock_api):
    mock_api.get("/api/v1/crm/saved-filters").respond(
        200, json={"data": [SAMPLE_FILTER], "total": 1}
    )
    result = invoke(["crm", "saved-filters", "list"])
    assert result.exit_code == 0
    assert "FinTech London" in result.output


def test_list_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/saved-filters").respond(
        200, json={"data": [SAMPLE_FILTER], "total": 1}
    )
    result = invoke(["crm", "saved-filters", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["name"] == "FinTech London"


def test_list_member_type_filter(invoke, mock_api):
    route = mock_api.get("/api/v1/crm/saved-filters").respond(200, json={"data": [], "total": 0})
    result = invoke(["crm", "saved-filters", "list", "--member-type", "signal"])
    assert result.exit_code == 0
    # respx records the request — confirm member_type=signal made it onto the query.
    assert b"member_type=signal" in route.calls.last.request.url.query


def test_get(invoke, mock_api):
    mock_api.get("/api/v1/crm/saved-filters/f1").respond(200, json=SAMPLE_FILTER)
    result = invoke(["crm", "saved-filters", "get", "f1"])
    assert result.exit_code == 0
    assert "FinTech London" in result.output


def test_create(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/saved-filters").respond(201, json=SAMPLE_FILTER)
    result = invoke(
        [
            "crm",
            "saved-filters",
            "create",
            "--name",
            "FinTech London",
            "--member-type",
            "company",
            "--criteria",
            '{"industry": "FinTech"}',
            "--visibility",
            "private",
        ]
    )
    assert result.exit_code == 0
    assert "Created saved filter" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "FinTech London"
    assert body["member_type"] == "company"
    assert body["criteria"] == {"industry": "FinTech"}
    assert body["visibility"] == "private"
    # Backend derives org_id + profile_id from auth — never sent from CLI.
    assert "organization_id" not in body
    assert "profile_id" not in body


def test_create_invalid_criteria_json_exits_2(invoke, mock_api):
    result = invoke(
        [
            "crm",
            "saved-filters",
            "create",
            "--name",
            "X",
            "--member-type",
            "company",
            "--criteria",
            "{not-json",
        ]
    )
    assert result.exit_code == 2


def test_update(invoke, mock_api):
    updated = {**SAMPLE_FILTER, "name": "Renamed"}
    mock_api.patch("/api/v1/crm/saved-filters/f1").respond(200, json=updated)
    result = invoke(["crm", "saved-filters", "update", "f1", "--name", "Renamed"])
    assert result.exit_code == 0
    assert "Updated saved filter" in result.output


def test_update_no_fields_exits_1(invoke, mock_api):
    result = invoke(["crm", "saved-filters", "update", "f1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_delete_requires_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/saved-filters/f1").respond(204)
    # No `--yes`, no piped input → typer aborts the confirm.
    result = invoke(["crm", "saved-filters", "delete", "f1"], input="n\n")
    assert result.exit_code != 0


def test_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/saved-filters/f1").respond(204)
    result = invoke(["crm", "saved-filters", "delete", "f1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted saved filter" in result.output


def test_delete_with_yes_json(invoke, mock_api):
    mock_api.delete("/api/v1/crm/saved-filters/f1").respond(204)
    result = invoke(["crm", "saved-filters", "delete", "f1", "--yes", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {"deleted": True, "id": "f1"}


def test_get_not_found_exits_3(invoke, mock_api):
    mock_api.get("/api/v1/crm/saved-filters/missing").respond(
        404, json={"detail": "Saved filter not found"}
    )
    result = invoke(["crm", "saved-filters", "get", "missing"])
    assert result.exit_code == 3
