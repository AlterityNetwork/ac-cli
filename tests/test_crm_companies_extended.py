"""Extended tests for CRM companies commands: delete edge cases and error handling."""

import json

import httpx
import respx

from tests.conftest import WHOAMI_RESPONSE


SAMPLE_COMPANY = {
    "id": "c1",
    "organization_id": "org-456",
    "name": "Acme Corp",
    "industry": "SaaS",
    "lifecycle_stage": "prospect",
    "location": "San Francisco",
    "website": "https://acme.com",
    "tags": ["target"],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "data_version": 1,
}


def test_companies_delete_not_found(invoke, mock_api):
    """Delete returns exit code 3 when company does not exist."""
    mock_api.delete("/api/v1/crm/companies/nonexistent").respond(
        404, json={"detail": "Not found"}
    )
    result = invoke(["crm", "companies", "delete", "nonexistent", "--yes"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_companies_delete_json_error(invoke, mock_api):
    """Delete with --json returns structured JSON error on 404."""
    mock_api.delete("/api/v1/crm/companies/nonexistent").respond(
        404, json={"detail": "Not found"}
    )
    result = invoke(["crm", "--json", "companies", "delete", "nonexistent", "--yes"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 404
    assert parsed["detail"] == "Not found"


def test_companies_list_network_timeout(invoke, mock_api):
    """Network timeout on list returns exit code 1 with connection error."""
    mock_api.get("/api/v1/crm/companies").mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )
    result = invoke(["crm", "companies", "list"])
    assert result.exit_code == 1
    assert "Connection" in result.output or "timed out" in result.output


def test_companies_get_network_timeout_json(invoke, mock_api):
    """Network timeout with --json returns structured JSON error."""
    mock_api.get("/api/v1/crm/companies/c1").mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )
    result = invoke(["crm", "--json", "companies", "get", "c1"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] is None
    assert "timed out" in parsed["detail"]


def test_companies_get_invalid_json_response(invoke, mock_api):
    """Server returns non-JSON response body — command handles gracefully."""
    mock_api.get("/api/v1/crm/companies/c1").respond(
        200,
        content=b"<html>Internal Server Error</html>",
        headers={"content-type": "text/html"},
    )
    result = invoke(["crm", "companies", "get", "c1"])
    # The command will try to call resp.json() and fail — should not exit 0 cleanly
    # (either it raises or prints garbled output, but should not silently succeed)
    assert result.exit_code != 0 or "Internal Server Error" in result.output


def test_companies_create_missing_required_name(invoke, mock_api):
    """Create without --name exits with error (Typer validation)."""
    result = invoke(["crm", "companies", "create"])
    assert result.exit_code != 0
    assert "Missing" in result.output or "--name" in result.output or "required" in result.output.lower()


def test_companies_delete_missing_company_id(invoke, mock_api):
    """Delete without company_id argument exits with error (Typer validation)."""
    result = invoke(["crm", "companies", "delete"])
    assert result.exit_code != 0
    assert "Missing" in result.output or "COMPANY_ID" in result.output or "required" in result.output.lower()
