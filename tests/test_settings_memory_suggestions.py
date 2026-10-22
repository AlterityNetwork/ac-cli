"""Tests for `ac settings memory suggestions` (memory lines learned from edits)."""

import json

_BASE = "/api/v1/settings/memory/suggestions"

SUGGESTION = {
    "id": "22222222-2222-2222-2222-222222222222",
    "text": "Use UK spelling [en-GB]",
    "evidence_count": 4,
    "recipient_count": 3,
    "examples": [{"before": "color", "after": "colour"}],
    "created_at": "2026-10-09T09:00:00+00:00",
}
SUGGESTION_ID = SUGGESTION["id"]
LIST = {"data": [SUGGESTION], "total": 1}

LINE = {
    "id": "11111111-1111-1111-1111-111111111111",
    "text": "Use UK spelling [en-GB]",
    "applies_to": "email",
    "source": "learned",
    "created_at": "2026-10-09T10:00:00+00:00",
    "updated_at": "2026-10-09T10:00:00+00:00",
}


def test_suggestions_list_prints_a_table(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=LIST)
    result = invoke(["settings", "memory", "suggestions", "list"])
    assert result.exit_code == 0, result.output
    assert SUGGESTION_ID[:8] in result.output
    assert "[en-GB]" in result.output
    assert "4 emails / 3 people" in result.output
    assert "colour" not in result.output


def test_suggestions_list_empty(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json={"data": [], "total": 0})
    result = invoke(["settings", "memory", "suggestions", "list"])
    assert result.exit_code == 0
    assert "No suggestions" in result.output


def test_suggestions_list_json_keeps_the_examples(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=LIST)
    result = invoke(["settings", "memory", "suggestions", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == LIST


def test_suggestions_list_forbidden_json(invoke, mock_api):
    mock_api.get(_BASE).respond(403, json={"detail": "Not allowed"})
    result = invoke(["settings", "memory", "suggestions", "list", "--json"])
    assert result.exit_code == 4
    assert json.loads(result.output)["status_code"] == 403


def test_suggestions_refresh_prints_the_counts(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/refresh").respond(200, json={"emails_read": 12, "proposed": 2})
    result = invoke(["settings", "memory", "suggestions", "refresh"])
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.content == b""
    assert "Read 12 emails. 2 new suggestions." in result.output


def test_suggestions_refresh_json(invoke, mock_api):
    body = {"emails_read": 12, "proposed": 2}
    mock_api.post(f"{_BASE}/refresh").respond(200, json=body)
    result = invoke(["settings", "memory", "suggestions", "refresh", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == body


def test_suggestions_accept_without_text_sends_an_empty_body(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{SUGGESTION_ID}/accept").respond(201, json=LINE)
    result = invoke(["settings", "memory", "suggestions", "accept", SUGGESTION_ID])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {}
    assert LINE["id"] in result.output
    assert "[en-GB]" in result.output


def test_suggestions_accept_with_text_sends_the_text(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{SUGGESTION_ID}/accept").respond(201, json=LINE)
    result = invoke(
        ["settings", "memory", "suggestions", "accept", SUGGESTION_ID, "--text", "Use UK English"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"text": "Use UK English"}


def test_suggestions_accept_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SUGGESTION_ID}/accept").respond(201, json=LINE)
    result = invoke(["settings", "memory", "suggestions", "accept", SUGGESTION_ID, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == LINE


def test_suggestions_accept_at_the_cap_is_400(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SUGGESTION_ID}/accept").respond(
        400, json={"detail": "You can keep 50 memories. Remove one to add another."}
    )
    result = invoke(["settings", "memory", "suggestions", "accept", SUGGESTION_ID, "--json"])
    assert result.exit_code == 1
    body = json.loads(result.output)
    assert body["status_code"] == 400
    assert "50 memories" in body["detail"]


def test_suggestions_accept_not_found(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SUGGESTION_ID}/accept").respond(
        404, json={"detail": "Suggestion not found"}
    )
    result = invoke(["settings", "memory", "suggestions", "accept", SUGGESTION_ID, "--json"])
    assert result.exit_code == 3
    assert json.loads(result.output)["status_code"] == 404


def test_suggestions_accept_conflict(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SUGGESTION_ID}/accept").respond(
        409, json={"detail": "The suggestion is not proposed"}
    )
    result = invoke(["settings", "memory", "suggestions", "accept", SUGGESTION_ID, "--json"])
    assert result.exit_code == 5
    assert json.loads(result.output)["status_code"] == 409


def test_suggestions_dismiss(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{SUGGESTION_ID}/dismiss").respond(204)
    result = invoke(["settings", "memory", "suggestions", "dismiss", SUGGESTION_ID, "--yes"])
    assert result.exit_code == 0, result.output
    assert route.called
    assert f"Dismissed suggestion {SUGGESTION_ID}" in result.output


def test_suggestions_dismiss_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SUGGESTION_ID}/dismiss").respond(204)
    result = invoke(["settings", "memory", "suggestions", "dismiss", SUGGESTION_ID, "-y", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"ok": True, "id": SUGGESTION_ID, "action": "dismiss"}


def test_suggestions_dismiss_abort(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{SUGGESTION_ID}/dismiss").respond(204)
    result = invoke(["settings", "memory", "suggestions", "dismiss", SUGGESTION_ID], input="n\n")
    assert result.exit_code != 0
    assert not route.called


def test_suggestions_dismiss_ac_yes_skips_the_prompt(invoke, mock_api, monkeypatch):
    monkeypatch.setenv("AC_YES", "1")
    route = mock_api.post(f"{_BASE}/{SUGGESTION_ID}/dismiss").respond(204)
    result = invoke(["settings", "memory", "suggestions", "dismiss", SUGGESTION_ID])
    assert result.exit_code == 0
    assert route.called


def test_suggestions_dismiss_not_found(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SUGGESTION_ID}/dismiss").respond(
        404, json={"detail": "Suggestion not found"}
    )
    result = invoke(["settings", "memory", "suggestions", "dismiss", SUGGESTION_ID, "--yes"])
    assert result.exit_code == 3


def test_suggestions_dismiss_conflict(invoke, mock_api):
    mock_api.post(f"{_BASE}/{SUGGESTION_ID}/dismiss").respond(
        409, json={"detail": "The suggestion is not proposed"}
    )
    result = invoke(
        ["settings", "memory", "suggestions", "dismiss", SUGGESTION_ID, "--yes", "--json"]
    )
    assert result.exit_code == 5
    assert json.loads(result.output)["status_code"] == 409
