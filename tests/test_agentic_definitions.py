"""Tests for the agentic platform definition commands.

`ac agentic definitions` drives the ten routes under
`/api/v1/agentic/definitions`. Staging serves none of them until the cutover,
so the audit for this group runs against a branch API.
"""

import json

DEFINITION_ID = "11111111-1111-4111-8111-111111111111"
TOKEN = "2026-08-23T10:00:00.123456+00:00"

SAMPLE = {
    "id": DEFINITION_ID,
    "organization_id": "99999999-9999-4999-8999-999999999999",
    "kind": "agent",
    "name": "researcher",
    "origin": "custom",
    "source_definition_id": None,
    "state": "draft",
    "has_unpublished_changes": False,
    "created_at": "2026-08-23T10:00:00Z",
    "published_at": None,
    "updated_at": TOKEN,
    "draft_config": {"instructions": "Answer."},
    "published_config": None,
    "referenced_ids": [],
    "capability_binding": None,
    "validation": None,
    "capability_id": None,
    "capability_active": False,
    "platform_managed": False,
    "references": [],
    "used_by": [],
}

BINDING = {
    "capability_id": "company.search",
    "contract_version": 2,
    "name": "Company Search",
    "description": "Finds companies and returns selectable references.",
    "input_schema": {"type": "object", "additionalProperties": False, "properties": {}},
    "output_schema": {"type": "object", "additionalProperties": False, "properties": {}},
    "platform_managed": True,
}

BOUND = {
    **SAMPLE,
    "kind": "workflow",
    "state": "active",
    "capability_binding": BINDING,
    "capability_id": "company.search",
    "capability_active": True,
    "platform_managed": True,
}

CHILD_ID = "22222222-2222-4222-8222-222222222222"
PARENT_ID = "33333333-3333-4333-8333-333333333333"

LINKED = {
    **SAMPLE,
    "kind": "workflow",
    "referenced_ids": [CHILD_ID],
    "references": [
        {
            "id": CHILD_ID,
            "kind": "agent",
            "name": "finder",
            "state": "active",
            "origin": "custom",
            "capability_id": None,
            "capability_active": False,
        }
    ],
    "used_by": [
        {
            "id": PARENT_ID,
            "kind": "workflow",
            "name": "digest",
            "state": "disabled",
            "origin": "custom",
            "capability_id": "signals.search",
            "capability_active": False,
        }
    ],
}

BASE = "/api/v1/agentic/definitions"


# --- list ------------------------------------------------------------------


def test_definitions_list(invoke, mock_api):
    mock_api.get(BASE).respond(200, json={"items": [SAMPLE], "next_cursor": None})
    result = invoke(["agentic", "definitions", "list"])

    assert result.exit_code == 0
    assert "researcher" in result.output


def test_definitions_list_forwards_every_filter(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json={"items": [], "next_cursor": None})
    invoke(
        [
            "agentic",
            "definitions",
            "list",
            "--kind",
            "workflow",
            "--origin",
            "platform",
            "--state",
            "active",
            "--cursor",
            "abc",
        ]
    )

    params = route.calls[0].request.url.params
    assert params["kind"] == "workflow"
    assert params["origin"] == "platform"
    assert params["state"] == "active"
    assert params["cursor"] == "abc"


def test_definitions_list_shows_the_capability_link(invoke, mock_api):
    """A row names the capability it binds."""
    mock_api.get(BASE).respond(200, json={"items": [BOUND], "next_cursor": None})

    result = invoke(["agentic", "definitions", "list"])

    assert result.exit_code == 0
    assert "Capabil" in result.output
    assert "company" in result.output


def test_definitions_list_json_carries_the_capability_link(invoke, mock_api):
    mock_api.get(BASE).respond(200, json={"items": [BOUND], "next_cursor": None})

    result = invoke(["agentic", "definitions", "list", "--json"])

    row = json.loads(result.output)["items"][0]
    assert row["capability_id"] == "company.search"
    assert row["capability_active"] is True
    assert row["platform_managed"] is True


def test_definitions_list_json(invoke, mock_api):
    mock_api.get(BASE).respond(200, json={"items": [SAMPLE], "next_cursor": "next"})
    result = invoke(["agentic", "definitions", "list", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["next_cursor"] == "next"


# --- create and read -------------------------------------------------------


def test_definitions_create(invoke, mock_api):
    route = mock_api.post(BASE).respond(201, json=SAMPLE)
    result = invoke(
        [
            "agentic",
            "definitions",
            "create",
            "--kind",
            "agent",
            "--name",
            "researcher",
            "--config",
            '{"instructions": "Answer."}',
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "kind": "agent",
        "name": "researcher",
        "config": {"instructions": "Answer."},
    }


def test_definitions_create_refuses_config_that_is_not_an_object(invoke, mock_api):
    result = invoke(
        ["agentic", "definitions", "create", "--kind", "agent", "--name", "x", "--config", "[1, 2]"]
    )

    assert result.exit_code == 1


def test_definitions_get(invoke, mock_api):
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(200, json=SAMPLE)
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID])

    assert result.exit_code == 0
    assert "researcher" in result.output


def test_definitions_get_shows_the_capability_contract(invoke, mock_api):
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(200, json=BOUND)
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID])

    assert result.exit_code == 0
    assert "Capability: company.search" in result.output
    assert "Contract version: 2" in result.output
    assert "--json" in result.output


def test_definitions_get_shows_the_capability_flags(invoke, mock_api):
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(200, json=BOUND)
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID])

    assert result.exit_code == 0
    assert "Active executor: True" in result.output
    assert "Platform managed: True" in result.output


def test_definitions_get_shows_the_links_in_both_directions(invoke, mock_api):
    """The detail names what the row uses and what uses the row."""
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(200, json=LINKED)
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID])

    assert result.exit_code == 0
    assert "References (1)" in result.output
    assert "finder" in result.output
    assert "Used by (1)" in result.output
    assert "digest" in result.output
    assert "signals.search" in result.output


def test_definitions_get_with_no_links_prints_no_link_table(invoke, mock_api):
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(200, json=SAMPLE)
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID])

    assert result.exit_code == 0
    assert "References" not in result.output
    assert "Used by" not in result.output


def test_definitions_get_json_carries_the_links(invoke, mock_api):
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(200, json=LINKED)
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID, "--json"])

    body = json.loads(result.output)
    assert body["references"] == LINKED["references"]
    assert body["used_by"] == LINKED["used_by"]


def test_definitions_get_of_an_unbound_definition_names_no_capability(invoke, mock_api):
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(200, json=SAMPLE)
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID])

    assert result.exit_code == 0
    assert "company.search" not in result.output
    assert "--json" not in result.output


def test_definitions_get_json_carries_both_schemas(invoke, mock_api):
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(200, json=BOUND)
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID, "--json"])

    assert result.exit_code == 0
    binding = json.loads(result.output)["capability_binding"]
    assert binding["input_schema"] == BINDING["input_schema"]
    assert binding["output_schema"] == BINDING["output_schema"]


def test_definitions_get_of_another_tenant_is_not_found(invoke, mock_api):
    mock_api.get(f"{BASE}/{DEFINITION_ID}").respond(404, json={"detail": "definition not found"})
    result = invoke(["agentic", "definitions", "get", DEFINITION_ID])

    assert result.exit_code != 0


# --- the draft save --------------------------------------------------------


def test_definitions_patch_sends_the_token_and_the_patch(invoke, mock_api):
    route = mock_api.patch(f"{BASE}/{DEFINITION_ID}/draft").respond(200, json=SAMPLE)
    invoke(
        [
            "agentic",
            "definitions",
            "patch",
            DEFINITION_ID,
            "--expected-updated-at",
            TOKEN,
            "--patch",
            '{"tool_ids": ["crm.get_company"]}',
        ]
    )

    assert json.loads(route.calls[0].request.content) == {
        "expected_updated_at": TOKEN,
        "patch": {"tool_ids": ["crm.get_company"]},
    }


def test_definitions_patch_reports_what_validation_found(invoke, mock_api):
    answer = {
        **SAMPLE,
        "validation": {
            "ok": False,
            "issues": [{"code": "missing_model", "message": "name a model", "path": None}],
        },
    }
    mock_api.patch(f"{BASE}/{DEFINITION_ID}/draft").respond(200, json=answer)
    result = invoke(
        [
            "agentic",
            "definitions",
            "patch",
            DEFINITION_ID,
            "--expected-updated-at",
            TOKEN,
            "--patch",
            '{"a": 1}',
        ]
    )

    assert result.exit_code == 0
    assert "missing_model" in result.output


def test_definitions_patch_reports_a_stale_token(invoke, mock_api):
    mock_api.patch(f"{BASE}/{DEFINITION_ID}/draft").respond(
        409, json={"detail": "the definition moved on; reload and retry"}
    )
    result = invoke(
        [
            "agentic",
            "definitions",
            "patch",
            DEFINITION_ID,
            "--expected-updated-at",
            TOKEN,
            "--patch",
            '{"a": 1}',
        ]
    )

    assert result.exit_code != 0


# --- validate and publish --------------------------------------------------


def test_definitions_validate(invoke, mock_api):
    mock_api.post(f"{BASE}/{DEFINITION_ID}/validate").respond(
        200, json={**SAMPLE, "validation": {"ok": True, "issues": []}}
    )
    result = invoke(["agentic", "definitions", "validate", DEFINITION_ID])

    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_definitions_publish(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DEFINITION_ID}/publish").respond(
        200, json={**SAMPLE, "state": "active"}
    )
    result = invoke(
        [
            "agentic",
            "definitions",
            "publish",
            DEFINITION_ID,
            "--expected-updated-at",
            TOKEN,
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {"expected_updated_at": TOKEN}


def test_definitions_publish_refused_by_a_referrer(invoke, mock_api):
    mock_api.post(f"{BASE}/{DEFINITION_ID}/publish").respond(
        422,
        json={
            "detail": {
                "outcome": "invalid",
                "reason": "a definition that references this one would break",
                "issues": [
                    {
                        "code": "referrer_regression",
                        "message": "digest would break",
                        "path": None,
                    }
                ],
            }
        },
    )
    result = invoke(
        [
            "agentic",
            "definitions",
            "publish",
            DEFINITION_ID,
            "--expected-updated-at",
            TOKEN,
        ]
    )

    assert result.exit_code != 0


# --- disable, enable, fork -------------------------------------------------


def test_definitions_disable(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DEFINITION_ID}/disable").respond(
        200, json={**SAMPLE, "state": "disabled"}
    )
    result = invoke(["agentic", "definitions", "disable", DEFINITION_ID, "--yes"])

    assert result.exit_code == 0
    assert route.calls[0].request.content == b""


def test_definitions_disable_refused_while_in_use(invoke, mock_api):
    mock_api.post(f"{BASE}/{DEFINITION_ID}/disable").respond(
        409, json={"detail": "digest still references this definition"}
    )
    result = invoke(["agentic", "definitions", "disable", DEFINITION_ID, "--yes"])

    assert result.exit_code != 0


def test_definitions_enable(invoke, mock_api):
    mock_api.post(f"{BASE}/{DEFINITION_ID}/enable").respond(200, json={**SAMPLE, "state": "active"})
    result = invoke(["agentic", "definitions", "enable", DEFINITION_ID])

    assert result.exit_code == 0


def test_definitions_fork(invoke, mock_api):
    mock_api.post(f"{BASE}/{DEFINITION_ID}/fork").respond(200, json=SAMPLE)
    result = invoke(["agentic", "definitions", "fork", DEFINITION_ID])

    assert result.exit_code == 0
    assert DEFINITION_ID in result.output


# --- delete ----------------------------------------------------------------


def test_definitions_delete_asks_before_it_removes(invoke, mock_api):
    route = mock_api.delete(f"{BASE}/{DEFINITION_ID}").respond(204)
    result = invoke(["agentic", "definitions", "delete", DEFINITION_ID], input="n\n")

    assert result.exit_code != 0
    assert route.calls == []


def test_definitions_delete_with_yes_skips_the_prompt(invoke, mock_api):
    route = mock_api.delete(f"{BASE}/{DEFINITION_ID}").respond(204)
    result = invoke(["agentic", "definitions", "delete", DEFINITION_ID, "--yes"])

    assert result.exit_code == 0
    assert len(route.calls) == 1


def test_definitions_delete_of_a_published_row_is_refused(invoke, mock_api):
    mock_api.delete(f"{BASE}/{DEFINITION_ID}").respond(
        409, json={"detail": "this definition is active; disable it instead"}
    )
    result = invoke(["agentic", "definitions", "delete", DEFINITION_ID, "--yes"])

    assert result.exit_code != 0


def test_definitions_create_renders_a_close_tag_in_the_name(invoke, mock_api):
    """The author writes the name, so a bracket must not break the line."""
    mock_api.post(BASE).respond(
        201,
        json={"id": "def-1", "name": "Acme [/beta] agent", "kind": "workflow", "state": "draft"},
    )
    result = invoke(
        [
            "agentic",
            "definitions",
            "create",
            "--kind",
            "agent",
            "--name",
            "Acme [/beta] agent",
            "--config",
            '{"instructions": "Answer."}',
        ]
    )

    assert result.exit_code == 0
    assert "[/beta]" in result.output


def test_definitions_validate_renders_a_close_tag_in_an_issue_path(invoke, mock_api):
    """The path names a JSON key the author typed, so it can hold a bracket."""
    mock_api.post(f"{BASE}/def-1/validate").respond(
        200,
        json={
            "validation": {
                "ok": False,
                "issues": [
                    {"code": "unknown_field", "path": "cfg[/beta]", "message": "not a field"}
                ],
            }
        },
    )
    result = invoke(["agentic", "definitions", "validate", "def-1"])

    assert result.exit_code == 0
    assert "cfg[/beta]" in result.output
