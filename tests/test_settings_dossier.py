"""Tests for `ac settings dossier` (the Company dossier)."""

import json

_BASE = "/api/v1/settings/dossier"

SAMPLE = {
    "organization_id": "org-456",
    "company": {"name": "Northwind Studio", "description": None},
    "services": [],
    "targeting": {"profiles": [], "legacy_target_customers": None, "legacy_target_locations": []},
    "offers": [],
    "offers_total": 0,
    "documents": [],
    "documents_total": 0,
    "generated_at": "2026-10-06T12:00:00+00:00",
    "user": None,
    "markdown": "# Company dossier: Northwind Studio\n\n## Company [beta]\n",
    "gaps": [
        {
            "section": "company",
            "field": "description",
            "message": "Add a description of your company.",
            "settings_path": "/settings/organization",
        }
    ],
}


def test_dossier_get_prints_the_markdown(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE)
    result = invoke(["settings", "dossier", "get"])
    assert result.exit_code == 0, result.output
    assert "# Company dossier: Northwind Studio" in result.output
    assert "## Company [beta]" in result.output
    assert "include_user" not in str(route.calls.last.request.url)


def test_dossier_get_lists_the_gaps(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=SAMPLE)
    result = invoke(["settings", "dossier", "get"])
    assert result.exit_code == 0
    assert "Add a description of your company." in result.output
    assert "/settings/organization" in result.output


def test_dossier_get_json(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=SAMPLE)
    result = invoke(["settings", "dossier", "get", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["company"]["name"] == "Northwind Studio"
    assert data["gaps"][0]["field"] == "description"


def test_dossier_get_user_sends_include_user(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE)
    result = invoke(["settings", "dossier", "get", "--user"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params["include_user"] == "true"


def test_dossier_get_forbidden(invoke, mock_api):
    mock_api.get(_BASE).respond(403, json={"detail": {"code": "insufficient_role"}})
    result = invoke(["settings", "dossier", "get"])
    assert result.exit_code == 4


def test_dossier_get_forbidden_json(invoke, mock_api):
    mock_api.get(_BASE).respond(403, json={"detail": "Not allowed"})
    result = invoke(["settings", "dossier", "get", "--json"])
    assert result.exit_code == 4
    assert json.loads(result.output)["status_code"] == 403
