"""Tests for the agentic platform connection commands.

`ac agentic connections` reads the provider accounts of an organization, starts
the link flow for a new account, and revokes an account. The API never answers
the external account id or a credential, so the CLI never prints one.
"""

import json

import pytest

_BASE = "/api/v1/agentic/connections"
_CONNECTION_ID = "33333333-3333-4333-8333-333333333333"

SAMPLE_CONNECTION = {
    "id": _CONNECTION_ID,
    "provider": "linkedin",
    "display_name": "Sarah Chen",
    "owner_user_id": "44444444-4444-4444-8444-444444444444",
    "status": "connected",
    "created_at": "2026-09-20T10:00:00Z",
    "updated_at": "2026-09-20T10:00:00Z",
    "revoked_at": None,
    "held_until": None,
    "hold_reason": None,
    "send_window_start": None,
    "send_window_end": None,
}

HELD_CONNECTION = {
    **SAMPLE_CONNECTION,
    "held_until": "2026-10-11T00:00:00Z",
    "hold_reason": "too_many_requests",
    "send_window_start": "06:00:00",
    "send_window_end": "22:30:00",
}

REVOKED_CONNECTION = {
    **SAMPLE_CONNECTION,
    "status": "revoked",
    "revoked_at": "2026-09-21T10:00:00Z",
}

SAMPLE_PAGE = {"items": [SAMPLE_CONNECTION]}

LINK_URL = "https://auth.example.test/hosted/abc"


# --- list ------------------------------------------------------------------


def test_connections_list(invoke, mock_api, table_column):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "connections", "list"])

    assert result.exit_code == 0
    assert table_column(result.output, 1) == "linkedin"
    assert table_column(result.output, 2) == "SarahChen"
    assert table_column(result.output, 3) == "connected"
    assert table_column(result.output, 4) == "44444444-4444-4444-8444-444444444444"
    assert "provider" not in route.calls[0].request.url.params


def test_connections_list_shows_the_hold_and_the_window(invoke, mock_api, table_column):
    mock_api.get(_BASE).respond(200, json={"items": [HELD_CONNECTION]})
    result = invoke(["agentic", "connections", "list"])

    assert result.exit_code == 0
    assert table_column(result.output, 5) == "2026-10-11T00:00:00Z"
    assert table_column(result.output, 6) == "06:00to22:30"


def test_connections_list_shows_the_default_window(invoke, mock_api, table_column):
    mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "connections", "list"])

    assert result.exit_code == 0
    assert table_column(result.output, 5) == ""
    assert table_column(result.output, 6) == "07:00to20:00(default)"


def test_connections_list_sends_the_provider_it_was_given(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    invoke(["agentic", "connections", "list", "--provider", "linkedin"])

    assert route.calls[0].request.url.params["provider"] == "linkedin"


def test_connections_list_reports_an_empty_organization(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json={"items": []})
    result = invoke(["agentic", "connections", "list"])

    assert result.exit_code == 0
    assert "no connections" in result.output.lower()


def test_connections_list_json(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "connections", "list", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == SAMPLE_PAGE


def test_connections_list_refusal_json(invoke, mock_api):
    mock_api.get(_BASE).respond(403, json={"detail": "not a member"})
    result = invoke(["agentic", "connections", "list", "--json"])

    assert result.exit_code == 4
    assert json.loads(result.output) == {
        "error": True,
        "status_code": 403,
        "detail": "not a member",
    }


# --- providers -------------------------------------------------------------

SAMPLE_PROVIDERS = {"items": [{"provider": "linkedin", "available": False}]}


def test_connections_providers(invoke, mock_api, table_column):
    route = mock_api.get(f"{_BASE}/providers").respond(200, json=SAMPLE_PROVIDERS)
    result = invoke(["agentic", "connections", "providers"])

    assert result.exit_code == 0
    assert route.called
    assert table_column(result.output, 0) == "linkedin"
    assert table_column(result.output, 1) == "False"


def test_connections_providers_json(invoke, mock_api):
    mock_api.get(f"{_BASE}/providers").respond(200, json=SAMPLE_PROVIDERS)
    result = invoke(["agentic", "connections", "providers", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == SAMPLE_PROVIDERS


def test_connections_providers_refusal(invoke, mock_api):
    """An actor that names no person answers 403, which exits 4."""
    mock_api.get(f"{_BASE}/providers").respond(
        403, json={"detail": "a connection belongs to a person"}
    )
    result = invoke(["agentic", "connections", "providers", "--json"])

    assert result.exit_code == 4
    assert json.loads(result.output) == {
        "error": True,
        "status_code": 403,
        "detail": "a connection belongs to a person",
    }


# --- get -------------------------------------------------------------------


def test_connections_get(invoke, mock_api):
    route = mock_api.get(f"{_BASE}/{_CONNECTION_ID}").respond(200, json=SAMPLE_CONNECTION)
    result = invoke(["agentic", "connections", "get", _CONNECTION_ID])

    assert result.exit_code == 0
    assert route.called
    assert "Sarah Chen" in result.output
    assert "44444444-4444-4444-8444-444444444444" in result.output
    assert "2026-09-20T10:00:00Z" in result.output


def test_connections_get_shows_the_hold_and_the_window(invoke, mock_api):
    mock_api.get(f"{_BASE}/{_CONNECTION_ID}").respond(200, json=HELD_CONNECTION)
    result = invoke(["agentic", "connections", "get", _CONNECTION_ID])

    assert result.exit_code == 0
    assert "2026-10-11T00:00:00Z" in result.output
    assert "too_many_requests" in result.output
    assert "06:00 to 22:30" in result.output


def test_connections_get_json(invoke, mock_api):
    mock_api.get(f"{_BASE}/{_CONNECTION_ID}").respond(200, json=SAMPLE_CONNECTION)
    result = invoke(["agentic", "connections", "get", _CONNECTION_ID, "--json"])

    assert json.loads(result.output) == SAMPLE_CONNECTION


def test_connections_get_not_found(invoke, mock_api):
    """A connection of another organization answers 404, which exits 3."""
    mock_api.get(f"{_BASE}/{_CONNECTION_ID}").respond(404, json={"detail": "not found"})
    result = invoke(["agentic", "connections", "get", _CONNECTION_ID])

    assert result.exit_code == 3


# --- link ------------------------------------------------------------------


def test_connections_link_prints_the_url(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/link").respond(200, json={"url": LINK_URL})
    result = invoke(["agentic", "connections", "link", "--provider", "linkedin"])

    assert result.exit_code == 0
    assert LINK_URL in result.output
    assert json.loads(route.calls[0].request.content) == {"provider": "linkedin"}


def test_connections_link_needs_a_provider(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/link").respond(200, json={"url": LINK_URL})
    result = invoke(["agentic", "connections", "link"])

    assert result.exit_code != 0
    assert not route.called


def test_connections_link_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/link").respond(200, json={"url": LINK_URL})
    result = invoke(["agentic", "connections", "link", "--provider", "linkedin", "--json"])

    assert json.loads(result.output) == {"url": LINK_URL}


def test_connections_link_reports_an_unavailable_provider(invoke, mock_api):
    """A 503 means the provider has no link flow on this deploy."""
    mock_api.post(f"{_BASE}/link").respond(503, json={"detail": "provider unavailable"})
    result = invoke(["agentic", "connections", "link", "--provider", "linkedin"])

    assert result.exit_code == 1
    assert "not available on this deploy" in result.output
    assert "linkedin" in result.output


def test_connections_link_reports_an_unavailable_provider_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/link").respond(503, json={"detail": "provider unavailable"})
    result = invoke(["agentic", "connections", "link", "--provider", "linkedin", "--json"])

    assert result.exit_code == 1
    error = json.loads(result.output)
    assert error["error"] is True
    assert error["status_code"] == 503
    assert "not available on this deploy" in error["detail"]


def test_connections_link_other_errors_keep_their_exit_code(invoke, mock_api):
    """Only a 503 takes the provider message. A refusal keeps exit 4."""
    mock_api.post(f"{_BASE}/link").respond(403, json={"detail": "admin only"})
    result = invoke(["agentic", "connections", "link", "--provider", "linkedin"])

    assert result.exit_code == 4
    assert "admin only" in result.output


# --- reconnect -------------------------------------------------------------


def test_connections_reconnect_prints_the_url(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_CONNECTION_ID}/reconnect").respond(
        200, json={"url": LINK_URL}
    )
    result = invoke(["agentic", "connections", "reconnect", _CONNECTION_ID])

    assert result.exit_code == 0
    assert route.called
    assert LINK_URL in result.output


def test_connections_reconnect_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_CONNECTION_ID}/reconnect").respond(200, json={"url": LINK_URL})
    result = invoke(["agentic", "connections", "reconnect", _CONNECTION_ID, "--json"])

    assert json.loads(result.output) == {"url": LINK_URL}


@pytest.mark.parametrize(
    ("status", "exit_code"),
    [(404, 3), (409, 5)],
)
def test_connections_reconnect_errors(invoke, mock_api, status, exit_code):
    """An unknown connection exits 3. A revoked connection answers 409 and exits 5."""
    mock_api.post(f"{_BASE}/{_CONNECTION_ID}/reconnect").respond(status, json={"detail": "refused"})
    result = invoke(["agentic", "connections", "reconnect", _CONNECTION_ID])

    assert result.exit_code == exit_code


def test_connections_reconnect_reports_an_unavailable_provider(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_CONNECTION_ID}/reconnect").respond(
        503, json={"detail": "provider unavailable"}
    )
    result = invoke(["agentic", "connections", "reconnect", _CONNECTION_ID])

    assert result.exit_code == 1
    assert "not available on this deploy" in result.output


# --- revoke ----------------------------------------------------------------


def test_connections_revoke_with_yes(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_CONNECTION_ID}/revoke").respond(200, json=REVOKED_CONNECTION)
    result = invoke(["agentic", "connections", "revoke", _CONNECTION_ID, "--yes"])

    assert result.exit_code == 0
    assert route.called
    assert "revoked" in result.output.lower()


def test_connections_revoke_asks_before_it_revokes(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_CONNECTION_ID}/revoke").respond(200, json=REVOKED_CONNECTION)
    result = invoke(["agentic", "connections", "revoke", _CONNECTION_ID], input="n\n")

    assert result.exit_code != 0
    assert not route.called


def test_connections_revoke_confirmed_at_the_prompt(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_CONNECTION_ID}/revoke").respond(200, json=REVOKED_CONNECTION)
    result = invoke(["agentic", "connections", "revoke", _CONNECTION_ID], input="y\n")

    assert result.exit_code == 0
    assert route.called


def test_connections_revoke_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_CONNECTION_ID}/revoke").respond(200, json=REVOKED_CONNECTION)
    result = invoke(["agentic", "connections", "revoke", _CONNECTION_ID, "--yes", "--json"])

    assert json.loads(result.output) == REVOKED_CONNECTION


def test_connections_revoke_not_found(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_CONNECTION_ID}/revoke").respond(404, json={"detail": "not found"})
    result = invoke(["agentic", "connections", "revoke", _CONNECTION_ID, "--yes"])

    assert result.exit_code == 3


# --- set-window --------------------------------------------------------------


def _set_window(*extra: str) -> list[str]:
    return ["agentic", "connections", "set-window", _CONNECTION_ID, *extra]


def test_connections_set_window(invoke, mock_api):
    route = mock_api.patch(f"{_BASE}/{_CONNECTION_ID}").respond(200, json=HELD_CONNECTION)
    result = invoke(_set_window("--start", "06:00", "--end", "22:30"))

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "send_window_start": "06:00",
        "send_window_end": "22:30",
    }
    assert "06:00 to 22:30" in result.output


def test_connections_set_window_clear_sends_null(invoke, mock_api):
    route = mock_api.patch(f"{_BASE}/{_CONNECTION_ID}").respond(200, json=SAMPLE_CONNECTION)
    result = invoke(_set_window("--clear"))

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "send_window_start": None,
        "send_window_end": None,
    }
    assert "07:00 to 20:00 (default)" in result.output


def test_connections_set_window_json(invoke, mock_api):
    mock_api.patch(f"{_BASE}/{_CONNECTION_ID}").respond(200, json=HELD_CONNECTION)
    result = invoke(_set_window("--start", "06:00", "--end", "22:30", "--json"))

    assert result.exit_code == 0
    assert json.loads(result.output) == HELD_CONNECTION


@pytest.mark.parametrize(
    "extra",
    [
        (),
        ("--start", "06:00"),
        ("--end", "22:00"),
        ("--start", "06:00", "--end", "22:00", "--clear"),
    ],
)
def test_connections_set_window_needs_both_ends_or_clear(invoke, mock_api, extra):
    route = mock_api.patch(f"{_BASE}/{_CONNECTION_ID}").respond(200, json=HELD_CONNECTION)
    result = invoke(_set_window(*extra))

    assert result.exit_code == 2
    assert not route.called


def test_connections_set_window_member_refusal_json(invoke, mock_api):
    """Only an admin widens a window. A member answers 403 and exits 4."""
    mock_api.patch(f"{_BASE}/{_CONNECTION_ID}").respond(
        403, json={"detail": "only an organization admin changes a connection"}
    )
    result = invoke(_set_window("--start", "06:00", "--end", "22:00", "--json"))

    assert result.exit_code == 4
    assert json.loads(result.output) == {
        "error": True,
        "status_code": 403,
        "detail": "only an organization admin changes a connection",
    }


def test_connections_set_window_prints_the_api_detail_on_422(invoke, mock_api):
    """A window whose start is not before its end answers 422 and exits 2."""
    mock_api.patch(f"{_BASE}/{_CONNECTION_ID}").respond(
        422, json={"detail": "the send window must start before it ends"}
    )
    result = invoke(_set_window("--start", "22:00", "--end", "06:00"))

    assert result.exit_code == 2
    assert "must start before it ends" in result.output


def test_connections_set_window_not_found(invoke, mock_api):
    mock_api.patch(f"{_BASE}/{_CONNECTION_ID}").respond(404, json={"detail": "not found"})
    result = invoke(_set_window("--clear"))

    assert result.exit_code == 3
