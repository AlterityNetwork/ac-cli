"""Tests for `ac settings memory` (personal memory lines)."""

import json

_BASE = "/api/v1/settings/memory"

LINE = {
    "id": "11111111-1111-1111-1111-111111111111",
    "text": "Sign off as Marc [no title]",
    "applies_to": "email",
    "source": "user",
    "created_at": "2026-10-09T09:00:00+00:00",
    "updated_at": "2026-10-09T09:00:00+00:00",
}
LINE_ID = LINE["id"]
LIST = {"data": [LINE], "total": 1, "max_lines": 50}


def test_memory_list_prints_a_table(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=LIST)
    result = invoke(["settings", "memory", "list"])
    assert result.exit_code == 0, result.output
    assert "1 of 50" in result.output
    assert "[no title]" in result.output
    assert "email" in result.output


def test_memory_list_empty(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json={"data": [], "total": 0, "max_lines": 50})
    result = invoke(["settings", "memory", "list"])
    assert result.exit_code == 0
    assert "No memories" in result.output


def test_memory_list_json(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=LIST)
    result = invoke(["settings", "memory", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == LIST


def test_memory_list_forbidden_json(invoke, mock_api):
    mock_api.get(_BASE).respond(403, json={"detail": "Not allowed"})
    result = invoke(["settings", "memory", "list", "--json"])
    assert result.exit_code == 4
    assert json.loads(result.output)["status_code"] == 403


def test_memory_add_sends_the_text_and_the_default(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json={**LINE, "applies_to": "all"})
    result = invoke(["settings", "memory", "add", "--text", "Sign off as Marc"])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"text": "Sign off as Marc"}
    assert LINE_ID in result.output


def test_memory_add_applies_to_email(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=LINE)
    result = invoke(
        ["settings", "memory", "add", "--text", "Sign off as Marc", "--applies-to", "email"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "text": "Sign off as Marc",
        "applies_to": "email",
    }


def test_memory_add_json(invoke, mock_api):
    mock_api.post(_BASE).respond(201, json=LINE)
    result = invoke(["settings", "memory", "add", "--text", "x", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == LINE


def test_memory_add_rejects_an_unknown_applies_to(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=LINE)
    result = invoke(["settings", "memory", "add", "--text", "x", "--applies-to", "chat"])
    assert result.exit_code == 2
    assert not route.called


def test_memory_add_limit_reached_is_400(invoke, mock_api):
    mock_api.post(_BASE).respond(
        400, json={"detail": "You can keep 50 memories. Remove one to add another."}
    )
    result = invoke(["settings", "memory", "add", "--text", "x", "--json"])
    assert result.exit_code == 1
    body = json.loads(result.output)
    assert body["status_code"] == 400
    assert "50 memories" in body["detail"]


def test_memory_add_validation_is_422(invoke, mock_api):
    mock_api.post(_BASE).respond(422, json={"detail": "text is too long"})
    result = invoke(["settings", "memory", "add", "--text", "x"])
    assert result.exit_code == 2


def test_memory_edit_sends_only_the_given_fields(invoke, mock_api):
    route = mock_api.patch(f"{_BASE}/{LINE_ID}").respond(200, json=LINE)
    result = invoke(["settings", "memory", "edit", LINE_ID, "--applies-to", "email"])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"applies_to": "email"}
    assert LINE_ID in result.output


def test_memory_edit_text_json(invoke, mock_api):
    route = mock_api.patch(f"{_BASE}/{LINE_ID}").respond(200, json=LINE)
    result = invoke(["settings", "memory", "edit", LINE_ID, "--text", "New line", "--json"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"text": "New line"}
    assert json.loads(result.output) == LINE


def test_memory_edit_with_no_field_refuses(invoke, mock_api):
    route = mock_api.patch(f"{_BASE}/{LINE_ID}").respond(200, json=LINE)
    result = invoke(["settings", "memory", "edit", LINE_ID, "--json"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] is True
    assert not route.called


def test_memory_edit_not_found(invoke, mock_api):
    mock_api.patch(f"{_BASE}/{LINE_ID}").respond(404, json={"detail": "Memory not found"})
    result = invoke(["settings", "memory", "edit", LINE_ID, "--text", "x", "--json"])
    assert result.exit_code == 3
    assert json.loads(result.output)["status_code"] == 404


def test_memory_edit_validation_is_422(invoke, mock_api):
    mock_api.patch(f"{_BASE}/not-a-uuid").respond(422, json={"detail": "bad id"})
    result = invoke(["settings", "memory", "edit", "not-a-uuid", "--text", "x"])
    assert result.exit_code == 2


def test_memory_remove(invoke, mock_api):
    route = mock_api.delete(f"{_BASE}/{LINE_ID}").respond(204)
    result = invoke(["settings", "memory", "remove", LINE_ID, "--yes"])
    assert result.exit_code == 0, result.output
    assert route.called
    assert f"Removed memory {LINE_ID}" in result.output


def test_memory_remove_json(invoke, mock_api):
    mock_api.delete(f"{_BASE}/{LINE_ID}").respond(204)
    result = invoke(["settings", "memory", "remove", LINE_ID, "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"ok": True, "id": LINE_ID, "action": "remove"}


def test_memory_remove_abort(invoke, mock_api):
    route = mock_api.delete(f"{_BASE}/{LINE_ID}").respond(204)
    result = invoke(["settings", "memory", "remove", LINE_ID], input="n\n")
    assert result.exit_code != 0
    assert not route.called


def test_memory_remove_ac_yes_skips_the_prompt(invoke, mock_api, monkeypatch):
    monkeypatch.setenv("AC_YES", "1")
    route = mock_api.delete(f"{_BASE}/{LINE_ID}").respond(204)
    result = invoke(["settings", "memory", "remove", LINE_ID])
    assert result.exit_code == 0
    assert route.called


def test_memory_remove_not_found(invoke, mock_api):
    mock_api.delete(f"{_BASE}/{LINE_ID}").respond(404, json={"detail": "Memory not found"})
    result = invoke(["settings", "memory", "remove", LINE_ID, "--yes"])
    assert result.exit_code == 3
