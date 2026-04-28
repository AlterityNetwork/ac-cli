"""Tests for envoy campaigns commands."""

import json

from tests.conftest import WHOAMI_RESPONSE


SAMPLE_CAMPAIGN = {
    "id": "camp-1",
    "organization_id": "org-456",
    "name": "Q2 Outreach",
    "description": "Spring push",
    "goal": "10 demos",
    "source_app": "envoy",
    "started_at": "2026-04-01T00:00:00Z",
    "ended_at": None,
    "archived_at": None,
    "sequence_count": 3,
    "created_by": "user-123",
    "created_at": "2026-04-01T00:00:00Z",
    "updated_at": "2026-04-01T00:00:00Z",
}


def test_campaigns_list(invoke, mock_api):
    mock_api.get("/api/v1/envoy/campaigns").respond(
        200, json={"data": [SAMPLE_CAMPAIGN], "next_cursor": None}
    )
    result = invoke(["envoy", "campaigns", "list"])
    assert result.exit_code == 0
    assert "Q2 Outreach" in result.output


def test_campaigns_list_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/campaigns").respond(
        200, json={"data": [SAMPLE_CAMPAIGN], "next_cursor": None}
    )
    result = invoke(["envoy", "campaigns", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["name"] == "Q2 Outreach"


def test_campaigns_list_archived_filter(invoke, mock_api):
    route = mock_api.get("/api/v1/envoy/campaigns").respond(
        200, json={"data": [], "next_cursor": None}
    )
    result = invoke(["envoy", "campaigns", "list", "--archived"])
    assert result.exit_code == 0
    assert "archived=true" in str(route.calls.last.request.url)


def test_campaigns_get(invoke, mock_api):
    mock_api.get("/api/v1/envoy/campaigns/camp-1").respond(200, json=SAMPLE_CAMPAIGN)
    result = invoke(["envoy", "campaigns", "get", "camp-1"])
    assert result.exit_code == 0
    assert "Q2 Outreach" in result.output


def test_campaigns_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/envoy/campaigns/bogus").respond(
        404, json={"detail": "Not found"}
    )
    result = invoke(["envoy", "campaigns", "get", "bogus"])
    assert result.exit_code == 3


def test_campaigns_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/envoy/campaigns").respond(201, json=SAMPLE_CAMPAIGN)
    result = invoke(["envoy", "campaigns", "create", "--name", "Q2 Outreach"])
    assert result.exit_code == 0
    assert "Created campaign" in result.output


def test_campaigns_create_json(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/envoy/campaigns").respond(201, json=SAMPLE_CAMPAIGN)
    result = invoke(
        ["envoy", "campaigns", "create", "--name", "Q2 Outreach", "--json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "camp-1"


def test_campaigns_update(invoke, mock_api):
    updated = {**SAMPLE_CAMPAIGN, "name": "Q2 Renamed"}
    mock_api.patch("/api/v1/envoy/campaigns/camp-1").respond(200, json=updated)
    result = invoke(
        ["envoy", "campaigns", "update", "camp-1", "--name", "Q2 Renamed"]
    )
    assert result.exit_code == 0
    assert "Updated campaign" in result.output


def test_campaigns_update_no_fields(invoke, mock_api):
    result = invoke(["envoy", "campaigns", "update", "camp-1"])
    assert result.exit_code == 1


def test_campaigns_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/envoy/campaigns/camp-1").respond(204)
    result = invoke(["envoy", "campaigns", "delete", "camp-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_campaigns_delete_aborted(invoke, mock_api):
    result = invoke(["envoy", "campaigns", "delete", "camp-1"], input="n\n")
    assert result.exit_code == 1


def test_campaigns_archive(invoke, mock_api):
    archived = {**SAMPLE_CAMPAIGN, "archived_at": "2026-04-15T00:00:00Z"}
    mock_api.post("/api/v1/envoy/campaigns/camp-1/archive").respond(200, json=archived)
    result = invoke(["envoy", "campaigns", "archive", "camp-1"])
    assert result.exit_code == 0
    assert "Archived campaign" in result.output


def test_campaigns_unarchive(invoke, mock_api):
    mock_api.post("/api/v1/envoy/campaigns/camp-1/unarchive").respond(
        200, json=SAMPLE_CAMPAIGN
    )
    result = invoke(["envoy", "campaigns", "unarchive", "camp-1"])
    assert result.exit_code == 0
    assert "Unarchived campaign" in result.output
