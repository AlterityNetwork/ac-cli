"""Tests for the CRM pipeline-stages commands (ENG-931)."""

import json

SAMPLE_STAGE = {
    "id": "s1",
    "organization_id": "org-456",
    "key": "identified",
    "label": "Identified",
    "sort_order": 1,
    "default_probability": 10,
    "stage_type": "open",
    "created_at": "2026-05-27T00:00:00Z",
    "updated_at": "2026-05-27T00:00:00Z",
}


def test_list(invoke, mock_api):
    mock_api.get("/api/v1/crm/pipeline/stages").respond(200, json=[SAMPLE_STAGE])
    result = invoke(["crm", "pipeline", "list"])
    assert result.exit_code == 0
    assert "Identified" in result.output


def test_list_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/pipeline/stages").respond(200, json=[SAMPLE_STAGE])
    result = invoke(["crm", "pipeline", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["key"] == "identified"


def test_create(invoke, mock_api):
    created = {**SAMPLE_STAGE, "key": "discovery", "label": "Discovery"}
    route = mock_api.post("/api/v1/crm/pipeline/stages").respond(201, json=created)
    result = invoke(
        [
            "crm",
            "pipeline",
            "create",
            "--label",
            "Discovery",
            "--default-probability",
            "15",
        ]
    )
    assert result.exit_code == 0, result.output
    assert "Created stage" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"label": "Discovery", "default_probability": 15}


def test_update(invoke, mock_api):
    updated = {**SAMPLE_STAGE, "label": "Renamed"}
    route = mock_api.patch("/api/v1/crm/pipeline/stages/s1").respond(200, json=updated)
    result = invoke(["crm", "pipeline", "update", "s1", "--label", "Renamed"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"label": "Renamed"}


def test_update_no_fields_exits_1(invoke, mock_api):
    result = invoke(["crm", "pipeline", "update", "s1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_delete_requires_confirm(invoke, mock_api):
    mock_api.delete("/api/v1/crm/pipeline/stages/s1").respond(204)
    result = invoke(["crm", "pipeline", "delete", "s1"], input="n\n")
    assert result.exit_code != 0


def test_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/pipeline/stages/s1").respond(204)
    result = invoke(["crm", "pipeline", "delete", "s1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted stage" in result.output


def test_delete_passes_reassign_to(invoke, mock_api):
    route = mock_api.delete("/api/v1/crm/pipeline/stages/s1").respond(204)
    result = invoke(
        [
            "crm",
            "pipeline",
            "delete",
            "s1",
            "--reassign-to",
            "qualified",
            "--yes",
        ]
    )
    assert result.exit_code == 0
    assert b"reassign_to=qualified" in route.calls.last.request.url.query


def test_reorder(invoke, mock_api):
    items = [
        {"id": "s1", "sort_order": 1},
        {"id": "s2", "sort_order": 2},
    ]
    reordered = [SAMPLE_STAGE, {**SAMPLE_STAGE, "id": "s2", "key": "qualified"}]
    route = mock_api.post("/api/v1/crm/pipeline/stages/reorder").respond(200, json=reordered)
    result = invoke(["crm", "pipeline", "reorder", "--items", json.dumps(items)])
    assert result.exit_code == 0, result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"items": items}


def test_reorder_invalid_json_exits_2(invoke, mock_api):
    result = invoke(["crm", "pipeline", "reorder", "--items", "{not-json"])
    assert result.exit_code == 2


def test_member_gets_403_on_create(invoke, mock_api):
    mock_api.post("/api/v1/crm/pipeline/stages").respond(
        403, json={"detail": "Organization owner or admin access required."}
    )
    result = invoke(
        [
            "crm",
            "pipeline",
            "create",
            "--label",
            "Discovery",
            "--default-probability",
            "15",
        ]
    )
    assert result.exit_code != 0
