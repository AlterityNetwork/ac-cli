"""Tests for Nylas commands."""

import json

SAMPLE_ACCOUNT = {
    "email": "user@example.com",
    "provider": "google",
    "status": "connected",
    "connected_at": "2026-01-01T00:00:00Z",
}


def test_nylas_oauth_start(invoke, mock_api):
    mock_api.get("/api/v1/nylas/oauth/start").respond(
        200, json={"url": "https://accounts.google.com/o/oauth2/auth?client_id=123"}
    )
    result = invoke(["nylas", "oauth-start"])
    assert result.exit_code == 0
    assert "https://" in result.output


def test_nylas_oauth_start_json(invoke, mock_api):
    mock_api.get("/api/v1/nylas/oauth/start").respond(
        200, json={"url": "https://accounts.google.com/o/oauth2/auth?client_id=123"}
    )
    result = invoke(["nylas", "oauth-start", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["url"].startswith("https://")


def test_nylas_account(invoke, mock_api):
    mock_api.get("/api/v1/nylas/oauth/account").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(["nylas", "account"])
    assert result.exit_code == 0
    assert "user@example.com" in result.output


def test_nylas_account_json(invoke, mock_api):
    mock_api.get("/api/v1/nylas/oauth/account").respond(200, json=SAMPLE_ACCOUNT)
    result = invoke(["nylas", "account", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["email"] == "user@example.com"


def test_nylas_org_accounts(invoke, mock_api):
    mock_api.get("/api/v1/nylas/oauth/organization/accounts").respond(
        200, json={"accounts": [SAMPLE_ACCOUNT]}
    )
    result = invoke(["nylas", "org-accounts"])
    assert result.exit_code == 0
    assert "user@example.com" in result.output


def test_nylas_disconnect(invoke, mock_api):
    mock_api.post("/api/v1/nylas/oauth/disconnect").respond(200, json={"success": True})
    result = invoke(["nylas", "disconnect", "--yes"])
    assert result.exit_code == 0
    assert "Disconnected" in result.output


def test_nylas_disconnect_aborted(invoke, mock_api):
    result = invoke(["nylas", "disconnect"], input="n\n")
    assert result.exit_code == 1


def test_nylas_send(invoke, mock_api):
    mock_api.post("/api/v1/nylas/email/send").respond(200, json={"message_id": "msg-1"})
    result = invoke(["nylas", "send", "--to", "a@b.com", "--subject", "Hi", "--body", "Hello"])
    assert result.exit_code == 0
    assert "Email sent" in result.output


def test_nylas_update_signature(invoke, mock_api):
    mock_api.put("/api/v1/nylas/email/account/signature").respond(
        200, json={"signature": "<b>My Sig</b>"}
    )
    result = invoke(["nylas", "update-signature", "--signature", "<b>My Sig</b>"])
    assert result.exit_code == 0
    assert "Signature updated" in result.output


def test_nylas_validate_signature(invoke, mock_api):
    mock_api.post("/api/v1/nylas/email/account/signature/validate").respond(
        200, json={"valid": True, "issues": []}
    )
    result = invoke(["nylas", "validate-signature", "--signature", "<b>My Sig</b>"])
    assert result.exit_code == 0
