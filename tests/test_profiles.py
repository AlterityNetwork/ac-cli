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
        {"id": "user-1", "first_name": "Jane", "last_name": "Smith", "email": "jane@example.com", "job_title": "Developer"},
        {"id": "user-2", "first_name": "Bob", "last_name": "Jones", "email": "bob@example.com", "job_title": "Designer"},
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
