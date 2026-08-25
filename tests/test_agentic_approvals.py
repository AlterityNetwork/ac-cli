"""Tests for the agentic platform approval commands.

`ac agentic approvals` drives the Approval Inbox. The four commands are the
whole surface a person needs to see and answer a paused run.
"""

import json

_BASE = "/api/v1/agentic/approvals"

SAMPLE_APPROVAL = {
    "id": "11111111-1111-4111-8111-111111111111",
    "run_id": "22222222-2222-4222-8222-222222222222",
    "root_run_id": "22222222-2222-4222-8222-222222222222",
    "raised_by": "action",
    "action": "email.send",
    "target_summary": "Sarah Chen at Acme",
    "preview": "send the follow up draft",
    "status": "pending",
    "created_at": "2026-08-25T10:00:00Z",
    "expires_at": "2026-08-26T10:00:00Z",
    "reason": "an email to a new recipient needs approval",
    "proposed_arguments": {"to": "sarah@acme.test", "subject": "Following up"},
    "arguments_hash": "a" * 64,
    "resolved_by": None,
    "resolved_at": None,
}

SAMPLE_PAGE = {"items": [SAMPLE_APPROVAL], "next_cursor": None}


# --- list ------------------------------------------------------------------


def test_approvals_list(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "approvals", "list"])

    assert result.exit_code == 0
    assert "email.send" in result.output
    assert route.called


def test_approvals_list_defaults_to_the_work_that_waits(invoke, mock_api):
    """The endpoint reads pending when no status is named, and so does this."""
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    invoke(["agentic", "approvals", "list"])

    assert "status" not in route.calls[0].request.url.params


def test_approvals_list_sends_the_status_it_was_given(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    invoke(["agentic", "approvals", "list", "--status", "expired"])

    assert route.calls[0].request.url.params["status"] == "expired"


def test_approvals_list_pages(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json={**SAMPLE_PAGE, "next_cursor": "abc"})
    result = invoke(["agentic", "approvals", "list", "--cursor", "xyz", "--limit", "5"])

    assert route.calls[0].request.url.params["cursor"] == "xyz"
    assert route.calls[0].request.url.params["limit"] == "5"
    assert "abc" in result.output


def test_approvals_list_json(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "approvals", "list", "--json"])

    assert json.loads(result.output) == SAMPLE_PAGE


def test_a_bracket_in_a_preview_does_not_break_the_table(invoke, mock_api):
    """The model writes the preview, so no cell reaches the markup parser."""
    mock_api.get(_BASE).respond(
        200,
        json={
            "items": [{**SAMPLE_APPROVAL, "preview": "send to [Acme] (formerly Beta)"}],
            "next_cursor": None,
        },
    )
    result = invoke(["agentic", "approvals", "list"])

    assert result.exit_code == 0
    assert "[Acme]" in result.output


# --- get -------------------------------------------------------------------


def test_approvals_get(invoke, mock_api):
    route = mock_api.get(f"{_BASE}/{SAMPLE_APPROVAL['id']}").respond(200, json=SAMPLE_APPROVAL)
    result = invoke(["agentic", "approvals", "get", SAMPLE_APPROVAL["id"]])

    assert result.exit_code == 0
    assert route.called
    assert "email.send" in result.output


def test_approvals_get_prints_the_proposal(invoke, mock_api):
    """A person authorizes an exact proposal, so the command shows it."""
    mock_api.get(f"{_BASE}/{SAMPLE_APPROVAL['id']}").respond(200, json=SAMPLE_APPROVAL)
    result = invoke(["agentic", "approvals", "get", SAMPLE_APPROVAL["id"]])

    assert "sarah@acme.test" in result.output


def test_approvals_get_json(invoke, mock_api):
    mock_api.get(f"{_BASE}/{SAMPLE_APPROVAL['id']}").respond(200, json=SAMPLE_APPROVAL)
    result = invoke(["agentic", "approvals", "get", SAMPLE_APPROVAL["id"], "--json"])

    assert json.loads(result.output) == SAMPLE_APPROVAL


def test_approvals_get_not_found(invoke, mock_api):
    mock_api.get(f"{_BASE}/{SAMPLE_APPROVAL['id']}").respond(
        404, json={"detail": "approval not found"}
    )
    result = invoke(["agentic", "approvals", "get", SAMPLE_APPROVAL["id"]])

    assert result.exit_code == 3


# --- approve and reject ----------------------------------------------------


def test_approve_asks_first(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/approve").respond(
        200, json={**SAMPLE_APPROVAL, "status": "approved"}
    )
    result = invoke(["agentic", "approvals", "approve", SAMPLE_APPROVAL["id"]], input="n\n")

    assert result.exit_code != 0


def test_approve_with_yes(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/approve").respond(
        200, json={**SAMPLE_APPROVAL, "status": "approved"}
    )
    result = invoke(["agentic", "approvals", "approve", SAMPLE_APPROVAL["id"], "--yes"])

    assert result.exit_code == 0
    assert route.called
    assert "approved" in result.output


def test_approve_sends_no_idempotency_key(invoke, mock_api):
    """This route starts no run, so the shared key rule does not reach it."""
    route = mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/approve").respond(
        200, json={**SAMPLE_APPROVAL, "status": "approved"}
    )
    invoke(["agentic", "approvals", "approve", SAMPLE_APPROVAL["id"], "--yes"])

    assert "Idempotency-Key" not in route.calls[0].request.headers


def test_reject_asks_first(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/reject").respond(
        200, json={**SAMPLE_APPROVAL, "status": "rejected"}
    )
    result = invoke(["agentic", "approvals", "reject", SAMPLE_APPROVAL["id"]], input="n\n")

    assert result.exit_code != 0


def test_reject_with_yes(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/reject").respond(
        200, json={**SAMPLE_APPROVAL, "status": "rejected"}
    )
    result = invoke(["agentic", "approvals", "reject", SAMPLE_APPROVAL["id"], "--yes"])

    assert result.exit_code == 0
    assert route.called
    assert "rejected" in result.output


def test_a_decision_somebody_else_made_is_reported_as_such(invoke, mock_api):
    """A repeated resolve answers 200 with the current state, never 409.

    So the command reads the status back and does not claim this caller made
    the decision.
    """
    mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/approve").respond(
        200,
        json={
            **SAMPLE_APPROVAL,
            "status": "rejected",
            "resolved_by": "99999999-9999-4999-8999-999999999999",
            "resolved_at": "2026-08-25T10:05:00Z",
        },
    )
    result = invoke(["agentic", "approvals", "approve", SAMPLE_APPROVAL["id"], "--yes"])

    assert result.exit_code == 0
    assert "rejected" in result.output


def test_a_lapsed_row_reports_expired(invoke, mock_api):
    """The API writes nothing on a dead row, and the status is the answer."""
    mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/approve").respond(
        200, json={**SAMPLE_APPROVAL, "status": "expired"}
    )
    result = invoke(["agentic", "approvals", "approve", SAMPLE_APPROVAL["id"], "--yes"])

    assert result.exit_code == 0
    assert "expired" in result.output


def test_an_impersonated_session_is_refused(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/approve").respond(
        403, json={"detail": "an impersonated session may not resolve one"}
    )
    result = invoke(["agentic", "approvals", "approve", SAMPLE_APPROVAL["id"], "--yes"])

    assert result.exit_code != 0


def test_approve_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/approve").respond(
        200, json={**SAMPLE_APPROVAL, "status": "approved"}
    )
    result = invoke(["agentic", "approvals", "approve", SAMPLE_APPROVAL["id"], "--yes", "--json"])

    assert json.loads(result.output)["status"] == "approved"


def test_reject_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SAMPLE_APPROVAL['id']}/reject").respond(
        200, json={**SAMPLE_APPROVAL, "status": "rejected"}
    )
    result = invoke(["agentic", "approvals", "reject", SAMPLE_APPROVAL["id"], "--yes", "--json"])

    assert json.loads(result.output)["status"] == "rejected"
