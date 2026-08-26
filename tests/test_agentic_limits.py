"""Tests for the agentic platform limit commands.

`ac agentic limits` reads and writes what one organization may spend on AI in a
day. The table holds cost alone: rate and concurrency live in Inngest.
"""

import json

_BASE = "/api/v1/agentic/limits"

SAMPLE_LIMIT = {
    "kind": "daily_cost",
    "value_cents": 5000,
    "updated_at": "2026-08-25T10:00:00.123456+00:00",
}

SAMPLE_PAGE = {"items": [SAMPLE_LIMIT]}

REMOVED_LIMIT = {"kind": "daily_cost", "value_cents": None, "updated_at": None}


# --- get -------------------------------------------------------------------


def test_limits_get(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "limits", "get"])

    assert result.exit_code == 0
    assert "daily_cost" in result.output
    assert route.called


def test_limits_get_reports_no_cap(invoke, mock_api):
    """An organization that set no ceiling reads as no cap, and not as an
    error."""
    mock_api.get(_BASE).respond(200, json={"items": []})
    result = invoke(["agentic", "limits", "get"])

    assert result.exit_code == 0
    assert "no cap" in result.output.lower()


def test_limits_get_json(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "limits", "get", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == SAMPLE_PAGE


# --- set -------------------------------------------------------------------


def test_limits_set(invoke, mock_api):
    route = mock_api.put(_BASE).respond(200, json={**SAMPLE_LIMIT, "value_cents": 9000})
    result = invoke(["agentic", "limits", "set", "--value-cents", "9000"])

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "kind": "daily_cost",
        "value_cents": 9000,
    }


def test_limits_set_sends_the_kind_it_was_given(invoke, mock_api):
    route = mock_api.put(_BASE).respond(200, json=SAMPLE_LIMIT)
    invoke(["agentic", "limits", "set", "--kind", "daily_cost", "--value-cents", "5000"])

    assert json.loads(route.calls[0].request.content)["kind"] == "daily_cost"


def test_limits_set_accepts_zero(invoke, mock_api):
    """Zero is a ceiling somebody set, and it stops every run."""
    route = mock_api.put(_BASE).respond(200, json={**SAMPLE_LIMIT, "value_cents": 0})
    result = invoke(["agentic", "limits", "set", "--value-cents", "0"])

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content)["value_cents"] == 0


def test_limits_set_json(invoke, mock_api):
    mock_api.put(_BASE).respond(200, json=SAMPLE_LIMIT)
    result = invoke(["agentic", "limits", "set", "--value-cents", "5000", "--json"])

    assert json.loads(result.output) == SAMPLE_LIMIT


def test_limits_set_reports_a_refusal(invoke, mock_api):
    """A `403` exits 4, which is the code every authorization refusal takes."""
    mock_api.put(_BASE).respond(403, json={"detail": "only an organization admin writes a policy"})
    result = invoke(["agentic", "limits", "set", "--value-cents", "5000"])

    assert result.exit_code == 4


# --- clear -----------------------------------------------------------------


def test_limits_clear_sends_a_null_value(invoke, mock_api):
    """A null value removes the row, which is the one path back to no cap."""
    route = mock_api.put(_BASE).respond(200, json=REMOVED_LIMIT)
    result = invoke(["agentic", "limits", "clear", "--yes"])

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "kind": "daily_cost",
        "value_cents": None,
    }


def test_limits_clear_asks_before_it_removes(invoke, mock_api):
    """It lifts a spending guard, so it confirms like every destructive
    command."""
    route = mock_api.put(_BASE).respond(200, json=REMOVED_LIMIT)
    result = invoke(["agentic", "limits", "clear"], input="n\n")

    assert result.exit_code != 0
    assert not route.called


def test_limits_clear_json(invoke, mock_api):
    mock_api.put(_BASE).respond(200, json=REMOVED_LIMIT)
    result = invoke(["agentic", "limits", "clear", "--yes", "--json"])

    assert json.loads(result.output) == REMOVED_LIMIT
