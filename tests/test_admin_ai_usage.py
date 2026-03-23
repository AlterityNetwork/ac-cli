"""Tests for admin ai-usage commands."""

import json

SAMPLE_SUMMARY = {
    "total_requests": 1000,
    "total_tokens": 500000,
    "total_cost": 12.50,
    "by_model": [
        {"model_id": "gpt-4", "provider": "openai", "requests": 600, "tokens": 300000, "cost": 9.00},
        {"model_id": "claude-3", "provider": "anthropic", "requests": 400, "tokens": 200000, "cost": 3.50},
    ],
}

SAMPLE_USERS = {
    "items": [
        {
            "email": "alice@example.com",
            "full_name": "Alice Smith",
            "total_cost": 8.00,
            "total_tokens": 300000,
            "total_requests": 600,
            "last_active": "2026-03-20T10:00:00Z",
        },
    ],
    "total": 1,
}

SAMPLE_USER_DETAIL = {
    "email": "alice@example.com",
    "full_name": "Alice Smith",
    "total_cost": 8.00,
    "total_tokens": 300000,
    "total_requests": 600,
    "by_model": [
        {"model_id": "gpt-4", "provider": "openai", "requests": 400, "tokens": 200000, "cost": 6.00},
    ],
    "by_workflow": [
        {"workflow_id": "wf-enrich", "requests": 300, "tokens": 150000, "cost": 4.50},
    ],
}

SAMPLE_BY_MODEL = [
    {"model_id": "gpt-4", "provider": "openai", "requests": 600, "tokens": 300000, "cost": 9.00},
    {"model_id": "claude-3", "provider": "anthropic", "requests": 400, "tokens": 200000, "cost": 3.50},
]

SAMPLE_BY_WORKFLOW = [
    {"workflow_id": "wf-enrich", "requests": 500, "tokens": 250000, "cost": 7.50},
    {"workflow_id": "wf-score", "requests": 300, "tokens": 150000, "cost": 3.00},
]

SAMPLE_DETAILS = {
    "items": [
        {
            "id": "rec-1",
            "model_id": "gpt-4",
            "user_email": "alice@example.com",
            "workflow_id": "wf-enrich",
            "tokens": 500,
            "cost": 0.015,
            "created_at": "2026-03-20T10:00:00Z",
        },
    ],
}


def test_ai_usage_summary(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "ai-usage", "summary"])
    assert result.exit_code == 0
    assert "1000" in result.output


def test_ai_usage_summary_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "--json", "ai-usage", "summary"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["total_requests"] == 1000


def test_ai_usage_summary_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke([
        "admin", "ai-usage", "summary",
        "--start-date", "2026-03-01",
        "--end-date", "2026-03-20",
        "--org-id", "org-123",
    ])
    assert result.exit_code == 0


def test_ai_usage_users(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/users").respond(200, json=SAMPLE_USERS)
    result = invoke(["admin", "ai-usage", "users"])
    assert result.exit_code == 0
    assert "alice@example" in result.output


def test_ai_usage_users_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/users").respond(200, json=SAMPLE_USERS)
    result = invoke(["admin", "--json", "ai-usage", "users"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"][0]["email"] == "alice@example.com"


def test_ai_usage_users_with_options(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/users").respond(200, json=SAMPLE_USERS)
    result = invoke([
        "admin", "ai-usage", "users",
        "--sort", "total_cost",
        "--order", "desc",
        "--page", "2",
        "--page-size", "10",
        "--search", "alice",
    ])
    assert result.exit_code == 0


def test_ai_usage_user(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/users/user-123").respond(200, json=SAMPLE_USER_DETAIL)
    result = invoke(["admin", "ai-usage", "user", "user-123"])
    assert result.exit_code == 0
    assert "alice@example.com" in result.output
    assert "gpt-4" in result.output


def test_ai_usage_user_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/users/user-123").respond(200, json=SAMPLE_USER_DETAIL)
    result = invoke(["admin", "--json", "ai-usage", "user", "user-123"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["email"] == "alice@example.com"
    assert len(parsed["by_model"]) == 1


def test_ai_usage_by_model(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/by-model").respond(200, json=SAMPLE_BY_MODEL)
    result = invoke(["admin", "ai-usage", "by-model"])
    assert result.exit_code == 0
    assert "gpt-4" in result.output


def test_ai_usage_by_model_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/by-model").respond(200, json=SAMPLE_BY_MODEL)
    result = invoke(["admin", "--json", "ai-usage", "by-model"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed) == 2
    assert parsed[0]["model_id"] == "gpt-4"


def test_ai_usage_by_workflow(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/by-workflow").respond(200, json=SAMPLE_BY_WORKFLOW)
    result = invoke(["admin", "ai-usage", "by-workflow"])
    assert result.exit_code == 0
    assert "wf-enrich" in result.output


def test_ai_usage_by_workflow_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/by-workflow").respond(200, json=SAMPLE_BY_WORKFLOW)
    result = invoke(["admin", "--json", "ai-usage", "by-workflow"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed) == 2
    assert parsed[0]["workflow_id"] == "wf-enrich"


def test_ai_usage_details(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/details").respond(200, json=SAMPLE_DETAILS)
    result = invoke(["admin", "ai-usage", "details"])
    assert result.exit_code == 0
    assert "rec-1" in result.output


def test_ai_usage_details_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/details").respond(200, json=SAMPLE_DETAILS)
    result = invoke(["admin", "--json", "ai-usage", "details"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"][0]["id"] == "rec-1"


def test_ai_usage_details_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/details").respond(200, json=SAMPLE_DETAILS)
    result = invoke([
        "admin", "ai-usage", "details",
        "--model-id", "gpt-4",
        "--user-id", "user-123",
        "--workflow-run-id", "run-456",
        "--limit", "10",
        "--offset", "5",
    ])
    assert result.exit_code == 0
