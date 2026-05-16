"""Tests for managed onboarding commands."""

import json


def test_config(invoke, mock_api):
    mock_api.get("/api/v1/managed-onboarding/config").respond(
        200, json={"status": "active", "org_name": "Acme"}
    )
    result = invoke(["onboarding", "config"])
    assert result.exit_code == 0
    assert "Acme" in result.output


def test_config_json(invoke, mock_api):
    mock_api.get("/api/v1/managed-onboarding/config").respond(
        200, json={"status": "active", "org_name": "Acme"}
    )
    result = invoke(["onboarding", "config", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "active"


def test_config_403(invoke, mock_api):
    mock_api.get("/api/v1/managed-onboarding/config").respond(403, json={"detail": "Forbidden"})
    result = invoke(["onboarding", "config"])
    assert result.exit_code == 4


def test_complete(invoke, mock_api):
    mock_api.post("/api/v1/managed-onboarding/complete").respond(200, json={"status": "pending"})
    result = invoke(["onboarding", "complete"])
    assert result.exit_code == 0
    assert "complete" in result.output.lower()


def test_complete_json(invoke, mock_api):
    mock_api.post("/api/v1/managed-onboarding/complete").respond(200, json={"status": "pending"})
    result = invoke(["onboarding", "complete", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "pending"
