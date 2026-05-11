"""Tests for shared helpers: _build_body, _resolve_entity, _require_id, _get_org_id."""

import json

from tests.conftest import API_BASE, WHOAMI_RESPONSE


# -- _build_body ---------------------------------------------------------------


def test_build_body_filters_none(invoke, mock_api):
    """_build_body excludes None values from the body."""
    from ac_cli.commands._helpers import _build_body

    body = _build_body(name="Acme", website=None, industry="Tech")
    assert body == {"name": "Acme", "industry": "Tech"}


def test_build_body_splits_tags(invoke, mock_api):
    """_build_body splits comma-separated tag strings into lists."""
    from ac_cli.commands._helpers import _build_body

    body = _build_body(tags="a, b , c")
    assert body == {"tags": ["a", "b", "c"]}


def test_build_body_empty(invoke, mock_api):
    """_build_body with all None returns empty dict."""
    from ac_cli.commands._helpers import _build_body

    body = _build_body(name=None, website=None)
    assert body == {}


def test_build_body_tags_list_passthrough(invoke, mock_api):
    """_build_body passes non-string tags through unchanged."""
    from ac_cli.commands._helpers import _build_body

    body = _build_body(tags=["a", "b"])
    assert body == {"tags": ["a", "b"]}


# -- _resolve_entity -----------------------------------------------------------


def test_resolve_entity_with_explicit_id(invoke, mock_api):
    """_resolve_entity returns the explicit ID when provided."""
    from ac_cli.commands._helpers import _resolve_entity

    result = _resolve_entity(
        entity_id="abc-123",
        entity_name=None,
        search_path="/api/v1/crm/companies",
    )
    assert result == "abc-123"


def test_resolve_entity_neither_id_nor_name(invoke, mock_api):
    """_resolve_entity returns None when neither ID nor name is given."""
    from ac_cli.commands._helpers import _resolve_entity

    result = _resolve_entity(
        entity_id=None,
        entity_name=None,
        search_path="/api/v1/crm/companies",
    )
    assert result is None


def test_resolve_entity_single_match(invoke, mock_api):
    """_resolve_entity returns the ID when exactly one match is found."""
    from ac_cli.commands._helpers import _resolve_entity

    mock_api.get("/api/v1/crm/companies").respond(
        200, json={"data": [{"id": "co-1", "name": "Acme Corp"}]}
    )
    result = _resolve_entity(
        entity_id=None,
        entity_name="Acme",
        search_path="/api/v1/crm/companies",
        label="company",
    )
    assert result == "co-1"


def test_resolve_entity_no_matches_exits(invoke, mock_api):
    """_resolve_entity exits with code 3 when no matches found."""
    mock_api.get("/api/v1/crm/companies").respond(200, json={"data": []})
    result = invoke(["crm", "companies", "create", "--name", "Ghost", "--company-name", "NoExist"])
    # The command will fail because _resolve_entity exits early
    assert result.exit_code != 0


def test_resolve_entity_multiple_matches_exact(invoke, mock_api):
    """_resolve_entity picks exact match when multiple results returned."""
    from ac_cli.commands._helpers import _resolve_entity

    mock_api.get("/api/v1/crm/companies").respond(
        200,
        json={
            "data": [
                {"id": "co-1", "name": "Acme Corp"},
                {"id": "co-2", "name": "Acme"},
            ]
        },
    )
    result = _resolve_entity(
        entity_id=None,
        entity_name="Acme",
        search_path="/api/v1/crm/companies",
        label="company",
    )
    assert result == "co-2"


# -- _require_id ---------------------------------------------------------------


def test_require_id_with_value(invoke, mock_api):
    """_require_id returns the value when it's truthy."""
    from ac_cli.commands._helpers import _require_id

    assert _require_id("abc-123") == "abc-123"


# -- _get_org_id ---------------------------------------------------------------


def test_get_org_id(invoke, mock_api):
    """_get_org_id fetches organization_id from /whoami."""
    from ac_cli.commands._helpers import _get_org_id

    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    org_id = _get_org_id()
    assert org_id == "org-456"


def test_get_org_id_used_in_create(invoke, mock_api):
    """Create commands use _get_org_id to set organization_id."""
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/companies").respond(
        201, json={"id": "co-new", "name": "NewCo"}
    )
    result = invoke(["crm", "companies", "create", "--name", "NewCo", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "co-new"
