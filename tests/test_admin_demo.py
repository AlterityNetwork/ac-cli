"""Tests for admin demo commands."""

import json

SAMPLE_ACCOUNT = {
    "org_id": "org-demo-1",
    "org_name": "Demo Corp",
    "status": "active",
    "created_at": "2026-01-01T00:00:00Z",
}

SAMPLE_SCRAPE = {
    "name": "Acme Corp",
    "industry": "SaaS",
    "description": "A software company",
}


def test_demo_scrape_website(invoke, mock_api):
    mock_api.post("/api/v1/admin/demo/scrape-website").respond(200, json=SAMPLE_SCRAPE)
    result = invoke(["admin", "demo", "scrape-website", "--url", "https://example.com"])
    assert result.exit_code == 0


def test_demo_generate_org(invoke, mock_api):
    mock_api.post("/api/v1/admin/demo/generate-random-org").respond(
        200, json={"name": "Random Corp"}
    )
    result = invoke(["admin", "demo", "generate-org"])
    assert result.exit_code == 0


def test_demo_generate_profile(invoke, mock_api):
    mock_api.post("/api/v1/admin/demo/generate-random-profile").respond(
        200, json={"name": "John Doe"}
    )
    result = invoke(["admin", "demo", "generate-profile"])
    assert result.exit_code == 0


def test_demo_prepare_account(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/prepare-account").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(["admin", "demo", "prepare-account", "--org-name", "Demo Corp"])
    assert result.exit_code == 0
    # Default: full CRM data — skip_crm_data is not sent.
    body = json.loads(route.calls.last.request.content)
    assert "skip_crm_data" not in body


def test_demo_prepare_account_empty(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/prepare-account").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(["admin", "demo", "prepare-account", "--org-name", "Demo Corp", "--empty"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["skip_crm_data"] is True


def test_demo_list_accounts(invoke, mock_api):
    mock_api.get("/api/v1/admin/demo/accounts").respond(
        200,
        json={
            "data": [SAMPLE_ACCOUNT],
            "total": 1,
            "page": 1,
            "page_size": 50,
        },
    )
    result = invoke(["admin", "demo", "list-accounts"])
    assert result.exit_code == 0
    assert "Demo Corp" in result.output


def test_demo_list_accounts_json(invoke, mock_api):
    payload = {"data": [SAMPLE_ACCOUNT], "total": 1, "page": 1, "page_size": 50}
    mock_api.get("/api/v1/admin/demo/accounts").respond(200, json=payload)
    result = invoke(["admin", "demo", "list-accounts", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["org_name"] == "Demo Corp"


def test_demo_get_account(invoke, mock_api):
    mock_api.get("/api/v1/admin/demo/accounts/org-demo-1").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(["admin", "demo", "get-account", "org-demo-1"])
    assert result.exit_code == 0


def test_demo_update_account(invoke, mock_api):
    updated = {**SAMPLE_ACCOUNT, "status": "inactive"}
    mock_api.patch("/api/v1/admin/demo/accounts/org-demo-1").respond(200, json=updated)
    result = invoke(["admin", "demo", "update-account", "org-demo-1", "--status", "inactive"])
    assert result.exit_code == 0
    assert "Updated" in result.output


def test_demo_delete_account_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/demo/accounts/org-demo-1").respond(204)
    result = invoke(["admin", "demo", "delete-account", "org-demo-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_demo_delete_account_aborted(invoke, mock_api):
    result = invoke(["admin", "demo", "delete-account", "org-demo-1"], input="n\n")
    assert result.exit_code == 1


def test_demo_cleanup(invoke, mock_api):
    mock_api.post("/api/v1/admin/demo/cleanup").respond(200, json={"cleaned": 5})
    result = invoke(["admin", "demo", "cleanup", "--yes"])
    assert result.exit_code == 0
    assert "Cleanup complete" in result.output


def test_demo_stats(invoke, mock_api):
    mock_api.get("/api/v1/admin/demo/stats").respond(200, json={"total_accounts": 10, "active": 8})
    result = invoke(["admin", "demo", "stats"])
    assert result.exit_code == 0
