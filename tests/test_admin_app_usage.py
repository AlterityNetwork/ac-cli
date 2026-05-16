"""Tests for admin app-usage commands."""

import json

SAMPLE_SUMMARY = {
    "total_opens": 150,
    "total_runs": 80,
    "total_events": 500,
    "unique_users": 12,
}

SAMPLE_USERS = {
    "items": [
        {
            "email": "alice@example.com",
            "full_name": "Alice Smith",
            "total_opens": 50,
            "total_runs": 30,
            "total_events": 200,
            "last_active": "2026-03-20T10:00:00Z",
        },
    ],
    "total": 1,
}

SAMPLE_USER_DETAIL = {
    "email": "alice@example.com",
    "full_name": "Alice Smith",
    "total_opens": 50,
    "total_runs": 30,
    "total_events": 200,
    "by_app": [
        {"app_name": "CRM", "opens": 30, "runs": 20, "events": 120},
    ],
    "recent_events": [
        {"event_type": "page_view", "app_name": "CRM", "created_at": "2026-03-20T10:00:00Z"},
    ],
}


def test_app_usage_summary(invoke, mock_api):
    mock_api.get("/api/v1/admin/app-usage/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "app-usage", "summary"])
    assert result.exit_code == 0
    assert "150" in result.output


def test_app_usage_summary_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/app-usage/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "app-usage", "summary", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["total_opens"] == 150


def test_app_usage_summary_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/admin/app-usage/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(
        [
            "admin",
            "app-usage",
            "summary",
            "--start-date",
            "2026-03-01",
            "--end-date",
            "2026-03-20",
            "--org-id",
            "org-123",
        ]
    )
    assert result.exit_code == 0


def test_app_usage_users(invoke, mock_api):
    mock_api.get("/api/v1/admin/app-usage/users").respond(200, json=SAMPLE_USERS)
    result = invoke(["admin", "app-usage", "users"])
    assert result.exit_code == 0
    assert "alice@example.com" in result.output


def test_app_usage_users_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/app-usage/users").respond(200, json=SAMPLE_USERS)
    result = invoke(["admin", "app-usage", "users", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"][0]["email"] == "alice@example.com"


def test_app_usage_users_with_options(invoke, mock_api):
    mock_api.get("/api/v1/admin/app-usage/users").respond(200, json=SAMPLE_USERS)
    result = invoke(
        [
            "admin",
            "app-usage",
            "users",
            "--sort",
            "total_opens",
            "--order",
            "desc",
            "--page",
            "2",
            "--page-size",
            "10",
            "--search",
            "alice",
        ]
    )
    assert result.exit_code == 0


def test_app_usage_user(invoke, mock_api):
    mock_api.get("/api/v1/admin/app-usage/users/user-123").respond(200, json=SAMPLE_USER_DETAIL)
    result = invoke(["admin", "app-usage", "user", "user-123"])
    assert result.exit_code == 0
    assert "alice@example.com" in result.output
    assert "CRM" in result.output


def test_app_usage_user_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/app-usage/users/user-123").respond(200, json=SAMPLE_USER_DETAIL)
    result = invoke(["admin", "app-usage", "user", "user-123", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["email"] == "alice@example.com"
    assert len(parsed["by_app"]) == 1
