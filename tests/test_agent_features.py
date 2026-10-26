"""Tests for agent-friendly features: JSON errors, semantic exit codes, AC_YES, health --json, whoami --json."""

import json
import os
from unittest.mock import patch

from tests.conftest import WHOAMI_RESPONSE

# -- Structured JSON errors ---------------------------------------------------


def test_json_error_404(invoke, mock_api):
    """When --json is active, 404 errors return structured JSON."""
    mock_api.get("/api/v1/crm/companies/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["crm", "companies", "get", "bad", "--json"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 404
    assert parsed["detail"] == "Not found"


def test_json_error_403(invoke, mock_api):
    """When --json is active, 403 errors return structured JSON with exit code 4."""
    mock_api.get("/api/v1/crm/companies").respond(403, json={"detail": "Forbidden"})
    result = invoke(["crm", "companies", "list", "--json"])
    assert result.exit_code == 4
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 403


def test_json_error_422(invoke, mock_api):
    """When --json is active, 422 errors return structured JSON with exit code 2."""
    mock_api.post("/api/v1/crm/companies").respond(422, json={"detail": "Validation error"})
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    result = invoke(["crm", "companies", "create", "--name", "Bad", "--json"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 422


def test_json_error_409(invoke, mock_api):
    """When --json is active, 409 errors return structured JSON with exit code 5."""
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/orgs/org-456/apps/email-finder").respond(
        409, json={"detail": "Already installed"}
    )
    result = invoke(["apps", "install", "email-finder", "--json"])
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
    import respx

    with respx.mock:
        respx.get("http://test-api:8008/health").respond(200, json={"status": "healthy"})
        result = invoke(["health", "check", "--api-url", "http://test-api:8008", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "healthy"


def test_health_check_json_error(invoke, mock_api, mock_config):
    """health --json check returns JSON on error."""
    import respx

    with respx.mock:
        respx.get("http://test-api:8008/health").respond(503, json={"status": "unhealthy"})
        result = invoke(["health", "check", "--api-url", "http://test-api:8008", "--json"])
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


# The two 402 shapes the API answers. A route that raises HTTPException puts the
# refusal under "detail". A gated router raises EntitlementError, and the
# shared handler answers "message", "code" and "context" with no "detail".
_REFUSAL = {
    "code": "not_entitled",
    "key": "companies",
    "message": "Company Search is not on your plan.",
    "remedy": "Ask an owner to add Company Search to your plan.",
}
_DETAIL_402 = {"detail": _REFUSAL}
_HANDLER_402 = {
    "error": "Plan Limit",
    "message": "CRM is not on your plan.",
    "type": "entitlement",
    "code": "not_entitled",
    "context": {
        "code": "not_entitled",
        "key": "crm",
        "message": "CRM is not on your plan.",
        "remedy": "Ask an owner to add CRM to your plan.",
    },
}


def _start_capability(invoke, *extra):
    return invoke(
        [
            "agentic",
            "capabilities",
            "start",
            "company.search",
            "--input",
            "{}",
            "--idempotency-key",
            "key-1",
            *extra,
        ]
    )


def test_json_error_402_from_a_route_detail(invoke, mock_api):
    """A detail-shaped plan refusal exits 6 with the sentence and the remedy."""
    mock_api.post("/api/v1/agentic/capabilities/company.search/runs").respond(402, json=_DETAIL_402)
    result = _start_capability(invoke, "--json")
    assert result.exit_code == 6
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 402
    assert parsed["detail"] == (
        "Company Search is not on your plan. Ask an owner to add Company Search to your plan."
    )


def test_json_error_402_from_a_gated_router(invoke, mock_api):
    """A handler-shaped plan refusal keeps the code and remedy in context."""
    mock_api.get("/api/v1/crm/companies").respond(402, json=_HANDLER_402)
    result = invoke(["crm", "companies", "list", "--json"])
    assert result.exit_code == 6
    parsed = json.loads(result.output)
    assert parsed["status_code"] == 402
    assert parsed["detail"] == "CRM is not on your plan. Ask an owner to add CRM to your plan."
    assert parsed["context"]["code"] == "not_entitled"
    assert parsed["context"]["remedy"] == "Ask an owner to add CRM to your plan."


def test_exit_code_402_for_a_bare_detail(invoke, mock_api):
    mock_api.get("/api/v1/crm/companies").respond(402, json={"detail": "Payment Required"})
    result = invoke(["crm", "companies", "list"])
    assert result.exit_code == 6
    assert "Payment Required" in result.output


def test_a_402_detail_without_a_message_is_not_flattened(invoke, mock_api):
    """Only a refusal with a sentence is joined. Another object prints as it is."""
    mock_api.get("/api/v1/crm/companies").respond(
        402, json={"detail": {"code": "credits_exhausted"}}
    )
    result = invoke(["crm", "companies", "list", "--json"])
    assert result.exit_code == 6
    assert json.loads(result.output)["detail"] == {"code": "credits_exhausted"}


def test_a_non_402_detail_with_a_message_is_not_flattened(invoke, mock_api):
    """The join is for a plan refusal only. A 409 object keeps its fields."""
    detail = {"code": "idempotency_conflict", "message": "This key belongs to another start."}
    mock_api.post("/api/v1/agentic/capabilities/company.search/runs").respond(
        409, json={"detail": detail}
    )
    result = _start_capability(invoke, "--json")
    assert result.exit_code == 5
    assert json.loads(result.output)["detail"] == detail


def test_json_error_402_from_a_route_detail_keeps_the_code(invoke, mock_api):
    """A script must tell a missing module from a lapsed plan."""
    mock_api.post("/api/v1/agentic/capabilities/company.search/runs").respond(402, json=_DETAIL_402)
    result = _start_capability(invoke, "--json")
    parsed = json.loads(result.output)
    assert (parsed.get("context") or {}).get("code") == "not_entitled"
