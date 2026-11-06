"""Tests for notifications commands."""

import json

NOTIF = {
    "id": "n-1",
    "type": "system",
    "title": "Welcome",
    "is_read": False,
    "created_at": "2026-05-10T00:00:00Z",
}


def test_notifications_list(invoke, mock_api):
    mock_api.get("/api/v1/notifications").respond(
        200, json={"data": [NOTIF], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["notifications", "list"])
    assert result.exit_code == 0
    assert "Welcome" in result.output


def test_notifications_list_unread_only(invoke, mock_api):
    route = mock_api.get("/api/v1/notifications").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["notifications", "list", "--unread-only", "--json"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params["unread_only"] == "true"


def test_notifications_unread_count(invoke, mock_api):
    mock_api.get("/api/v1/notifications/unread-count").respond(200, json={"count": 7})
    result = invoke(["notifications", "unread-count"])
    assert result.exit_code == 0
    assert "7" in result.output


def test_notifications_unread_count_json(invoke, mock_api):
    mock_api.get("/api/v1/notifications/unread-count").respond(200, json={"count": 3})
    result = invoke(["notifications", "unread-count", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"count": 3}


def test_notifications_read(invoke, mock_api):
    mock_api.post("/api/v1/notifications/n-1/read").respond(204)
    result = invoke(["notifications", "read", "n-1"])
    assert result.exit_code == 0
    assert "Marked notification n-1 read" in result.output


def test_notifications_read_all(invoke, mock_api):
    mock_api.post("/api/v1/notifications/read-all").respond(204)
    result = invoke(["notifications", "read-all"])
    assert result.exit_code == 0


def test_notifications_delete(invoke, mock_api):
    route = mock_api.delete("/api/v1/notifications/n-1").respond(204)
    result = invoke(["notifications", "delete", "n-1", "--yes"])
    assert result.exit_code == 0
    assert route.called
    assert "Deleted notification n-1" in result.output


def test_notifications_delete_json(invoke, mock_api):
    mock_api.delete("/api/v1/notifications/n-1").respond(204)
    result = invoke(["notifications", "delete", "n-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"ok": True, "id": "n-1", "action": "delete"}


def test_notifications_delete_abort(invoke, mock_api):
    route = mock_api.delete("/api/v1/notifications/n-1").respond(204)
    result = invoke(["notifications", "delete", "n-1"], input="n\n")
    assert result.exit_code != 0
    assert not route.called


def test_notifications_delete_not_found(invoke, mock_api):
    mock_api.delete("/api/v1/notifications/missing").respond(404, json={"detail": "no"})
    result = invoke(["notifications", "delete", "missing", "--yes"])
    assert result.exit_code == 3


def test_notifications_preferences(invoke, mock_api):
    mock_api.get("/api/v1/notifications/preferences").respond(
        200, json=[{"type": "mention", "channel": "email", "enabled": True}]
    )
    result = invoke(["notifications", "preferences", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)[0]["type"] == "mention"


def test_notifications_set_preference(invoke, mock_api):
    route = mock_api.put("/api/v1/notifications/preferences").respond(204)
    result = invoke(
        [
            "notifications",
            "set-preference",
            "--type",
            "mention",
            "--channel",
            "email",
            "--disabled",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"type": "mention", "channel": "email", "enabled": False}


def test_notifications_read_not_found(invoke, mock_api):
    mock_api.post("/api/v1/notifications/missing/read").respond(404, json={"detail": "no"})
    result = invoke(["notifications", "read", "missing"])
    assert result.exit_code == 3


def test_notifications_reset_preferences(invoke, mock_api):
    route = mock_api.delete("/api/v1/notifications/preferences").respond(204)
    result = invoke(["notifications", "reset-preferences", "--yes"])
    assert result.exit_code == 0
    assert route.called
    assert "Reset" in result.output or "reset" in result.output


def test_notifications_reset_preferences_json(invoke, mock_api):
    mock_api.delete("/api/v1/notifications/preferences").respond(204)
    result = invoke(["notifications", "reset-preferences", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"ok": True, "action": "reset-preferences"}


def test_notifications_reset_preferences_abort(invoke, mock_api):
    route = mock_api.delete("/api/v1/notifications/preferences").respond(204)
    result = invoke(["notifications", "reset-preferences"], input="n\n")
    assert result.exit_code != 0
    assert not route.called


SIGNALS_SETTINGS = {
    "min_score": 50,
    "searches": [
        {"saved_search_id": "s-1", "name": "Fintech hiring", "enabled": True},
        {"saved_search_id": "s-2", "name": "UK SaaS", "enabled": False},
    ],
}


def test_notifications_signals_settings(invoke, mock_api):
    mock_api.get("/api/v1/notifications/signals-settings").respond(200, json=SIGNALS_SETTINGS)
    result = invoke(["notifications", "signals-settings"])
    assert result.exit_code == 0
    assert "5/10" in result.output
    assert "Fintech hiring" in result.output
    assert "UK SaaS" in result.output


def test_notifications_signals_settings_json(invoke, mock_api):
    mock_api.get("/api/v1/notifications/signals-settings").respond(200, json=SIGNALS_SETTINGS)
    result = invoke(["notifications", "signals-settings", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == SIGNALS_SETTINGS


def test_notifications_set_signals_settings_min_score(invoke, mock_api):
    route = mock_api.put("/api/v1/notifications/signals-settings").respond(
        200, json=SIGNALS_SETTINGS
    )
    result = invoke(["notifications", "set-signals-settings", "--min-score", "60"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"min_score": 60}


def test_notifications_set_signals_settings_mute_and_unmute(invoke, mock_api):
    route = mock_api.put("/api/v1/notifications/signals-settings").respond(
        200, json=SIGNALS_SETTINGS
    )
    result = invoke(
        [
            "notifications",
            "set-signals-settings",
            "--mute-search",
            "s-1",
            "--unmute-search",
            "s-2",
            "--json",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {
        "searches": [
            {"saved_search_id": "s-1", "enabled": False},
            {"saved_search_id": "s-2", "enabled": True},
        ]
    }
    assert json.loads(result.output) == SIGNALS_SETTINGS


def test_notifications_set_signals_settings_requires_a_change(invoke, mock_api):
    result = invoke(["notifications", "set-signals-settings"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_notifications_set_signals_settings_rejects_out_of_range(invoke, mock_api):
    result = invoke(["notifications", "set-signals-settings", "--min-score", "101"])
    assert result.exit_code == 2


def test_notifications_set_signals_settings_unknown_search(invoke, mock_api):
    mock_api.put("/api/v1/notifications/signals-settings").respond(
        400, json={"detail": "Not a Signals saved search"}
    )
    result = invoke(["notifications", "set-signals-settings", "--mute-search", "x", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["status_code"] == 400
