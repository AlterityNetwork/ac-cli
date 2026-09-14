"""Tests for admin copilots commands."""

SAMPLE_COPILOT = {
    "user_id": "u-1",
    "email": "copilot@agencycore.ai",
    "first_name": "Cora",
    "last_name": "Pilot",
    "avatar_url": None,
    "organizations": [
        {"organization_id": "org-1", "name": "Acme"},
        {"organization_id": "org-2", "name": "Beta"},
    ],
}


def test_copilots_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/copilots").respond(200, json={"data": [SAMPLE_COPILOT]})
    result = invoke(["admin", "copilots", "list"])
    assert result.exit_code == 0
    assert "copilot@agencycore.ai" in result.output
    assert "Acme" in result.output


def test_copilots_list_empty(invoke, mock_api):
    mock_api.get("/api/v1/admin/copilots").respond(200, json={"data": []})
    result = invoke(["admin", "copilots", "list"])
    assert result.exit_code == 0
    assert "No copilots" in result.output


def test_copilots_list_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/copilots").respond(200, json={"data": [SAMPLE_COPILOT]})
    result = invoke(["admin", "copilots", "list", "--json"])
    assert result.exit_code == 0
    assert '"user_id": "u-1"' in result.output


def test_copilots_assign(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/copilots/u-1/organizations/org-1").respond(
        200, json={"ok": True}
    )
    result = invoke(["admin", "copilots", "assign", "u-1", "org-1"])
    assert result.exit_code == 0
    assert route.called
    assert "Assigned" in result.output


def test_copilots_assign_existing_member_fails(invoke, mock_api):
    mock_api.post("/api/v1/admin/copilots/u-1/organizations/org-1").respond(
        400, json={"detail": "User is already a member of this organization"}
    )
    result = invoke(["admin", "copilots", "assign", "u-1", "org-1"])
    assert result.exit_code != 0


def test_copilots_unassign_with_yes(invoke, mock_api):
    route = mock_api.delete("/api/v1/admin/copilots/u-1/organizations/org-1").respond(
        200, json={"ok": True}
    )
    result = invoke(["admin", "copilots", "unassign", "u-1", "org-1", "--yes"])
    assert result.exit_code == 0
    assert route.called
    assert "Unassigned" in result.output


def test_copilots_unassign_aborted(invoke, mock_api):
    route = mock_api.delete("/api/v1/admin/copilots/u-1/organizations/org-1").respond(
        200, json={"ok": True}
    )
    result = invoke(["admin", "copilots", "unassign", "u-1", "org-1"], input="n\n")
    assert result.exit_code == 1
    assert not route.called
