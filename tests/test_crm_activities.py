"""Tests for CRM activities commands."""

import json

from tests.conftest import WHOAMI_RESPONSE


SAMPLE_ACTIVITY = {
    "id": "a1",
    "organization_id": "org-456",
    "type": "task",
    "title": "Follow up with Acme",
    "status": "pending",
    "priority": "medium",
    "due_date": "2026-03-15T00:00:00Z",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_activities_list(invoke, mock_api):
    mock_api.get("/crm/activities").respond(200, json=[SAMPLE_ACTIVITY])
    result = invoke(["crm", "activities", "list"])
    assert result.exit_code == 0
    assert "Follow up with Acme" in result.output


def test_activities_list_json(invoke, mock_api):
    mock_api.get("/crm/activities").respond(200, json=[SAMPLE_ACTIVITY])
    result = invoke(["crm", "--json", "activities", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["title"] == "Follow up with Acme"


def test_activities_list_with_filters(invoke, mock_api):
    mock_api.get("/crm/activities").respond(200, json=[])
    result = invoke(["crm", "activities", "list", "--type", "task", "--status", "pending"])
    assert result.exit_code == 0


def test_activities_get(invoke, mock_api):
    mock_api.get("/crm/activities/a1").respond(200, json=SAMPLE_ACTIVITY)
    result = invoke(["crm", "activities", "get", "a1"])
    assert result.exit_code == 0
    assert "Follow up with Acme" in result.output


def test_activities_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/crm/activities").respond(201, json=SAMPLE_ACTIVITY)
    result = invoke([
        "crm", "activities", "create",
        "--type", "task",
        "--title", "Follow up with Acme",
    ])
    assert result.exit_code == 0
    assert "Created activity" in result.output


def test_activities_complete(invoke, mock_api):
    completed = {**SAMPLE_ACTIVITY, "status": "completed", "completed_at": "2026-03-12T00:00:00Z"}
    mock_api.patch("/crm/activities/a1").respond(200, json=completed)
    result = invoke(["crm", "activities", "complete", "a1"])
    assert result.exit_code == 0
    assert "Completed activity" in result.output


def test_activities_delete_with_yes(invoke, mock_api):
    mock_api.delete("/crm/activities/a1").respond(204)
    result = invoke(["crm", "activities", "delete", "a1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_activities_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "activities", "delete", "a1"], input="n\n")
    assert result.exit_code == 1
