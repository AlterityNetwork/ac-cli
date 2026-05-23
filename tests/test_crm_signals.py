"""Tests for CRM signals commands."""

import json

SIGNAL = {
    "id": "sig-1",
    "signal_type": "funding",
    "description": "Series B raised",
    "signal_date": "2026-05-01",
    "source_url": "https://example.com",
    "source_agent": "manual",
    "snippet": None,
    "workflow_run_id": None,
    "created_at": "2026-05-10T00:00:00Z",
}


def test_signals_list(invoke, mock_api):
    mock_api.get("/api/v1/crm/signals").respond(
        200, json={"data": [SIGNAL], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["crm", "signals", "list"])
    assert result.exit_code == 0
    assert "funding" in result.output


def test_signals_list_filters(invoke, mock_api):
    route = mock_api.get("/api/v1/crm/signals").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(
        [
            "crm",
            "signals",
            "list",
            "--signal-type",
            "funding",
            "--company-id",
            "c-1",
            "--limit",
            "10",
            "--json",
        ]
    )
    assert result.exit_code == 0
    assert route.called
    qs = route.calls.last.request.url.params
    assert qs["signal_type"] == "funding"
    assert qs["company_id"] == "c-1"
    assert qs["limit"] == "10"


def test_signals_list_workflow_run_company_id(invoke, mock_api):
    """ENG-961 F10: --workflow-run-company-id forwards to /crm/signals as a query param."""
    route = mock_api.get("/api/v1/crm/signals").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(
        [
            "crm",
            "signals",
            "list",
            "--workflow-run-company-id",
            "wrc-123",
            "--json",
        ]
    )
    assert result.exit_code == 0
    assert route.called
    qs = route.calls.last.request.url.params
    assert qs["workflow_run_company_id"] == "wrc-123"


def test_signals_get(invoke, mock_api):
    mock_api.get("/api/v1/crm/signals/sig-1").respond(200, json=SIGNAL)
    result = invoke(["crm", "signals", "get", "sig-1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == "sig-1"


def test_signals_create_company(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/signals").respond(201, json=SIGNAL)
    result = invoke(
        [
            "crm",
            "signals",
            "create",
            "--signal-type",
            "funding",
            "--description",
            "Series B raised",
            "--company-id",
            "c-1",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["signal_type"] == "funding"
    assert body["attach_to"] == {"subject_type": "company", "subject_id": "c-1"}


def test_signals_create_requires_one_subject(invoke, mock_api):
    result = invoke(["crm", "signals", "create", "--signal-type", "funding", "--description", "x"])
    assert result.exit_code == 1
    assert "exactly one" in result.output


def test_signals_create_rejects_both_subjects(invoke, mock_api):
    result = invoke(
        [
            "crm",
            "signals",
            "create",
            "--signal-type",
            "funding",
            "--description",
            "x",
            "--company-id",
            "c-1",
            "--person-id",
            "p-1",
        ]
    )
    assert result.exit_code == 1


def test_signals_attach_person_with_score(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/signals/sig-1/attach").respond(200, json=SIGNAL)
    result = invoke(
        [
            "crm",
            "signals",
            "attach",
            "sig-1",
            "--person-id",
            "p-9",
            "--score",
            "80",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "attach_to": {"subject_type": "person", "subject_id": "p-9", "attachment_score": 80}
    }


def test_signals_delete_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/signals/sig-1").respond(204)
    result = invoke(["crm", "signals", "delete", "sig-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted signal sig-1" in result.output


def test_signals_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "signals", "delete", "sig-1"], input="n\n")
    assert result.exit_code == 1


def test_signals_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/crm/signals/missing").respond(404, json={"detail": "not found"})
    result = invoke(["crm", "signals", "get", "missing"])
    assert result.exit_code == 3
