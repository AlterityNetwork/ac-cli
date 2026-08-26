"""Tests for the agentic platform policy commands.

`ac agentic policies` drives the rules an organization governs its agents with.
A rule restricts and it never grants, so the four commands are a list, a
create, an edit and a delete.
"""

import json

_BASE = "/api/v1/agentic/policies"

SAMPLE_POLICY = {
    "id": "11111111-1111-4111-8111-111111111111",
    "name": "no bulk email",
    "action": "email.send",
    "decision": "deny",
    "definition_id": None,
    "conditions": None,
    "approval_ttl_seconds": None,
    "enabled": True,
    "created_at": "2026-08-25T09:00:00Z",
    "updated_at": "2026-08-25T10:00:00.123456+00:00",
}

SAMPLE_PAGE = {"items": [SAMPLE_POLICY], "next_cursor": None}

_ID = SAMPLE_POLICY["id"]
_TOKEN = SAMPLE_POLICY["updated_at"]


# --- list ------------------------------------------------------------------


def test_policies_list(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "policies", "list"])

    assert result.exit_code == 0
    assert "no bulk email" in result.output
    assert route.called


def test_policies_list_json_carries_the_write_token(invoke, mock_api):
    """There is no detail route, so the list is where `patch` reads the token.

    The table drops it. It is 32 characters, and a sixth column of that width
    truncates every other one to nothing.
    """
    mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "policies", "list", "--json"])

    assert json.loads(result.output)["items"][0]["updated_at"] == _TOKEN


def test_policies_list_filters_the_action(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    invoke(["agentic", "policies", "list", "--action", "email.send"])

    assert route.calls[0].request.url.params["action"] == "email.send"


def test_policies_list_pages(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json={**SAMPLE_PAGE, "next_cursor": "abc"})
    result = invoke(["agentic", "policies", "list", "--cursor", "xyz", "--limit", "5"])

    assert route.calls[0].request.url.params["cursor"] == "xyz"
    assert route.calls[0].request.url.params["limit"] == "5"
    assert "abc" in result.output


def test_policies_list_json(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "policies", "list", "--json"])

    assert json.loads(result.output) == SAMPLE_PAGE


# --- create ----------------------------------------------------------------


def test_policies_create(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=SAMPLE_POLICY)
    result = invoke(
        [
            "agentic",
            "policies",
            "create",
            "--name",
            "no bulk email",
            "--action",
            "email.send",
            "--decision",
            "deny",
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "name": "no bulk email",
        "action": "email.send",
        "decision": "deny",
        "enabled": True,
    }


def test_policies_create_sends_a_condition_tree(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=SAMPLE_POLICY)
    invoke(
        [
            "agentic",
            "policies",
            "create",
            "--name",
            "gate large sends",
            "--action",
            "email.send",
            "--decision",
            "require_approval",
            "--ttl",
            "3600",
            "--conditions",
            '{"op": "gt", "path": "arguments.limit", "value": 1000}',
        ]
    )

    body = json.loads(route.calls[0].request.content)
    assert body["conditions"] == {
        "op": "gt",
        "path": "arguments.limit",
        "value": 1000,
    }
    assert body["approval_ttl_seconds"] == 3600


def test_policies_create_refuses_a_condition_tree_that_is_not_json(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=SAMPLE_POLICY)
    result = invoke(
        [
            "agentic",
            "policies",
            "create",
            "--name",
            "x",
            "--action",
            "email.send",
            "--decision",
            "deny",
            "--conditions",
            "{not json",
        ]
    )

    assert result.exit_code == 1
    assert not route.called


def test_policies_create_can_start_disabled(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=SAMPLE_POLICY)
    invoke(
        [
            "agentic",
            "policies",
            "create",
            "--name",
            "x",
            "--action",
            "email.send",
            "--decision",
            "deny",
            "--disabled",
        ]
    )

    assert json.loads(route.calls[0].request.content)["enabled"] is False


def test_policies_create_reports_a_refused_rule(invoke, mock_api):
    """A rule this deploy cannot govern answers `400`, and the reason names
    which check refused it."""
    mock_api.post(_BASE).respond(
        400,
        json={
            "detail": {
                "code": "unknown_action",
                "reason": "no tool and no checkpoint answers the action 'crm.udpate'",
            }
        },
    )
    result = invoke(
        [
            "agentic",
            "policies",
            "create",
            "--name",
            "x",
            "--action",
            "crm.udpate",
            "--decision",
            "deny",
        ]
    )

    assert result.exit_code == 1


def test_policies_create_json(invoke, mock_api):
    mock_api.post(_BASE).respond(201, json=SAMPLE_POLICY)
    result = invoke(
        [
            "agentic",
            "policies",
            "create",
            "--name",
            "x",
            "--action",
            "email.send",
            "--decision",
            "deny",
            "--json",
        ]
    )

    assert json.loads(result.output) == SAMPLE_POLICY


# --- patch -----------------------------------------------------------------


def test_policies_patch(invoke, mock_api):
    route = mock_api.patch(f"{_BASE}/{_ID}").respond(200, json=SAMPLE_POLICY)
    result = invoke(
        [
            "agentic",
            "policies",
            "patch",
            _ID,
            "--expected-updated-at",
            _TOKEN,
            "--patch",
            '{"enabled": false}',
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "expected_updated_at": _TOKEN,
        "enabled": False,
    }


def test_policies_patch_sends_an_explicit_null(invoke, mock_api):
    """A null clears the narrowing. A merge cannot remove anything, so the
    patch replaces each named field whole."""
    route = mock_api.patch(f"{_BASE}/{_ID}").respond(200, json=SAMPLE_POLICY)
    invoke(
        [
            "agentic",
            "policies",
            "patch",
            _ID,
            "--expected-updated-at",
            _TOKEN,
            "--patch",
            '{"definition_id": null}',
        ]
    )

    body = json.loads(route.calls[0].request.content)
    assert "definition_id" in body
    assert body["definition_id"] is None


def test_policies_patch_reports_a_stale_token(invoke, mock_api):
    mock_api.patch(f"{_BASE}/{_ID}").respond(
        409, json={"detail": "the rule changed since you read it"}
    )
    result = invoke(
        [
            "agentic",
            "policies",
            "patch",
            _ID,
            "--expected-updated-at",
            "older",
            "--patch",
            '{"enabled": false}',
        ]
    )

    assert result.exit_code == 5


def test_policies_patch_json(invoke, mock_api):
    mock_api.patch(f"{_BASE}/{_ID}").respond(200, json=SAMPLE_POLICY)
    result = invoke(
        [
            "agentic",
            "policies",
            "patch",
            _ID,
            "--expected-updated-at",
            _TOKEN,
            "--patch",
            '{"enabled": false}',
            "--json",
        ]
    )

    assert json.loads(result.output) == SAMPLE_POLICY


# --- delete ----------------------------------------------------------------


def test_policies_delete(invoke, mock_api):
    route = mock_api.delete(f"{_BASE}/{_ID}").respond(204)
    result = invoke(["agentic", "policies", "delete", _ID, "--yes"])

    assert result.exit_code == 0
    assert route.called


def test_policies_delete_asks_first(invoke, mock_api):
    route = mock_api.delete(f"{_BASE}/{_ID}").respond(204)
    result = invoke(["agentic", "policies", "delete", _ID], input="n\n")

    assert result.exit_code != 0
    assert not route.called


def test_policies_delete_json(invoke, mock_api):
    mock_api.delete(f"{_BASE}/{_ID}").respond(204)
    result = invoke(["agentic", "policies", "delete", _ID, "--yes", "--json"])

    assert json.loads(result.output) == {"id": _ID, "deleted": True}
