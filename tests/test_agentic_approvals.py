"""Tests for ac agentic approvals commands."""

import json

_BASE = "/api/v1/agentic/approvals"
_AID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

SAMPLE_DETAIL = {
    "id": _AID,
    "run_id": "run-111",
    "root_run_id": "run-000",
    "raised_by": "agent",
    "action": "send_email",
    "target_summary": "alice@example.com",
    "display_status": "pending",
    "preview": "Dear Alice...",
    "proposed_content": {"to": "alice@example.com"},
    "reason": "High-value contact",
    "resolved_by": None,
    "resolved_at": None,
    "expires_at": "2099-01-01T00:00:00Z",
    "created_at": "2026-08-23T10:00:00Z",
}

SAMPLE_SUMMARY = {
    "id": _AID,
    "run_id": "run-111",
    "root_run_id": "run-000",
    "raised_by": "agent",
    "action": "send_email",
    "target_summary": "alice@example.com",
    "display_status": "pending",
    "expires_at": "2099-01-01T00:00:00Z",
    "created_at": "2026-08-23T10:00:00Z",
}

_PAGE = {"items": [SAMPLE_SUMMARY], "next_cursor": None, "has_more": False}


# ── list ────────────────────────────────────────────────────────────────────


def test_approvals_list_happy_path(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=_PAGE)
    result = invoke(["agentic", "approvals", "list"])
    assert result.exit_code == 0
    assert "send_email" in result.output


def test_approvals_list_json(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=_PAGE)
    result = invoke(["agentic", "approvals", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"][0]["id"] == _AID


def test_approvals_list_status_param(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=_PAGE)
    result = invoke(["agentic", "approvals", "list", "--status", "pending"])
    assert result.exit_code == 0
    assert route.calls[0].request.url.params["status"] == "pending"


def test_approvals_list_cursor_param(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=_PAGE)
    result = invoke(["agentic", "approvals", "list", "--cursor", "tok123"])
    assert result.exit_code == 0
    assert route.calls[0].request.url.params["cursor"] == "tok123"


def test_approvals_list_no_status_param_by_default(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=_PAGE)
    result = invoke(["agentic", "approvals", "list"])
    assert result.exit_code == 0
    assert "status" not in route.calls[0].request.url.params


def test_approvals_list_prints_next_cursor(invoke, mock_api):
    page = {"items": [SAMPLE_SUMMARY], "next_cursor": "cursor-abc", "has_more": True}
    mock_api.get(_BASE).respond(200, json=page)
    result = invoke(["agentic", "approvals", "list"])
    assert result.exit_code == 0
    assert "cursor-abc" in result.output


# ── read ────────────────────────────────────────────────────────────────────


def test_approvals_read_happy_path(invoke, mock_api):
    mock_api.get(f"{_BASE}/{_AID}").respond(200, json=SAMPLE_DETAIL)
    result = invoke(["agentic", "approvals", "read", _AID])
    assert result.exit_code == 0
    assert "send_email" in result.output
    assert "alice@example.com" in result.output


def test_approvals_read_json(invoke, mock_api):
    mock_api.get(f"{_BASE}/{_AID}").respond(200, json=SAMPLE_DETAIL)
    result = invoke(["agentic", "approvals", "read", _AID, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == _AID


def test_approvals_read_not_found(invoke, mock_api):
    mock_api.get(f"{_BASE}/{_AID}").respond(404, json={"detail": "not found"})
    result = invoke(["agentic", "approvals", "read", _AID])
    assert result.exit_code == 3
    assert "404" in result.output


def test_approvals_read_json_error(invoke, mock_api):
    mock_api.get(f"{_BASE}/{_AID}").respond(404, json={"detail": "not found"})
    result = invoke(["agentic", "approvals", "read", _AID, "--json"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 404


# ── approve ─────────────────────────────────────────────────────────────────


def test_approvals_approve_with_yes(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_AID}/approve").respond(200, json=SAMPLE_DETAIL)
    result = invoke(["agentic", "approvals", "approve", _AID, "--yes"])
    assert result.exit_code == 0
    assert route.called
    assert _AID in result.output


def test_approvals_approve_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_AID}/approve").respond(200, json=SAMPLE_DETAIL)
    result = invoke(["agentic", "approvals", "approve", _AID, "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == _AID


def test_approvals_approve_prompts_without_yes(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_AID}/approve").respond(200, json=SAMPLE_DETAIL)
    result = invoke(["agentic", "approvals", "approve", _AID], input="y\n")
    assert result.exit_code == 0
    assert route.called


def test_approvals_approve_abort_without_yes(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_AID}/approve").respond(200, json=SAMPLE_DETAIL)
    result = invoke(["agentic", "approvals", "approve", _AID], input="n\n")
    assert result.exit_code == 1
    assert not route.called


def test_approvals_approve_not_found(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_AID}/approve").respond(404, json={"detail": "not found"})
    result = invoke(["agentic", "approvals", "approve", _AID, "--yes"])
    assert result.exit_code == 3


# ── reject ──────────────────────────────────────────────────────────────────


def test_approvals_reject_with_yes(invoke, mock_api):
    rejected = {**SAMPLE_DETAIL, "display_status": "rejected"}
    route = mock_api.post(f"{_BASE}/{_AID}/reject").respond(200, json=rejected)
    result = invoke(["agentic", "approvals", "reject", _AID, "--yes"])
    assert result.exit_code == 0
    assert route.called
    assert _AID in result.output


def test_approvals_reject_json(invoke, mock_api):
    rejected = {**SAMPLE_DETAIL, "display_status": "rejected"}
    mock_api.post(f"{_BASE}/{_AID}/reject").respond(200, json=rejected)
    result = invoke(["agentic", "approvals", "reject", _AID, "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["display_status"] == "rejected"


def test_approvals_reject_prompts_without_yes(invoke, mock_api):
    rejected = {**SAMPLE_DETAIL, "display_status": "rejected"}
    route = mock_api.post(f"{_BASE}/{_AID}/reject").respond(200, json=rejected)
    result = invoke(["agentic", "approvals", "reject", _AID], input="y\n")
    assert result.exit_code == 0
    assert route.called


def test_approvals_reject_abort_without_yes(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_AID}/reject").respond(200, json=SAMPLE_DETAIL)
    result = invoke(["agentic", "approvals", "reject", _AID], input="n\n")
    assert result.exit_code == 1
    assert not route.called


def test_approvals_reject_not_found(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_AID}/reject").respond(404, json={"detail": "not found"})
    result = invoke(["agentic", "approvals", "reject", _AID, "--yes"])
    assert result.exit_code == 3
