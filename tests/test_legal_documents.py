"""Tests for legal documents commands."""

import json

SAMPLE_DOC = {
    "id": "doc-1",
    "type": "terms-of-service",
    "version": "2.0",
    "effective_date": "2026-01-01",
    "url": "https://example.com/tos",
}


def test_current(invoke, mock_api):
    mock_api.get("/api/v1/legal-documents/current/terms-of-service").respond(200, json=SAMPLE_DOC)
    result = invoke(["legal-docs", "current", "terms-of-service"])
    assert result.exit_code == 0
    assert "2.0" in result.output


def test_current_json(invoke, mock_api):
    mock_api.get("/api/v1/legal-documents/current/terms-of-service").respond(200, json=SAMPLE_DOC)
    result = invoke(["legal-docs", "current", "terms-of-service", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["version"] == "2.0"


def test_current_404(invoke, mock_api):
    mock_api.get("/api/v1/legal-documents/current/unknown").respond(
        404, json={"detail": "Not found"}
    )
    result = invoke(["legal-docs", "current", "unknown"])
    assert result.exit_code == 3


def test_status(invoke, mock_api):
    mock_api.get("/api/v1/legal-documents/status/terms-of-service").respond(
        200, json={"accepted": True, "accepted_version": "2.0", "accepted_at": "2026-01-15"}
    )
    result = invoke(["legal-docs", "status", "terms-of-service"])
    assert result.exit_code == 0
    assert "Accepted" in result.output


def test_status_json(invoke, mock_api):
    mock_api.get("/api/v1/legal-documents/status/terms-of-service").respond(
        200, json={"accepted": True, "accepted_version": "2.0"}
    )
    result = invoke(["legal-docs", "status", "terms-of-service", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["accepted"] is True


def test_status_not_accepted(invoke, mock_api):
    mock_api.get("/api/v1/legal-documents/status/terms-of-service").respond(
        200, json={"accepted": False}
    )
    result = invoke(["legal-docs", "status", "terms-of-service"])
    assert result.exit_code == 0
    assert "Not accepted" in result.output


def test_accept(invoke, mock_api):
    mock_api.post("/api/v1/legal-documents/accept").respond(200, json={"accepted": True})
    result = invoke(["legal-docs", "accept", "terms-of-service", "--version", "2.0"])
    assert result.exit_code == 0
    assert "Accepted" in result.output


def test_accept_json(invoke, mock_api):
    mock_api.post("/api/v1/legal-documents/accept").respond(200, json={"accepted": True})
    result = invoke(["legal-docs", "accept", "terms-of-service", "--version", "2.0", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["accepted"] is True
