"""Tests for agent-friendly features: JSON errors, semantic exit codes, AC_YES, health --json, whoami --json."""

import json
import os
from unittest.mock import patch

from tests.conftest import WHOAMI_RESPONSE


# -- Structured JSON errors ---------------------------------------------------


def test_json_error_404(invoke, mock_api):
    """When --json is active, 404 errors return structured JSON."""
    mock_api.get("/api/v1/crm/companies/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["crm", "--json", "companies", "get", "bad"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 404
    assert parsed["detail"] == "Not found"


def test_json_error_403(invoke, mock_api):
    """When --json is active, 403 errors return structured JSON with exit code 4."""
    mock_api.get("/api/v1/crm/companies").respond(403, json={"detail": "Forbidden"})
    result = invoke(["crm", "--json", "companies", "list"])
    assert result.exit_code == 4
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 403


def test_json_error_422(invoke, mock_api):
    """When --json is active, 422 errors return structured JSON with exit code 2."""
    mock_api.post("/api/v1/crm/companies").respond(422, json={"detail": "Validation error"})
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    result = invoke(["crm", "--json", "companies", "create", "--name", "Bad"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 422


def test_json_error_409(invoke, mock_api):
    """When --json is active, 409 errors return structured JSON with exit code 5."""
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/orgs/org-456/apps/email-finder").respond(409, json={"detail": "Already installed"})
    result = invoke(["apps", "--json", "install", "email-finder"])
    assert result.exit_code == 5
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 409


def test_rich_error_still_works(invoke, mock_api):
    """Without --json, errors still print Rich-formatted text."""
    mock_api.get("/api/v1/crm/companies/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["crm", "companies", "get", "bad"])
    assert result.exit_code == 3
    assert "404" in result.output
    assert "Not found" in result.output


# -- Semantic exit codes (without --json) -------------------------------------


def test_exit_code_404(invoke, mock_api):
    mock_api.get("/api/v1/crm/companies/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["crm", "companies", "get", "bad"])
    assert result.exit_code == 3


def test_exit_code_403(invoke, mock_api):
    mock_api.get("/api/v1/crm/companies").respond(403, json={"detail": "Forbidden"})
    result = invoke(["crm", "companies", "list"])
    assert result.exit_code == 4


def test_exit_code_422(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/companies").respond(422, json={"detail": "Validation error"})
    result = invoke(["crm", "companies", "create", "--name", "Bad"])
    assert result.exit_code == 2


def test_exit_code_500(invoke, mock_api):
    mock_api.get("/api/v1/crm/companies").respond(500, json={"detail": "Internal error"})
    result = invoke(["crm", "companies", "list"])
    assert result.exit_code == 1


# -- health --json ------------------------------------------------------------


def test_health_check_json(invoke, mock_api, mock_config):
    """health --json check returns JSON output."""
    import httpx
    import respx

    with respx.mock:
        respx.get("http://test-api:8008/health").respond(200, json={"status": "healthy"})
        result = invoke(["health", "--json", "check", "--api-url", "http://test-api:8008"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "healthy"


def test_health_check_json_error(invoke, mock_api, mock_config):
    """health --json check returns JSON on error."""
    import respx

    with respx.mock:
        respx.get("http://test-api:8008/health").respond(503, json={"status": "unhealthy"})
        result = invoke(["health", "--json", "check", "--api-url", "http://test-api:8008"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True


def test_health_check_rich(invoke, mock_api, mock_config):
    """health check without --json returns Rich output."""
    import respx

    with respx.mock:
        respx.get("http://test-api:8008/health").respond(200, json={"status": "healthy"})
        result = invoke(["health", "check", "--api-url", "http://test-api:8008"])
    assert result.exit_code == 0
    assert "healthy" in result.output


# -- whoami --json ------------------------------------------------------------


def test_whoami_json(invoke, mock_api):
    """whoami --json returns JSON output."""
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    result = invoke(["whoami", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["email"] == "test@example.com"
    assert "environment" in parsed


def test_whoami_json_error(invoke, mock_api):
    """whoami --json returns JSON error on auth failure (403)."""
    mock_api.get("/whoami").respond(403, json={"detail": "Not authorized"})
    result = invoke(["whoami", "--json"])
    assert result.exit_code == 4
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 403


def test_whoami_rich(invoke, mock_api):
    """whoami without --json returns Rich output."""
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    result = invoke(["whoami"])
    assert result.exit_code == 0
    assert "test@example.com" in result.output


# -- AC_YES env var -----------------------------------------------------------


def test_ac_yes_env_skips_confirm(invoke, mock_api):
    """AC_YES=1 skips confirmation prompt on delete."""
    mock_api.delete("/api/v1/crm/companies/c1").respond(204)
    with patch.dict(os.environ, {"AC_YES": "1"}):
        result = invoke(["crm", "companies", "delete", "c1"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_ac_yes_true_skips_confirm(invoke, mock_api):
    """AC_YES=true also works."""
    mock_api.delete("/api/v1/crm/companies/c1").respond(204)
    with patch.dict(os.environ, {"AC_YES": "true"}):
        result = invoke(["crm", "companies", "delete", "c1"])
    assert result.exit_code == 0


def test_ac_yes_unset_prompts(invoke, mock_api):
    """Without AC_YES or --yes, delete prompts for confirmation."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("AC_YES", None)
        result = invoke(["crm", "companies", "delete", "c1"], input="n\n")
    assert result.exit_code == 1
