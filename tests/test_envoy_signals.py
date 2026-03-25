"""Tests for envoy signals command."""
import json


SAMPLE_SIGNAL = {
    "id": "sig-1",
    "recipient_id": "r-1",
    "signal_type": "email_opened",
    "description": "Opened intro email",
    "strength": "strong",
    "detected_at": "2026-01-15T10:00:00Z",
}


def test_signals_get(invoke, mock_api):
    mock_api.get("/api/v1/envoy/recipients/r-1/sales-signals").respond(200, json=[SAMPLE_SIGNAL])
    result = invoke(["envoy", "signals", "r-1"])
    assert result.exit_code == 0
    assert "email_opened" in result.output


def test_signals_get_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/recipients/r-1/sales-signals").respond(200, json=[SAMPLE_SIGNAL])
    result = invoke(["envoy", "signals", "r-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["signal_type"] == "email_opened"


def test_signals_not_found(invoke, mock_api):
    mock_api.get("/api/v1/envoy/recipients/bad/sales-signals").respond(404, json={"detail": "Not found"})
    result = invoke(["envoy", "signals", "bad"])
    assert result.exit_code == 3
    assert "404" in result.output
