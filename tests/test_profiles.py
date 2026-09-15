"""Tests for profiles commands."""

import json

SAMPLE_ME = {
    "id": "user-1",
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane@example.com",
    "job_title": "Developer",
    "bio": "Software engineer",
    "is_superadmin": False,
    "selected_organization": "org-1",
}

SAMPLE_UPDATED = {
    "id": "user-1",
    "first_name": "Janet",
    "last_name": "Smith",
    "email": "jane@example.com",
    "job_title": "Developer",
    "bio": "Software engineer",
    "is_superadmin": False,
    "selected_organization": "org-1",
}

SAMPLE_MEMBERS = {
    "data": [
        {
            "id": "user-1",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "job_title": "Developer",
        },
        {
            "id": "user-2",
            "first_name": "Bob",
            "last_name": "Jones",
            "email": "bob@example.com",
            "job_title": "Designer",
        },
    ],
    "total": 2,
}


def test_profiles_me(invoke, mock_api):
    mock_api.get("/api/v1/profiles/me").respond(200, json=SAMPLE_ME)
    result = invoke(["profiles", "me"])
    assert result.exit_code == 0
    assert "Jane" in result.output
    assert "jane@example.com" in result.output


def test_profiles_me_json(invoke, mock_api):
    mock_api.get("/api/v1/profiles/me").respond(200, json=SAMPLE_ME)
    result = invoke(["profiles", "me", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "user-1"


def test_profiles_update(invoke, mock_api):
    mock_api.patch("/api/v1/profiles/me").respond(200, json=SAMPLE_UPDATED)
    result = invoke(["profiles", "update", "--first-name", "Janet"])
    assert result.exit_code == 0
    assert "updated" in result.output.lower()


def test_profiles_update_no_fields(invoke, mock_api):
    result = invoke(["profiles", "update"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_profiles_update_json(invoke, mock_api):
    mock_api.patch("/api/v1/profiles/me").respond(200, json=SAMPLE_UPDATED)
    result = invoke(["profiles", "update", "--first-name", "Janet", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["first_name"] == "Janet"


def test_profiles_members(invoke, mock_api):
    mock_api.get("/api/v1/profiles/members").respond(200, json=SAMPLE_MEMBERS)
    result = invoke(["profiles", "members"])
    assert result.exit_code == 0
    assert "Jane" in result.output
    assert "Bob" in result.output


def test_profiles_members_shows_the_role(invoke, mock_api):
    """The team list marks a copilot seat, so the role column is printed."""
    members = {
        "data": [
            {"id": "u-9", "first_name": "Cora", "last_name": "Pilot", "role": "copilot"},
        ],
        "copilot_display_label": "Copilot",
    }
    mock_api.get("/api/v1/profiles/members").respond(200, json=members)
    result = invoke(["profiles", "members"])
    assert result.exit_code == 0
    assert "copilot" in result.output


def test_profiles_members_json(invoke, mock_api):
    mock_api.get("/api/v1/profiles/members").respond(200, json=SAMPLE_MEMBERS)
    result = invoke(["profiles", "members", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed["data"]) == 2


def test_profiles_set_organization(invoke, mock_api):
    route = mock_api.patch("/api/v1/profiles/me/organization").respond(204)
    result = invoke(["profiles", "set-organization", "org-2"])
    assert result.exit_code == 0
    assert "org-2" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"organization_id": "org-2"}


def test_profiles_set_organization_json(invoke, mock_api):
    mock_api.patch("/api/v1/profiles/me/organization").respond(204)
    result = invoke(["profiles", "set-organization", "org-2", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {"ok": True}


def test_profiles_set_organization_error(invoke, mock_api):
    # A body-less non-2xx surfaces a clean error (no traceback), the same empty-body
    # shape that broke the success path.
    mock_api.patch("/api/v1/profiles/me/organization").respond(403)
    result = invoke(["profiles", "set-organization", "org-2"])
    assert result.exit_code == 4
    assert "403" in result.output


def test_profiles_set_password(invoke, mock_api):
    mock_api.patch("/api/v1/profiles/me/password-set").respond(204)
    result = invoke(["profiles", "set-password"])
    assert result.exit_code == 0
    assert "Password marked" in result.output


def test_profiles_subscription(invoke, mock_api):
    mock_api.get("/api/v1/subscriptions/me").respond(
        200,
        json={
            "id": "sub-1",
            "plan_id": "pro",
            "billing_period": "monthly",
            "status": "active",
            "started_at": "2026-04-01",
            "ended_at": None,
            "trial_ends_at": None,
        },
    )
    result = invoke(["profiles", "subscription"])
    assert result.exit_code == 0
    assert "sub-1" in result.output


SAMPLE_USAGE = {
    "period_start": "2026-09-01T00:00:00+00:00",
    "period_end": "2026-10-01T00:00:00+00:00",
    "actions": [
        {"action_key": "company.search", "calls": 30, "total_tokens": 0, "cost_cents": 12},
        {"action_key": "front_door.turn", "calls": 4, "total_tokens": 900, "cost_cents": 3},
    ],
    "total_calls": 34,
    "total_cost_cents": 15,
}


def test_profiles_usage(invoke, mock_api):
    mock_api.get("/api/v1/subscriptions/me/usage").respond(200, json=SAMPLE_USAGE)
    result = invoke(["profiles", "usage"])
    assert result.exit_code == 0
    assert "company.search" in result.output
    assert "front_door.turn" in result.output
    assert "2026-09-01" in result.output
    assert "34" in result.output


def test_profiles_usage_with_no_rows(invoke, mock_api):
    mock_api.get("/api/v1/subscriptions/me/usage").respond(
        200,
        json={**SAMPLE_USAGE, "actions": [], "total_calls": 0, "total_cost_cents": 0},
    )
    result = invoke(["profiles", "usage"])
    assert result.exit_code == 0
    assert "No usage" in result.output


def test_profiles_usage_json(invoke, mock_api):
    mock_api.get("/api/v1/subscriptions/me/usage").respond(200, json=SAMPLE_USAGE)
    result = invoke(["profiles", "usage", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["total_calls"] == 34
    assert parsed["actions"][0]["action_key"] == "company.search"


def test_profiles_usage_prints_an_action_key_literally(invoke, mock_api):
    """print_table wraps each cell in Text, so a key holding markup prints as is."""
    mock_api.get("/api/v1/subscriptions/me/usage").respond(
        200,
        json={
            **SAMPLE_USAGE,
            "actions": [
                {
                    "action_key": "[bold]x",
                    "calls": 1,
                    "total_tokens": 0,
                    "cost_cents": 0,
                }
            ],
        },
    )
    result = invoke(["profiles", "usage"])
    assert result.exit_code == 0
    assert "[bold]" in result.output


def test_profiles_usage_error(invoke, mock_api):
    mock_api.get("/api/v1/subscriptions/me/usage").respond(500, json={"detail": "boom"})
    result = invoke(["profiles", "usage"])
    assert result.exit_code != 0


def test_profiles_subscription_json(invoke, mock_api):
    mock_api.get("/api/v1/subscriptions/me").respond(200, json={"id": "sub-1", "plan_id": "pro"})
    result = invoke(["profiles", "subscription", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["plan_id"] == "pro"
