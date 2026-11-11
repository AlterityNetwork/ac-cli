"""Tests for sequences recipients commands."""

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
    mock_api.get("/api/v1/sequences/sequences/seq-1/recipients").respond(
        200, json=[SAMPLE_RECIPIENT]
    )
    result = invoke(["sequences", "recipients", "list", "seq-1"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output


def test_recipients_list_json(invoke, mock_api):
    mock_api.get("/api/v1/sequences/sequences/seq-1/recipients").respond(
        200, json=[SAMPLE_RECIPIENT]
    )
    result = invoke(["sequences", "recipients", "list", "seq-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["recipient_email"] == "jane@example.com"


def test_recipients_list_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/sequences/sequences/seq-1/recipients").respond(200, json=[])
    result = invoke(
        ["sequences", "recipients", "list", "seq-1", "--status", "active", "--step-id", "step-1"]
    )
    assert result.exit_code == 0


def test_recipients_add_with_prospect_ids(invoke, mock_api):
    """Add recipients using --prospect-ids flag."""
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201,
        json=_add_response(
            added=[{"id": "rec-1", "prospect_id": "p1"}, {"id": "rec-2", "prospect_id": "p2"}]
        ),
    )
    result = invoke(["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2"])
    assert result.exit_code == 0
    assert "Added 2 recipient" in result.output


def test_recipients_add_with_crm_list(invoke, mock_api):
    """Add recipients using --crm-list-id flag."""
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])
    )
    result = invoke(["sequences", "recipients", "add", "seq-1", "--crm-list-id", "list-123"])
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output


def test_recipients_add_json(invoke, mock_api):
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])
    )
    result = invoke(["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["added"][0]["id"] == "rec-1"
    assert parsed["requires_confirmation"] == []


def test_recipients_add_raw_source(invoke, mock_api):
    """Raw --source JSON still works for advanced usage."""
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])
    )
    source = json.dumps({"type": "explicit", "prospect_ids": ["p1"]})
    result = invoke(["sequences", "recipients", "add", "seq-1", "--source", source])
    assert result.exit_code == 0


def test_recipients_add_invalid_json(invoke, mock_api):
    result = invoke(["sequences", "recipients", "add", "seq-1", "--source", "not json"])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_recipients_add_no_source(invoke, mock_api):
    """Error when no source is provided."""
    result = invoke(["sequences", "recipients", "add", "seq-1"])
    assert result.exit_code == 1


def test_recipients_add_partial_already_active(invoke, mock_api):
    """Some already active: added counted, already-active reported as skipped."""
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201,
        json=_add_response(
            added=[{"id": "rec-1", "prospect_id": "p3", "status": "active"}],
            already_active=["p1", "p2"],
        ),
    )
    result = invoke(["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2,p3"])
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output
    assert "2 already enrolled" in result.output


def test_recipients_add_422_error(invoke, mock_api):
    """API returns 422 validation error -> exit code 2."""
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        422, json={"detail": "The request contains invalid data."}
    )
    result = invoke(["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1"])
    assert result.exit_code == 2


def test_recipients_add_all_already_active(invoke, mock_api):
    """All already active -> info 'already enrolled', never a green 'Added'."""
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201, json=_add_response(already_active=["p1", "p2"])
    )
    result = invoke(["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1,p2"])
    assert result.exit_code == 0
    assert "2 already enrolled" in result.output
    assert "Added" not in result.output


def test_recipients_add_json_structured_passthrough(invoke, mock_api):
    """JSON output returns the structured body as-is."""
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201,
        json=_add_response(
            requires_confirmation=[
                {"prospect_id": "p1", "full_name": "Ada", "previous_status": "removed"}
            ]
        ),
    )
    result = invoke(["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["requires_confirmation"][0]["previous_status"] == "removed"


def test_recipients_add_previously_enrolled_declined(invoke, mock_api):
    """ENG-1188: previously-enrolled prospect warns; declining makes no re-call."""
    route = mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201,
        json=_add_response(
            requires_confirmation=[
                {"prospect_id": "p1", "full_name": "Ada Lovelace", "previous_status": "removed"}
            ]
        ),
    )
    result = invoke(
        ["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1"], input="n\n"
    )
    assert result.exit_code == 0
    assert "previously in this sequence" in result.output
    assert "--reenroll" in result.output
    assert route.call_count == 1  # no re-enrol re-call


def test_recipients_add_previously_enrolled_confirmed(invoke, mock_api):
    """Confirming the prompt re-calls with reenroll=true and reports the add."""
    mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").mock(
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
    result = invoke(
        ["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1"], input="y\n"
    )
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output


def test_recipients_add_reenroll_flag_sends_reenroll(invoke, mock_api):
    """--reenroll reactivates directly on the first call (no prompt)."""
    route = mock_api.post("/api/v1/sequences/sequences/seq-1/recipients").respond(
        201, json=_add_response(added=[{"id": "rec-1", "prospect_id": "p1"}])
    )
    result = invoke(
        ["sequences", "recipients", "add", "seq-1", "--prospect-ids", "p1", "--reenroll"]
    )
    assert result.exit_code == 0
    assert "Added 1 recipient" in result.output
    assert route.call_count == 1
    body = json.loads(route.calls.last.request.content)
    assert body["reenroll"] is True


def test_recipients_remove_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/sequences/sequences/seq-1/recipients/r1").respond(204)
    result = invoke(["sequences", "recipients", "remove", "seq-1", "r1", "--yes"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_recipients_remove_aborted(invoke, mock_api):
    result = invoke(["sequences", "recipients", "remove", "seq-1", "r1"], input="n\n")
    assert result.exit_code == 1


HISTORY = {
    "recipient_id": "rec-1",
    "steps": [
        {
            "step_id": "s1",
            "step_order": 1,
            "type": "message",
            "status": "sent",
            "subject": "One gap at Nuveau",
            "awaiting_approval_count": 0,
        },
        {"step_id": "s2", "step_order": 2, "type": "delay", "status": "upcoming"},
        {
            "step_id": "s5",
            "step_order": 5,
            "type": "task",
            "status": "sent",
            "connection_status": "not_accepted",
        },
        {
            "step_id": "s4",
            "step_order": 4,
            "type": "task",
            "status": "skipped",
            "skip_reason": "No phone number",
        },
        {
            "step_id": "s3",
            "step_order": 3,
            "type": "message",
            "status": "draft_generated",
            "awaiting_approval_count": 8,
        },
    ],
    "messages": [
        {
            "id": "c1",
            "direction": "outbound",
            "subject": "One gap at Nuveau",
            "communication_date": "2026-09-20T10:00:00Z",
        },
        {
            "id": "c2",
            "direction": "inbound",
            "subject": "Re: One gap at Nuveau",
            "communication_date": "2026-09-21T09:00:00Z",
        },
        {
            "id": "c3",
            "direction": "outbound",
            "subject": None,
            "communication_date": "2026-09-22T09:00:00Z",
            "channel": "linkedin",
        },
    ],
    "tasks": [
        {
            "id": "rs-4",
            "step_id": "s4",
            "activity_id": None,
            "activity_type": None,
            "title": None,
            "outcome": None,
            "suggested_message": None,
            "completed_at": "2026-09-19T09:00:00Z",
        },
        {
            "id": "rs-5",
            "step_id": "s5",
            "activity_id": "a1",
            "activity_type": "call",
            "title": "Call Jonah",
            "outcome": "Left a voicemail",
            "suggested_message": "Hi Jonah, a quick call.",
            "completed_at": "2026-09-24T09:00:00Z",
        },
    ],
}


def test_recipients_history(invoke, mock_api):
    mock_api.get("/api/v1/sequences/sequences/seq-1/recipients/rec-1/history").respond(
        200, json=HISTORY
    )
    result = invoke(["sequences", "recipients", "history", "seq-1", "rec-1"])
    assert result.exit_code == 0
    assert "One gap at Nuveau" in result.output
    assert "upcoming" in result.output
    assert "Waiting" in result.output
    assert "Reason" in result.output
    assert "8" in result.output
    assert "Re: One gap at Nuveau" in result.output
    assert "Channel" in result.output
    assert "linkedin" in result.output
    assert "Connection" in result.output
    assert "Tasks (2)" in result.output
    assert "call" in result.output
    assert "Call Jonah" in result.output
    assert "Left a voicemail" in result.output


def test_recipients_history_without_tasks(invoke, mock_api):
    """A response from an API that sends no tasks prints an empty Tasks table."""
    data = {key: value for key, value in HISTORY.items() if key != "tasks"}
    mock_api.get("/api/v1/sequences/sequences/seq-1/recipients/rec-1/history").respond(
        200, json=data
    )
    result = invoke(["sequences", "recipients", "history", "seq-1", "rec-1"])
    assert result.exit_code == 0
    assert "Tasks (0)" in result.output


def test_recipients_history_json(invoke, mock_api):
    mock_api.get("/api/v1/sequences/sequences/seq-1/recipients/rec-1/history").respond(
        200, json=HISTORY
    )
    result = invoke(["sequences", "recipients", "history", "seq-1", "rec-1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["messages"][1]["direction"] == "inbound"


def test_recipients_history_tasks_name_the_step_by_its_order(invoke, mock_api):
    """The Steps table shows the step order, so the Tasks table does too."""
    step_id = "9b1c2d3e-0000-4000-8000-000000000042"
    data = {
        "recipient_id": "rec-1",
        "steps": [{"step_id": step_id, "step_order": 6, "type": "task", "status": "task_created"}],
        "messages": [],
        "tasks": [
            {
                "id": "rs-6",
                "step_id": step_id,
                "activity_type": "call",
                "title": "Call Jonah",
                "outcome": None,
                "completed_at": "2026-09-24T09:00:00Z",
            }
        ],
    }
    mock_api.get("/api/v1/sequences/sequences/seq-1/recipients/rec-1/history").respond(
        200, json=data
    )
    result = invoke(["sequences", "recipients", "history", "seq-1", "rec-1"])
    assert result.exit_code == 0
    tasks_table = result.output.split("Tasks (1)", 1)[1]
    assert "9b1c2d3e" not in tasks_table
    assert "│ 6 " in tasks_table or "│ 6" in tasks_table
