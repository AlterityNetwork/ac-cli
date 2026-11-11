"""Tests for sequences signals commands (`for` and `recent` sub-commands)."""

import json

SAMPLE_SIGNAL = {
    "id": "sig-1",
    "signal_type": "funding",
    "title": "Funding",
    "snippet": "Raised $50M Series B",
    "source": "TechCrunch",
    "url": "https://techcrunch.com/example",
    "date": "2026-04-10",
}

SAMPLE_RECENT_ROW = {
    "company_id": "comp-1",
    "company_name": "Acme Corp",
    "signal": SAMPLE_SIGNAL,
}


# -- `ac sequences signals for <recipient_id>` -----------------------------------


def test_signals_for_get(invoke, mock_api):
    mock_api.get("/api/v1/sequences/recipients/r-1/sales-signals").respond(
        200, json=[SAMPLE_SIGNAL]
    )
    result = invoke(["sequences", "signals", "for", "r-1"])
    assert result.exit_code == 0
    assert "Funding" in result.output


def test_signals_for_get_json(invoke, mock_api):
    mock_api.get("/api/v1/sequences/recipients/r-1/sales-signals").respond(
        200, json=[SAMPLE_SIGNAL]
    )
    result = invoke(["sequences", "signals", "for", "r-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["signal_type"] == "funding"


def test_signals_for_not_found(invoke, mock_api):
    mock_api.get("/api/v1/sequences/recipients/bad/sales-signals").respond(
        404, json={"detail": "Not found"}
    )
    result = invoke(["sequences", "signals", "for", "bad"])
    assert result.exit_code == 3
    assert "404" in result.output


# -- `ac sequences signals recent` ----------------------------------------------


def test_signals_recent_default(invoke, mock_api):
    mock_api.get("/api/v1/sequences/signals/recent").respond(200, json=[SAMPLE_RECENT_ROW])
    result = invoke(["sequences", "signals", "recent"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output
    assert "Funding" in result.output


def test_signals_recent_since_days(invoke, mock_api):
    route = mock_api.get("/api/v1/sequences/signals/recent").respond(200, json=[SAMPLE_RECENT_ROW])
    result = invoke(["sequences", "signals", "recent", "--since-days", "14"])
    assert result.exit_code == 0
    request = route.calls.last.request
    assert request.url.params.get("since_days") == "14"


def test_signals_recent_json(invoke, mock_api):
    mock_api.get("/api/v1/sequences/signals/recent").respond(200, json=[SAMPLE_RECENT_ROW])
    result = invoke(["sequences", "signals", "recent", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["company_name"] == "Acme Corp"
    assert parsed[0]["signal"]["signal_type"] == "funding"


def test_signals_recent_empty(invoke, mock_api):
    mock_api.get("/api/v1/sequences/signals/recent").respond(200, json=[])
    result = invoke(["sequences", "signals", "recent", "--since-days", "3"])
    assert result.exit_code == 0
    assert "No signals" in result.output
