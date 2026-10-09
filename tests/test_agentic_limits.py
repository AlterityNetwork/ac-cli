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


# --- budgets ---------------------------------------------------------------

_BUDGETS = "/api/v1/agentic/limits/action-budgets"
_CONNECTION_ID = "33333333-3333-4333-8333-333333333333"

SAMPLE_BUDGETS = {
    "items": [
        {
            "connection_id": _CONNECTION_ID,
            "provider": "linkedin",
            "display_name": "Sarah Chen",
            "status": "connected",
            "half_rate_until": "2026-10-04T10:00:00Z",
            "budgets": [
                {
                    "budget_class": "linkedin.invitations",
                    "time_window": "day",
                    "platform_default": 20,
                    "cap": 10,
                    "override": None,
                    "used": 3,
                },
                {
                    "budget_class": "linkedin.invitations",
                    "time_window": "week",
                    "platform_default": 100,
                    "cap": 40,
                    "override": 40,
                    "used": 12,
                },
            ],
        }
    ]
}

SAMPLE_LINE = {
    "budget_class": "linkedin.invitations",
    "time_window": "day",
    "platform_default": 20,
    "cap": 15,
    "override": 15,
    "used": 3,
}


def test_limits_budgets(invoke, mock_api):
    route = mock_api.get(_BUDGETS).respond(200, json=SAMPLE_BUDGETS)
    result = invoke(["agentic", "limits", "budgets"])

    assert result.exit_code == 0
    assert route.called
    assert "Sarah Chen" in result.output
    assert "linkedin.invitations" in result.output
    assert "week" in result.output
    assert "2026-10-04T10:00:00Z" in result.output


def test_limits_budgets_reports_no_connections(invoke, mock_api):
    mock_api.get(_BUDGETS).respond(200, json={"items": []})
    result = invoke(["agentic", "limits", "budgets"])

    assert result.exit_code == 0
    assert "no connections" in result.output.lower()


def test_limits_budgets_json(invoke, mock_api):
    mock_api.get(_BUDGETS).respond(200, json=SAMPLE_BUDGETS)
    result = invoke(["agentic", "limits", "budgets", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == SAMPLE_BUDGETS


# --- set-budget ------------------------------------------------------------


def _set_budget(*extra: str) -> list[str]:
    return [
        "agentic",
        "limits",
        "set-budget",
        "--connection",
        _CONNECTION_ID,
        "--class",
        "linkedin.invitations",
        "--window",
        "day",
        *extra,
    ]


def test_limits_set_budget(invoke, mock_api):
    route = mock_api.put(_BUDGETS).respond(200, json=SAMPLE_LINE)
    result = invoke(_set_budget("--max", "15"))

    assert result.exit_code == 0
    assert "linkedin.invitations" in result.output
    assert json.loads(route.calls[0].request.content) == {
        "connection_id": _CONNECTION_ID,
        "budget_class": "linkedin.invitations",
        "time_window": "day",
        "max_count": 15,
    }


def test_limits_set_budget_accepts_zero(invoke, mock_api):
    """Zero is an override somebody set. It is not the same as no override."""
    route = mock_api.put(_BUDGETS).respond(200, json={**SAMPLE_LINE, "cap": 0, "override": 0})
    result = invoke(_set_budget("--max", "0"))

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content)["max_count"] == 0


def test_limits_set_budget_clear_sends_null(invoke, mock_api):
    route = mock_api.put(_BUDGETS).respond(200, json={**SAMPLE_LINE, "override": None})
    result = invoke(_set_budget("--clear"))

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content)["max_count"] is None


def test_limits_set_budget_json(invoke, mock_api):
    mock_api.put(_BUDGETS).respond(200, json=SAMPLE_LINE)
    result = invoke(_set_budget("--max", "15", "--json"))

    assert json.loads(result.output) == SAMPLE_LINE


def test_limits_set_budget_needs_max_or_clear(invoke, mock_api):
    route = mock_api.put(_BUDGETS).respond(200, json=SAMPLE_LINE)
    result = invoke(_set_budget())

    assert result.exit_code == 2
    assert not route.called


def test_limits_set_budget_refuses_max_and_clear(invoke, mock_api):
    route = mock_api.put(_BUDGETS).respond(200, json=SAMPLE_LINE)
    result = invoke(_set_budget("--max", "5", "--clear"))

    assert result.exit_code == 2
    assert not route.called


def test_limits_set_budget_refuses_an_unknown_window(invoke, mock_api):
    route = mock_api.put(_BUDGETS).respond(200, json=SAMPLE_LINE)
    result = invoke(
        [
            "agentic",
            "limits",
            "set-budget",
            "--connection",
            _CONNECTION_ID,
            "--class",
            "linkedin.invitations",
            "--window",
            "month",
            "--max",
            "5",
        ]
    )

    assert result.exit_code == 2
    assert not route.called


def test_limits_set_budget_prints_the_api_detail_on_422(invoke, mock_api):
    """An override above the platform default answers 422 and exits 2."""
    mock_api.put(_BUDGETS).respond(422, json={"detail": "above the platform default of 20"})
    result = invoke(_set_budget("--max", "999"))

    assert result.exit_code == 2
    assert "above the platform default of 20" in result.output


def test_limits_set_budget_not_found(invoke, mock_api):
    """A connection outside the organization answers 404 and exits 3."""
    mock_api.put(_BUDGETS).respond(404, json={"detail": "connection not found"})
    result = invoke(_set_budget("--max", "5"))

    assert result.exit_code == 3
