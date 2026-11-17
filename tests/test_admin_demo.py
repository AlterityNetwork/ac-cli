"""Tests for admin demo commands."""

import json

SAMPLE_ACCOUNT = {
    "org_id": "org-demo-1",
    "org_name": "Demo Corp",
    "status": "active",
    "created_at": "2026-01-01T00:00:00Z",
}

USER_ARGS = [
    "--user-email",
    "ada@example.com",
    "--user-first-name",
    "Ada",
    "--user-last-name",
    "Lovelace",
]

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
    route = mock_api.post("/api/v1/admin/demo/generate-random-org").respond(
        200, json={"name": "Random Corp"}
    )
    result = invoke(["admin", "demo", "generate-org", "--industry", "SaaS"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"industry": "SaaS"}


def test_demo_generate_org_requires_industry(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/generate-random-org").respond(200, json={})
    result = invoke(["admin", "demo", "generate-org"])
    assert result.exit_code == 2
    assert not route.called


def test_demo_generate_org_rejects_size(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/generate-random-org").respond(200, json={})
    result = invoke(["admin", "demo", "generate-org", "--industry", "SaaS", "--size", "small"])
    assert result.exit_code == 2
    assert not route.called


def test_demo_generate_profile(invoke, mock_api):
    mock_api.post("/api/v1/admin/demo/generate-random-profile").respond(
        200, json={"name": "John Doe"}
    )
    result = invoke(["admin", "demo", "generate-profile", "--role", "CEO"])
    assert result.exit_code == 0


def test_demo_generate_profile_sends_role(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/generate-random-profile").respond(200, json={})
    result = invoke(["admin", "demo", "generate-profile", "--role", "CEO", "--industry", "SaaS"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"role": "CEO", "industry": "SaaS"}


def test_demo_generate_profile_requires_role(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/generate-random-profile").respond(200, json={})
    result = invoke(["admin", "demo", "generate-profile"])
    assert result.exit_code == 2
    assert not route.called


def test_demo_prepare_account(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/prepare-account").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(["admin", "demo", "prepare-account", "--org-name", "Demo Corp", *USER_ARGS])
    assert result.exit_code == 0
    # Default: full CRM data, so skip_crm_data is not sent.
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "company_name": "Demo Corp",
        "user_email": "ada@example.com",
        "user_first_name": "Ada",
        "user_last_name": "Lovelace",
    }


def test_demo_prepare_account_requires_user_fields(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/prepare-account").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(["admin", "demo", "prepare-account", "--org-name", "Demo Corp"])
    assert result.exit_code == 2
    assert not route.called


def test_demo_prepare_account_rejects_template(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/prepare-account").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(
        [
            "admin",
            "demo",
            "prepare-account",
            "--org-name",
            "Demo Corp",
            *USER_ARGS,
            "--template",
            "x",
        ]
    )
    assert result.exit_code == 2
    assert not route.called


def test_demo_prepare_account_empty(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/prepare-account").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(
        ["admin", "demo", "prepare-account", "--org-name", "Demo Corp", *USER_ARGS, "--empty"]
    )
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
    route = mock_api.patch("/api/v1/admin/demo/accounts/org-demo-1").respond(
        200, json=SAMPLE_ACCOUNT
    )
    result = invoke(
        [
            "admin",
            "demo",
            "update-account",
            "org-demo-1",
            "--first-name",
            "Ada",
            "--last-name",
            "Lovelace",
            "--job-title",
            "CTO",
            "--bio",
            "Engineer",
            "--avatar-url",
            "https://example.com/a.png",
            "--website",
            "https://example.com",
        ]
    )
    assert result.exit_code == 0
    assert "Updated" in result.output
    assert json.loads(route.calls.last.request.content) == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "job_title": "CTO",
        "bio": "Engineer",
        "avatar_url": "https://example.com/a.png",
        "website": "https://example.com",
    }


def test_demo_update_account_rejects_status(invoke, mock_api):
    route = mock_api.patch("/api/v1/admin/demo/accounts/org-demo-1").respond(
        200, json=SAMPLE_ACCOUNT
    )
    result = invoke(["admin", "demo", "update-account", "org-demo-1", "--status", "inactive"])
    assert result.exit_code == 2
    assert not route.called


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


def test_demo_cleanup_sends_days_old(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/demo/cleanup").respond(200, json={"deleted_count": 0})
    result = invoke(["admin", "demo", "cleanup", "--max-age-days", "14", "--yes"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"days_old": 14}
