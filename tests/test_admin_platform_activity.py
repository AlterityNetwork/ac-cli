"""Tests for admin platform-activity commands."""

import json

SAMPLE_SUMMARY = {
    "total_events": 5000,
    "unique_users": 150,
    "by_category": [
        {"category": "crm", "event_count": 2000},
        {"category": "chat", "event_count": 1500},
        {"category": "email", "event_count": 1500},
    ],
}

SAMPLE_USERS = {
    "data": [
        {
            "email": "alice@example.com",
            "full_name": "Alice Smith",
            "total_events": 300,
            "last_active": "2026-03-20T10:00:00Z",
        },
    ],
    "total": 1,
    "limit": 50,
    "offset": 0,
    "has_more": False,
}

SAMPLE_USER_DETAIL = {
    "email": "alice@example.com",
    "full_name": "Alice Smith",
    "total_events": 300,
    "recent_events": [
        {"event_type": "page_view", "category": "crm", "created_at": "2026-03-20T10:00:00Z"},
        {"event_type": "button_click", "category": "chat", "created_at": "2026-03-20T09:30:00Z"},
    ],
}


def test_platform_activity_summary(invoke, mock_api):
    mock_api.get("/api/v1/admin/platform-activity/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "platform-activity", "summary"])
    assert result.exit_code == 0
    assert "5000" in result.output


def test_platform_activity_summary_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/platform-activity/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "platform-activity", "summary", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["total_events"] == 5000


def test_platform_activity_summary_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/admin/platform-activity/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(
        [
            "admin",
            "platform-activity",
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


def test_platform_activity_users(invoke, mock_api):
    mock_api.get("/api/v1/admin/platform-activity/users").respond(200, json=SAMPLE_USERS)
    result = invoke(["admin", "platform-activity", "users"])
    assert result.exit_code == 0
    assert "alice@example" in result.output


def test_platform_activity_users_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/platform-activity/users").respond(200, json=SAMPLE_USERS)
    result = invoke(["admin", "platform-activity", "users", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["email"] == "alice@example.com"


def test_platform_activity_user(invoke, mock_api):
    mock_api.get("/api/v1/admin/platform-activity/users/user-123").respond(
        200, json=SAMPLE_USER_DETAIL
    )
    result = invoke(["admin", "platform-activity", "user", "user-123"])
    assert result.exit_code == 0
    assert "alice@example.com" in result.output
    assert "page_view" in result.output


def test_platform_activity_user_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/platform-activity/users/user-123").respond(
        200, json=SAMPLE_USER_DETAIL
    )
    result = invoke(["admin", "platform-activity", "user", "user-123", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["email"] == "alice@example.com"
    assert len(parsed["recent_events"]) == 2
