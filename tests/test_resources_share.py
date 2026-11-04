"""Tests for the share link commands of a vault document."""

import json
from datetime import datetime, timedelta, timezone

import pytest

URL = "https://app.example.com/share/tok-abc123"

LINK = {
    "id": "link-1",
    "resource_id": "res-1",
    "kind": "public",
    "token": "tok-abc123",
    "url": URL,
    "status": "active",
    "expires_at": None,
    "revoked_at": None,
    "open_count": 3,
    "last_opened_at": "2026-11-03T09:00:00Z",
    "parent_link_id": None,
    "communication_id": None,
    "crm_person_id": None,
    "crm_person_name": None,
    "created_at": "2026-11-01T10:00:00Z",
}

RECIPIENT_LINK = dict(
    LINK,
    id="link-2",
    kind="recipient",
    token="tok-r",
    url="https://app.example.com/share/tok-r",
    open_count=1,
    parent_link_id="link-1",
    communication_id="comm-1",
    crm_person_id="person-1",
    crm_person_name="Ada Lovelace",
)

LINKS = {"data": [RECIPIENT_LINK, LINK], "total": 2, "limit": 50, "offset": 0, "has_more": False}

OPENS = {
    "data": [
        {
            "id": "open-1",
            "opened_at": "2026-11-03T09:00:00Z",
            "kind": "download",
            "user_agent": "Mozilla/5.0",
        },
        {
            "id": "open-2",
            "opened_at": "2026-11-02T08:00:00Z",
            "kind": "view",
            "user_agent": "curl/8.0",
        },
    ],
    "total": 2,
    "limit": 50,
    "offset": 0,
    "has_more": False,
}

NOT_FOUND = {"detail": "Not found"}


def _body(route) -> dict:
    return json.loads(route.calls.last.request.content)


def _assert_days_from_now(value: str, days: int) -> None:
    expires = datetime.fromisoformat(value)
    assert expires.tzinfo is not None
    expected = datetime.now(timezone.utc) + timedelta(days=days)
    assert abs((expires - expected).total_seconds()) < 60


# create


def test_share_create_prints_the_url(invoke, mock_api):
    route = mock_api.post("/api/v1/resources/res-1/share-links").respond(200, json=LINK)
    result = invoke(["resources", "share", "create", "res-1"])
    assert result.exit_code == 0
    assert URL in result.output
    assert "active" in result.output
    assert _body(route) == {"expires_at": None}


def test_share_create_with_expiry(invoke, mock_api):
    route = mock_api.post("/api/v1/resources/res-1/share-links").respond(
        200, json=dict(LINK, expires_at="2026-12-04T10:00:00Z")
    )
    result = invoke(["resources", "share", "create", "res-1", "--expires-in-days", "30"])
    assert result.exit_code == 0
    _assert_days_from_now(_body(route)["expires_at"], 30)
    assert "2026-12-04T10:00:00Z" in result.output


def test_share_create_json(invoke, mock_api):
    mock_api.post("/api/v1/resources/res-1/share-links").respond(200, json=LINK)
    result = invoke(["resources", "share", "create", "res-1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["url"] == URL


def test_share_create_shows_an_expired_link(invoke, mock_api):
    """The API returns an existing link unchanged, so its status must show."""
    mock_api.post("/api/v1/resources/res-1/share-links").respond(
        200, json=dict(LINK, status="expired", expires_at="2026-10-01T00:00:00Z")
    )
    result = invoke(["resources", "share", "create", "res-1", "--expires-in-days", "7"])
    assert result.exit_code == 0
    assert "expired" in result.output
    assert "share update" in result.output


def test_share_create_not_found(invoke, mock_api):
    mock_api.post("/api/v1/resources/res-9/share-links").respond(404, json=NOT_FOUND)
    result = invoke(["resources", "share", "create", "res-9"])
    assert result.exit_code == 3


def test_share_create_not_found_json(invoke, mock_api):
    mock_api.post("/api/v1/resources/res-9/share-links").respond(404, json=NOT_FOUND)
    result = invoke(["resources", "share", "create", "res-9", "--json"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["status_code"] == 404


@pytest.mark.parametrize("days", ["0", "-3"])
def test_share_create_refuses_a_day_count_below_one(invoke, mock_api, days):
    route = mock_api.post("/api/v1/resources/res-1/share-links").respond(200, json=LINK)
    result = invoke(["resources", "share", "create", "res-1", "--expires-in-days", days, "--json"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] is True
    assert not route.called


# list


def test_share_list(invoke, mock_api, table_column):
    route = mock_api.get("/api/v1/resources/res-1/share-links").respond(200, json=LINKS)
    result = invoke(["resources", "share", "list", "res-1"])
    assert result.exit_code == 0
    assert "2 total" in result.output
    assert "recipient" in result.output
    assert table_column(result.output, 5) == "AdaLovelace"
    assert table_column(result.output, 0) == "link-2link-1"
    assert table_column(result.output, 6) == RECIPIENT_LINK["url"] + URL
    assert route.calls.last.request.url.params["limit"] == "50"
    assert route.calls.last.request.url.params["offset"] == "0"


def test_share_list_pagination(invoke, mock_api):
    route = mock_api.get("/api/v1/resources/res-1/share-links").respond(200, json=LINKS)
    result = invoke(["resources", "share", "list", "res-1", "--limit", "10", "--offset", "20"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params["limit"] == "10"
    assert route.calls.last.request.url.params["offset"] == "20"


def test_share_list_json(invoke, mock_api):
    mock_api.get("/api/v1/resources/res-1/share-links").respond(200, json=LINKS)
    result = invoke(["resources", "share", "list", "res-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["crm_person_name"] == "Ada Lovelace"


def test_share_list_empty(invoke, mock_api):
    mock_api.get("/api/v1/resources/res-1/share-links").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["resources", "share", "list", "res-1"])
    assert result.exit_code == 0
    assert "No share links" in result.output


def test_share_list_not_found(invoke, mock_api):
    mock_api.get("/api/v1/resources/res-9/share-links").respond(404, json=NOT_FOUND)
    result = invoke(["resources", "share", "list", "res-9"])
    assert result.exit_code == 3


# update


def test_share_update_sets_an_expiry(invoke, mock_api):
    route = mock_api.patch("/api/v1/resources/share-links/link-1").respond(
        200, json=dict(LINK, expires_at="2026-11-11T10:00:00Z")
    )
    result = invoke(["resources", "share", "update", "link-1", "--expires-in-days", "7"])
    assert result.exit_code == 0
    _assert_days_from_now(_body(route)["expires_at"], 7)
    assert "2026-11-11T10:00:00Z" in result.output


def test_share_update_clears_the_expiry(invoke, mock_api):
    route = mock_api.patch("/api/v1/resources/share-links/link-1").respond(200, json=LINK)
    result = invoke(["resources", "share", "update", "link-1", "--no-expiry"])
    assert result.exit_code == 0
    assert _body(route) == {"expires_at": None}
    assert "never" in result.output


def test_share_update_json(invoke, mock_api):
    mock_api.patch("/api/v1/resources/share-links/link-1").respond(200, json=LINK)
    result = invoke(["resources", "share", "update", "link-1", "--no-expiry", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == "link-1"


@pytest.mark.parametrize(
    "flags",
    [[], ["--expires-in-days", "7", "--no-expiry"], ["--expires-in-days", "0"]],
)
def test_share_update_refuses_a_bad_flag_set(invoke, mock_api, flags):
    route = mock_api.patch("/api/v1/resources/share-links/link-1").respond(200, json=LINK)
    result = invoke(["resources", "share", "update", "link-1", *flags])
    assert result.exit_code == 2
    assert "Invalid option" in result.output
    assert not route.called


def test_share_update_refusal_json(invoke, mock_api):
    result = invoke(["resources", "share", "update", "link-1", "--json"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert "--no-expiry" in parsed["detail"]


def test_share_update_not_found(invoke, mock_api):
    mock_api.patch("/api/v1/resources/share-links/link-9").respond(404, json=NOT_FOUND)
    result = invoke(["resources", "share", "update", "link-9", "--no-expiry", "--json"])
    assert result.exit_code == 3
    assert json.loads(result.output)["status_code"] == 404


# revoke


def test_share_revoke_yes(invoke, mock_api):
    route = mock_api.post("/api/v1/resources/share-links/link-1/revoke").respond(
        200, json=dict(LINK, status="revoked", revoked_at="2026-11-04T10:00:00Z")
    )
    result = invoke(["resources", "share", "revoke", "link-1", "--yes"])
    assert result.exit_code == 0
    assert route.called
    assert "Revoked" in result.output


def test_share_revoke_json(invoke, mock_api):
    mock_api.post("/api/v1/resources/share-links/link-1/revoke").respond(
        200, json=dict(LINK, status="revoked")
    )
    result = invoke(["resources", "share", "revoke", "link-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "revoked"


def test_share_revoke_abort(invoke, mock_api):
    route = mock_api.post("/api/v1/resources/share-links/link-1/revoke").respond(200, json=LINK)
    result = invoke(["resources", "share", "revoke", "link-1"], input="n\n")
    assert result.exit_code == 1
    assert not route.called


def test_share_revoke_env_yes(invoke, mock_api, monkeypatch):
    monkeypatch.setenv("AC_YES", "1")
    route = mock_api.post("/api/v1/resources/share-links/link-1/revoke").respond(
        200, json=dict(LINK, status="revoked")
    )
    result = invoke(["resources", "share", "revoke", "link-1"])
    assert result.exit_code == 0
    assert route.called


def test_share_revoke_not_found(invoke, mock_api):
    mock_api.post("/api/v1/resources/share-links/link-9/revoke").respond(404, json=NOT_FOUND)
    result = invoke(["resources", "share", "revoke", "link-9", "--yes"])
    assert result.exit_code == 3


# opens


def test_share_opens(invoke, mock_api):
    route = mock_api.get("/api/v1/resources/share-links/link-1/opens").respond(200, json=OPENS)
    result = invoke(["resources", "share", "opens", "link-1"])
    assert result.exit_code == 0
    assert "2 total" in result.output
    assert "download" in result.output
    assert "curl/8.0" in result.output
    assert route.calls.last.request.url.params["limit"] == "50"
    assert route.calls.last.request.url.params["offset"] == "0"


def test_share_opens_pagination(invoke, mock_api):
    route = mock_api.get("/api/v1/resources/share-links/link-1/opens").respond(200, json=OPENS)
    result = invoke(["resources", "share", "opens", "link-1", "--limit", "5", "--offset", "10"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params["limit"] == "5"
    assert route.calls.last.request.url.params["offset"] == "10"


def test_share_opens_json(invoke, mock_api):
    mock_api.get("/api/v1/resources/share-links/link-1/opens").respond(200, json=OPENS)
    result = invoke(["resources", "share", "opens", "link-1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["data"][0]["kind"] == "download"


def test_share_opens_empty(invoke, mock_api):
    mock_api.get("/api/v1/resources/share-links/link-1/opens").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["resources", "share", "opens", "link-1"])
    assert result.exit_code == 0
    assert "No opens" in result.output


def test_share_opens_not_found(invoke, mock_api):
    mock_api.get("/api/v1/resources/share-links/link-9/opens").respond(404, json=NOT_FOUND)
    result = invoke(["resources", "share", "opens", "link-9", "--json"])
    assert result.exit_code == 3
    assert json.loads(result.output)["status_code"] == 404
