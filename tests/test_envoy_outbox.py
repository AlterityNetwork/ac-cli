"""Tests for envoy outbox commands."""

import json


SAMPLE_PENDING = {
    "id": "draft-1",
    "recipient_name": "Jane Doe",
    "subject": "Partnership opportunity",
    "body": "Hi Jane...",
    "sequence_name": "Q1 Outreach",
    "step_order": 1,
}

SAMPLE_SENT = {
    "id": "sent-1",
    "recipient_name": "Jane Doe",
    "subject": "Partnership opportunity",
    "status": "delivered",
    "sent_at": "2026-03-10T10:00:00Z",
}


def test_outbox_pending(invoke, mock_api):
    mock_api.get("/api/v1/envoy/outbox/pending").respond(
        200, json={"data": [SAMPLE_PENDING], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "pending"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output
    assert "Partnership" in result.output
    assert "1 total" in result.output


def test_outbox_pending_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/outbox/pending").respond(
        200, json={"data": [SAMPLE_PENDING], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "pending", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["id"] == "draft-1"


def test_outbox_pending_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/envoy/outbox/pending").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "pending", "--sequence-id", "seq-1", "--step-id", "step-1"])
    assert result.exit_code == 0


def test_outbox_pending_with_offset(invoke, mock_api):
    route = mock_api.get("/api/v1/envoy/outbox/pending").respond(
        200, json={"data": [SAMPLE_PENDING], "total": 11, "limit": 50, "offset": 10, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "pending", "--offset", "10"])
    assert result.exit_code == 0
    assert "11 total" in result.output
    req = route.calls[0].request
    assert "offset=10" in str(req.url)


def test_outbox_sent(invoke, mock_api):
    mock_api.get("/api/v1/envoy/outbox/sent").respond(
        200, json={"data": [SAMPLE_SENT], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "sent"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output
    assert "1 total" in result.output


def test_outbox_sent_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/outbox/sent").respond(
        200, json={"data": [SAMPLE_SENT], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "sent", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["status"] == "delivered"


def test_outbox_sent_with_offset(invoke, mock_api):
    route = mock_api.get("/api/v1/envoy/outbox/sent").respond(
        200, json={"data": [SAMPLE_SENT], "total": 20, "limit": 50, "offset": 5, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "sent", "--offset", "5"])
    assert result.exit_code == 0
    assert "20 total" in result.output
    req = route.calls[0].request
    assert "offset=5" in str(req.url)


def test_outbox_step_drafts(invoke, mock_api):
    mock_api.get("/api/v1/envoy/outbox/step-drafts").respond(
        200, json={"data": [SAMPLE_PENDING], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "step-drafts", "--sequence-id", "seq-1", "--step-id", "step-1"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output
    assert "1 total" in result.output


def test_outbox_step_drafts_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/outbox/step-drafts").respond(
        200, json={"data": [SAMPLE_PENDING], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "step-drafts", "--sequence-id", "seq-1", "--step-id", "step-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["id"] == "draft-1"


def test_outbox_step_drafts_with_offset(invoke, mock_api):
    route = mock_api.get("/api/v1/envoy/outbox/step-drafts").respond(
        200, json={"data": [SAMPLE_PENDING], "total": 15, "limit": 50, "offset": 5, "has_more": False}
    )
    result = invoke(["envoy", "outbox", "step-drafts", "--sequence-id", "seq-1", "--step-id", "step-1", "--offset", "5"])
    assert result.exit_code == 0
    assert "15 total" in result.output
    req = route.calls[0].request
    assert "offset=5" in str(req.url)


def test_outbox_update_draft(invoke, mock_api):
    updated = {**SAMPLE_PENDING, "subject": "New subject"}
    mock_api.patch("/api/v1/envoy/outbox/pending/draft-1").respond(200, json=updated)
    result = invoke(["envoy", "outbox", "update-draft", "draft-1", "--subject", "New subject"])
    assert result.exit_code == 0
    assert "Updated draft" in result.output


def test_outbox_update_draft_no_fields(invoke, mock_api):
    result = invoke(["envoy", "outbox", "update-draft", "draft-1"])
    assert result.exit_code == 1


def test_outbox_approve(invoke, mock_api):
    mock_api.post("/api/v1/envoy/outbox/pending/draft-1/approve").respond(200, json={"sent": True})
    result = invoke(["envoy", "outbox", "approve", "draft-1"])
    assert result.exit_code == 0
    assert "Approved" in result.output


def test_outbox_approve_json(invoke, mock_api):
    mock_api.post("/api/v1/envoy/outbox/pending/draft-1/approve").respond(200, json={"sent": True})
    result = invoke(["envoy", "outbox", "approve", "draft-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["sent"] is True


def test_outbox_reject(invoke, mock_api):
    mock_api.post("/api/v1/envoy/outbox/pending/draft-1/reject").respond(200, json={"rejected": True})
    result = invoke(["envoy", "outbox", "reject", "draft-1", "--action", "regenerate_draft", "--reason", "Too formal"])
    assert result.exit_code == 0
    assert "Rejected" in result.output
    assert "regenerate_draft" in result.output


def test_outbox_reject_json(invoke, mock_api):
    mock_api.post("/api/v1/envoy/outbox/pending/draft-1/reject").respond(200, json={"rejected": True})
    result = invoke(["envoy", "outbox", "reject", "draft-1", "--action", "remove_recipient", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["rejected"] is True


def test_outbox_regenerate(invoke, mock_api):
    mock_api.post("/api/v1/envoy/outbox/pending/draft-1/regenerate").respond(200, json={"regenerated": True})
    result = invoke(["envoy", "outbox", "regenerate", "draft-1", "--instruction", "Make it shorter"])
    assert result.exit_code == 0
    assert "Regenerated" in result.output


def test_outbox_regenerate_json(invoke, mock_api):
    mock_api.post("/api/v1/envoy/outbox/pending/draft-1/regenerate").respond(200, json={"regenerated": True})
    result = invoke(["envoy", "outbox", "regenerate", "draft-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["regenerated"] is True
