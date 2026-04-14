"""Tests for network commands: referrals, news, slack invites."""

import json


SAMPLE_REFERRAL = {"id": "ref-1", "company_name": "Acme Corp", "status": "pending", "created_at": "2026-01-01"}
SAMPLE_NEWS = {"id": "news-1", "title": "Q1 Update", "created_at": "2026-01-01"}


# -- Referrals -----------------------------------------------------------------


def test_referrals_list(invoke, mock_api):
    mock_api.get("/api/v1/network/referrals").respond(200, json=[SAMPLE_REFERRAL])
    result = invoke(["network", "referrals", "list"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output


def test_referrals_list_json(invoke, mock_api):
    mock_api.get("/api/v1/network/referrals").respond(200, json=[SAMPLE_REFERRAL])
    result = invoke(["network", "referrals", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)


def test_referrals_get(invoke, mock_api):
    mock_api.get("/api/v1/network/referrals/ref-1").respond(200, json=SAMPLE_REFERRAL)
    result = invoke(["network", "referrals", "get", "ref-1"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output


def test_referrals_get_json(invoke, mock_api):
    mock_api.get("/api/v1/network/referrals/ref-1").respond(200, json=SAMPLE_REFERRAL)
    result = invoke(["network", "referrals", "get", "ref-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "ref-1"


def test_referrals_create(invoke, mock_api):
    mock_api.post("/api/v1/network/referrals").respond(201, json={"id": "ref-2", "company_name": "NewCo"})
    result = invoke(["network", "referrals", "create", "--company-name", "NewCo"])
    assert result.exit_code == 0
    assert "Created" in result.output


def test_referrals_create_json(invoke, mock_api):
    mock_api.post("/api/v1/network/referrals").respond(201, json={"id": "ref-2"})
    result = invoke(["network", "referrals", "create", "--company-name", "NewCo", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "ref-2"


def test_referrals_update(invoke, mock_api):
    mock_api.patch("/api/v1/network/referrals/ref-1").respond(200, json={**SAMPLE_REFERRAL, "status": "claimed"})
    result = invoke(["network", "referrals", "update", "ref-1", "--status", "claimed"])
    assert result.exit_code == 0
    assert "Updated" in result.output


def test_referrals_update_no_fields(invoke, mock_api):
    result = invoke(["network", "referrals", "update", "ref-1"])
    assert result.exit_code == 1


def test_referrals_delete(invoke, mock_api):
    mock_api.delete("/api/v1/network/referrals/ref-1").respond(204)
    result = invoke(["network", "referrals", "delete", "ref-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_referrals_delete_abort(invoke, mock_api):
    result = invoke(["network", "referrals", "delete", "ref-1"], input="n\n")
    assert result.exit_code != 0


def test_referrals_view(invoke, mock_api):
    mock_api.post("/api/v1/network/referrals/ref-1/view").respond(200, json={"views": 5})
    result = invoke(["network", "referrals", "view", "ref-1"])
    assert result.exit_code == 0


def test_referrals_claim(invoke, mock_api):
    mock_api.post("/api/v1/network/referrals/ref-1/claim").respond(200, json={"status": "claimed"})
    result = invoke(["network", "referrals", "claim", "ref-1"])
    assert result.exit_code == 0
    assert "Claimed" in result.output


def test_referrals_404(invoke, mock_api):
    mock_api.get("/api/v1/network/referrals/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["network", "referrals", "get", "bad"])
    assert result.exit_code == 3


# -- News ----------------------------------------------------------------------


def test_news_list(invoke, mock_api):
    mock_api.get("/api/v1/network/news").respond(200, json=[SAMPLE_NEWS])
    result = invoke(["network", "news", "list"])
    assert result.exit_code == 0
    assert "Q1 Update" in result.output


def test_news_list_json(invoke, mock_api):
    mock_api.get("/api/v1/network/news").respond(200, json=[SAMPLE_NEWS])
    result = invoke(["network", "news", "list", "--json"])
    assert result.exit_code == 0
    json.loads(result.output)


def test_news_create(invoke, mock_api):
    mock_api.post("/api/v1/network/news").respond(201, json={"id": "news-2", "title": "New Post"})
    result = invoke(["network", "news", "create", "--title", "New Post", "--content", "Body text"])
    assert result.exit_code == 0
    assert "Created" in result.output


def test_news_create_json(invoke, mock_api):
    mock_api.post("/api/v1/network/news").respond(201, json={"id": "news-2"})
    result = invoke(["network", "news", "create", "--title", "New Post", "--content", "Body", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "news-2"


def test_news_update(invoke, mock_api):
    mock_api.patch("/api/v1/network/news/news-1").respond(200, json={**SAMPLE_NEWS, "title": "Updated"})
    result = invoke(["network", "news", "update", "news-1", "--title", "Updated"])
    assert result.exit_code == 0


def test_news_update_no_fields(invoke, mock_api):
    result = invoke(["network", "news", "update", "news-1"])
    assert result.exit_code == 1


def test_news_delete(invoke, mock_api):
    mock_api.delete("/api/v1/network/news/news-1").respond(204)
    result = invoke(["network", "news", "delete", "news-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


# -- Slack Invites -------------------------------------------------------------


def test_slack_status(invoke, mock_api):
    mock_api.get("/api/v1/network/slack-invites/status").respond(200, json={"status": "pending", "requested_at": "2026-01-01"})
    result = invoke(["network", "slack-invites", "status"])
    assert result.exit_code == 0
    assert "pending" in result.output.lower()


def test_slack_status_json(invoke, mock_api):
    mock_api.get("/api/v1/network/slack-invites/status").respond(200, json={"status": "pending"})
    result = invoke(["network", "slack-invites", "status", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "pending"


def test_slack_request(invoke, mock_api):
    mock_api.post("/api/v1/network/slack-invites").respond(200, json={"status": "requested"})
    result = invoke(["network", "slack-invites", "request"])
    assert result.exit_code == 0
    assert "requested" in result.output.lower()


def test_slack_request_json(invoke, mock_api):
    mock_api.post("/api/v1/network/slack-invites").respond(200, json={"status": "requested"})
    result = invoke(["network", "slack-invites", "request", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "requested"
