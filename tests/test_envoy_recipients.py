"""Tests for envoy recipients commands."""

import json

SAMPLE_RECIPIENT = {
    "id": "r1",
    "sequence_id": "seq-1",
    "recipient_name": "Jane Doe",
    "recipient_email": "jane@example.com",
    "status": "active",
    "current_step": 1,
}


def test_recipients_list(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1/recipients").respond(200, json=[SAMPLE_RECIPIENT])
    result = invoke(["envoy", "recipients", "list", "seq-1"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output


def test_recipients_list_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1/recipients").respond(200, json=[SAMPLE_RECIPIENT])
    result = invoke(["envoy", "recipients", "list", "seq-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["recipient_email"] == "jane@example.com"


def test_recipients_list_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1/recipients").respond(200, json=[])
    result = invoke(
        ["envoy", "recipients", "list", "seq-1", "--status", "active", "--step-id", "step-1"]
    )
    assert result.exit_code == 0


def test_recipients_add_with_prospect_ids(invoke, mock_api):
    """Add recipients using --prospect-ids flag."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=[{"id": "rec-1", "prospect_id": "p1"}, {"id": "rec-2", "prospect_id": "p2"}]
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2"])
    assert result.exit_code == 0
    assert "Added 2 recipient" in result.output


def test_recipients_add_with_crm_list(invoke, mock_api):
    """Add recipients using --crm-list-id flag."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=[{"id": "rec-1", "prospect_id": "p1"}]
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--crm-list-id", "list-123"])
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output


def test_recipients_add_json(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=[{"id": "rec-1", "prospect_id": "p1"}]
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["id"] == "rec-1"


def test_recipients_add_raw_source(invoke, mock_api):
    """Raw --source JSON still works for advanced usage."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=[{"id": "rec-1", "prospect_id": "p1"}]
    )
    source = json.dumps({"type": "explicit", "prospect_ids": ["p1"]})
    result = invoke(["envoy", "recipients", "add", "seq-1", "--source", source])
    assert result.exit_code == 0


def test_recipients_add_invalid_json(invoke, mock_api):
    result = invoke(["envoy", "recipients", "add", "seq-1", "--source", "not json"])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_recipients_add_no_source(invoke, mock_api):
    """Error when no source is provided."""
    result = invoke(["envoy", "recipients", "add", "seq-1"])
    assert result.exit_code == 1


def test_recipients_remove_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/envoy/sequences/seq-1/recipients/r1").respond(204)
    result = invoke(["envoy", "recipients", "remove", "seq-1", "r1", "--yes"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_recipients_add_with_duplicates_succeeds(invoke, mock_api):
    """API returns 201 with partial results when some recipients already exist."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=[{"id": "rec-1", "prospect_id": "p3", "status": "active"}]
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2,p3"])
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output


def test_recipients_add_422_error(invoke, mock_api):
    """API returns 422 validation error -> exit code 2."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        422, json={"detail": "The request contains invalid data."}
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1"])
    assert result.exit_code == 2


def test_recipients_add_all_duplicates(invoke, mock_api):
    """API returns empty list when all recipients already exist in the sequence."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(201, json=[])
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2"])
    assert result.exit_code == 0
    assert "No new recipients" in result.output
    assert "already in sequence" in result.output


def test_recipients_add_all_duplicates_json(invoke, mock_api):
    """JSON output for all-duplicate case returns the empty list as-is."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(201, json=[])
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == []


def test_recipients_remove_aborted(invoke, mock_api):
    result = invoke(["envoy", "recipients", "remove", "seq-1", "r1"], input="n\n")
    assert result.exit_code == 1
