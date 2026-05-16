"""Tests for admin managed onboarding commands."""

import json

SAMPLE_ACCOUNT = {
    "user_id": "user-onboard-1",
    "organization_id": "org-onboard-1",
    "onboarding_link": "https://app.example.com/onboarding/abc123",
    "status": "setup",
}

SAMPLE_LIST_ITEM = {
    "organization_id": "org-onboard-1",
    "organization_name": "Onboard Corp",
    "user_email": "user@onboard.com",
    "user_first_name": "Jane",
    "user_last_name": "Doe",
    "onboarding_status": "pending",
    "created_at": "2026-01-01T00:00:00Z",
}

SAMPLE_SETTINGS = {
    "terms_html": "<p>Terms</p>",
    "calendly_url": "https://calendly.com/test",
    "calendly_enabled": True,
}

_BASE = "/api/v1/admin/onboarding"


def test_onboarding_create(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(
        [
            "admin",
            "onboarding",
            "create",
            "--email",
            "user@example.com",
            "--first-name",
            "Jane",
            "--last-name",
            "Doe",
            "--org-name",
            "Test Corp",
        ]
    )
    assert result.exit_code == 0
    assert "org-onboard-1" in result.output


def test_onboarding_create_json(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(
        [
            "admin",
            "onboarding",
            "create",
            "--email",
            "user@example.com",
            "--first-name",
            "Jane",
            "--last-name",
            "Doe",
            "--org-name",
            "Test Corp",
            "--json",
        ]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["user_id"] == "user-onboard-1"
    assert parsed["organization_id"] == "org-onboard-1"


def test_onboarding_list(invoke, mock_api):
    mock_api.get(f"{_BASE}/accounts").respond(
        200,
        json={
            "items": [SAMPLE_LIST_ITEM],
            "total": 1,
            "page": 1,
            "page_size": 25,
        },
    )
    result = invoke(["admin", "onboarding", "list"])
    assert result.exit_code == 0
    assert "Onboard Corp" in result.output


def test_onboarding_list_with_filters(invoke, mock_api):
    mock_api.get(f"{_BASE}/accounts").respond(
        200,
        json={
            "items": [SAMPLE_LIST_ITEM],
            "total": 1,
            "page": 1,
            "page_size": 25,
        },
    )
    result = invoke(["admin", "onboarding", "list", "--status", "active", "--query", "test"])
    assert result.exit_code == 0


def test_onboarding_list_json(invoke, mock_api):
    payload = {"items": [SAMPLE_LIST_ITEM], "total": 1, "page": 1, "page_size": 25}
    mock_api.get(f"{_BASE}/accounts").respond(200, json=payload)
    result = invoke(["admin", "onboarding", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"][0]["organization_name"] == "Onboard Corp"


def test_onboarding_get(invoke, mock_api):
    mock_api.get(f"{_BASE}/accounts/org-onboard-1").respond(200, json=SAMPLE_LIST_ITEM)
    result = invoke(["admin", "onboarding", "get", "org-onboard-1"])
    assert result.exit_code == 0


def test_onboarding_delete_with_yes(invoke, mock_api):
    mock_api.delete(f"{_BASE}/accounts/org-onboard-1").respond(200, json={"deleted": True})
    result = invoke(["admin", "onboarding", "delete", "org-onboard-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_onboarding_delete_aborted(invoke, mock_api):
    result = invoke(["admin", "onboarding", "delete", "org-onboard-1"], input="n\n")
    assert result.exit_code == 1


def test_onboarding_send_link(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts/org-onboard-1/send-link").respond(
        200,
        json={
            "onboarding_link": "https://app.example.com/onboarding/new123",
            "email_sent": False,
        },
    )
    result = invoke(["admin", "onboarding", "send-link", "org-onboard-1"])
    assert result.exit_code == 0
    assert "new123" in result.output


def test_onboarding_send_link_email(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts/org-onboard-1/send-link").respond(
        200,
        json={
            "onboarding_link": "https://app.example.com/onboarding/new123",
            "email_sent": True,
        },
    )
    result = invoke(["admin", "onboarding", "send-link", "org-onboard-1", "--send-email"])
    assert result.exit_code == 0
    assert "Email sent" in result.output


def test_onboarding_impersonate(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts/org-onboard-1/impersonate").respond(
        200,
        json={
            "magic_link": "https://app.example.com/magic/xyz789",
        },
    )
    result = invoke(["admin", "onboarding", "impersonate", "org-onboard-1"])
    assert result.exit_code == 0
    assert "xyz789" in result.output


def test_onboarding_end_impersonation(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts/org-onboard-1/end-impersonate").respond(
        200,
        json={
            "organization_id": "org-onboard-1",
            "user_id": "user-onboard-1",
            "signed_out": True,
        },
    )
    result = invoke(["admin", "onboarding", "end-impersonation", "org-onboard-1"])
    assert result.exit_code == 0
    assert "ended" in result.output.lower()


def test_onboarding_end_impersonation_json(invoke, mock_api):
    payload = {
        "organization_id": "org-onboard-1",
        "user_id": "user-onboard-1",
        "signed_out": True,
    }
    mock_api.post(f"{_BASE}/accounts/org-onboard-1/end-impersonate").respond(200, json=payload)
    result = invoke(["admin", "onboarding", "end-impersonation", "org-onboard-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["signed_out"] is True
    assert parsed["organization_id"] == "org-onboard-1"


def test_onboarding_activate(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts/org-onboard-1/activate").respond(
        200,
        json={
            "status": "active",
        },
    )
    result = invoke(["admin", "onboarding", "activate", "org-onboard-1"])
    assert result.exit_code == 0
    assert "activated" in result.output


def test_onboarding_activate_no_reset(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts/org-onboard-1/activate").respond(
        200,
        json={
            "status": "active",
        },
    )
    result = invoke(
        [
            "admin",
            "onboarding",
            "activate",
            "org-onboard-1",
            "--no-send-password-reset",
        ]
    )
    assert result.exit_code == 0


def test_onboarding_deactivate(invoke, mock_api):
    mock_api.post(f"{_BASE}/accounts/org-onboard-1/deactivate").respond(
        200,
        json={
            "status": "pending",
        },
    )
    result = invoke(["admin", "onboarding", "deactivate", "org-onboard-1"])
    assert result.exit_code == 0
    assert "deactivated" in result.output


def test_onboarding_update_config(invoke, mock_api):
    mock_api.patch(f"{_BASE}/accounts/org-onboard-1/config").respond(
        200,
        json={
            "show_calendly": True,
            "calendly_url": "https://calendly.com/updated",
        },
    )
    result = invoke(
        [
            "admin",
            "onboarding",
            "update-config",
            "org-onboard-1",
            "--calendly-url",
            "https://calendly.com/updated",
        ]
    )
    assert result.exit_code == 0
    assert "Updated" in result.output


def test_onboarding_get_settings(invoke, mock_api):
    mock_api.get(f"{_BASE}/settings").respond(200, json=SAMPLE_SETTINGS)
    result = invoke(["admin", "onboarding", "get-settings"])
    assert result.exit_code == 0


def test_onboarding_get_settings_json(invoke, mock_api):
    mock_api.get(f"{_BASE}/settings").respond(200, json=SAMPLE_SETTINGS)
    result = invoke(["admin", "onboarding", "get-settings", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["calendly_enabled"] is True


def test_onboarding_update_settings(invoke, mock_api):
    mock_api.put(f"{_BASE}/settings").respond(200, json=SAMPLE_SETTINGS)
    result = invoke(
        [
            "admin",
            "onboarding",
            "update-settings",
            "--calendly-url",
            "https://calendly.com/new",
        ]
    )
    assert result.exit_code == 0
    assert "Updated" in result.output
