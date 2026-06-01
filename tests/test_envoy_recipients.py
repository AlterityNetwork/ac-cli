"""Tests for envoy recipients commands."""

import json

import httpx


def _add_response(added=None, already_active=None, requires_confirmation=None):
    """Structured POST /recipients response body (ENG-1188)."""
    return {
        "added": added or [],
        "already_active": already_active or [],
        "requires_confirmation": requires_confirmation or [],
    }


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
        201,
        json=_add_response(
            added=[{"id": "rec-1", "prospect_id": "p1"}, {"id": "rec-2", "prospect_id": "p2"}]
        ),
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2"])
    assert result.exit_code == 0
    assert "Added 2 recipient" in result.output


def test_recipients_add_with_crm_list(invoke, mock_api):
    """Add recipients using --crm-list-id flag."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--crm-list-id", "list-123"])
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output


def test_recipients_add_json(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["added"][0]["id"] == "rec-1"
    assert parsed["requires_confirmation"] == []


def test_recipients_add_raw_source(invoke, mock_api):
    """Raw --source JSON still works for advanced usage."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])
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


def test_recipients_add_partial_already_active(invoke, mock_api):
    """Some already active: added counted, already-active reported as skipped."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201,
        json=_add_response(
            added=[{"id": "rec-1", "prospect_id": "p3", "status": "active"}],
            already_active=["p1", "p2"],
        ),
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2,p3"])
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output
    assert "2 already enrolled" in result.output


def test_recipients_add_422_error(invoke, mock_api):
    """API returns 422 validation error -> exit code 2."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        422, json={"detail": "The request contains invalid data."}
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1"])
    assert result.exit_code == 2


def test_recipients_add_all_already_active(invoke, mock_api):
    """All already active -> info 'already enrolled', never a green 'Added'."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=_add_response(already_active=["p1", "p2"])
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2"])
    assert result.exit_code == 0
    assert "2 already enrolled" in result.output
    assert "Added" not in result.output


def test_recipients_add_json_structured_passthrough(invoke, mock_api):
    """JSON output returns the structured body as-is."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201,
        json=_add_response(
            requires_confirmation=[
                {"prospect_id": "p1", "full_name": "Ada", "previous_status": "removed"}
            ]
        ),
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["requires_confirmation"][0]["previous_status"] == "removed"


def test_recipients_add_previously_enrolled_declined(invoke, mock_api):
    """ENG-1188: previously-enrolled prospect warns; declining makes no re-call."""
    route = mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201,
        json=_add_response(
            requires_confirmation=[
                {"prospect_id": "p1", "full_name": "Ada Lovelace", "previous_status": "removed"}
            ]
        ),
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1"], input="n\n")
    assert result.exit_code == 0
    assert "previously in this sequence" in result.output
    assert "--reenroll" in result.output
    assert route.call_count == 1  # no re-enrol re-call


def test_recipients_add_previously_enrolled_confirmed(invoke, mock_api):
    """Confirming the prompt re-calls with reenroll=true and reports the add."""
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").mock(
        side_effect=[
            httpx.Response(
                201,
                json=_add_response(
                    requires_confirmation=[
                        {
                            "prospect_id": "p1",
                            "full_name": "Ada Lovelace",
                            "previous_status": "removed",
                        }
                    ]
                ),
            ),
            httpx.Response(201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])),
        ]
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1"], input="y\n")
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output


def test_recipients_add_reenroll_flag_sends_reenroll(invoke, mock_api):
    """--reenroll reactivates directly on the first call (no prompt)."""
    route = mock_api.post("/api/v1/envoy/sequences/seq-1/recipients").respond(
        201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])
    )
    result = invoke(["envoy", "recipients", "add", "seq-1", "--prospect-ids", "p1", "--reenroll"])
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output
    assert route.call_count == 1
    body = json.loads(route.calls.last.request.content)
    assert body["reenroll"] is True


def test_recipients_remove_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/envoy/sequences/seq-1/recipients/r1").respond(204)
    result = invoke(["envoy", "recipients", "remove", "seq-1", "r1", "--yes"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_recipients_remove_aborted(invoke, mock_api):
    result = invoke(["envoy", "recipients", "remove", "seq-1", "r1"], input="n\n")
    assert result.exit_code == 1
