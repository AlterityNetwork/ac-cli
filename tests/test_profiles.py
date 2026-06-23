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


def test_profiles_subscription_json(invoke, mock_api):
    mock_api.get("/api/v1/subscriptions/me").respond(200, json={"id": "sub-1", "plan_id": "pro"})
    result = invoke(["profiles", "subscription", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["plan_id"] == "pro"
