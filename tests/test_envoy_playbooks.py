"""Tests for envoy playbooks commands."""

import json

SAMPLE_PLAYBOOK = {
    "id": "pb-1",
    "name": "Spring offer",
    "icp": "Series A SaaS founders",
    "offer": "Free pipeline audit",
    "cta": "Book a call",
    "cta_link": "https://example.com/book",
    "example_emails": [],
    "icp_ids": [],
    "document_ids": ["res-1", "res-2"],
    "created_at": "2026-01-01T00:00:00Z",
}


def _page(*rows):
    return {"data": list(rows), "total": len(rows), "limit": 50, "offset": 0, "has_more": False}


def test_playbooks_list(invoke, mock_api, table_column):
    mock_api.get("/api/v1/playbooks").respond(200, json=_page(SAMPLE_PLAYBOOK))
    result = invoke(["envoy", "playbooks", "list"])
    assert result.exit_code == 0
    assert "Spring offer" in table_column(result.output, 0)
    assert "Free pipeline audit" in table_column(result.output, 1)
    assert "Book a call" in table_column(result.output, 2)
    assert table_column(result.output, 3) == "2"


def test_playbooks_list_without_documents(invoke, mock_api, table_column):
    row = {key: value for key, value in SAMPLE_PLAYBOOK.items() if key != "document_ids"}
    mock_api.get("/api/v1/playbooks").respond(200, json=_page(row))
    result = invoke(["envoy", "playbooks", "list"])
    assert result.exit_code == 0
    assert table_column(result.output, 3) == "0"


def test_playbooks_list_json(invoke, mock_api):
    mock_api.get("/api/v1/playbooks").respond(200, json=_page(SAMPLE_PLAYBOOK))
    result = invoke(["envoy", "playbooks", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["document_ids"] == ["res-1", "res-2"]


def test_playbooks_get(invoke, mock_api):
    mock_api.get("/api/v1/playbooks/pb-1").respond(200, json=SAMPLE_PLAYBOOK)
    result = invoke(["envoy", "playbooks", "get", "pb-1"])
    assert result.exit_code == 0
    for value in (
        "Spring offer",
        "Series A SaaS founders",
        "Free pipeline audit",
        "Book a call",
        "https://example.com/book",
        "res-1, res-2",
    ):
        assert value in result.output


def test_playbooks_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/playbooks/pb-999").respond(404, json={"detail": "Not found"})
    result = invoke(["envoy", "playbooks", "get", "pb-999"])
    assert result.exit_code == 3


def test_playbooks_create(invoke, mock_api):
    route = mock_api.post("/api/v1/playbooks").respond(201, json=SAMPLE_PLAYBOOK)
    result = invoke(
        [
            "envoy",
            "playbooks",
            "create",
            "--name",
            "Spring offer",
            "--icp",
            "Series A SaaS founders",
            "--offer",
            "Free pipeline audit",
            "--cta",
            "Book a call",
            "--cta-link",
            "https://example.com/book",
            "--document",
            "res-1",
            "--document",
            "res-2",
        ]
    )
    assert result.exit_code == 0
    assert "Created playbook" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "name": "Spring offer",
        "icp": "Series A SaaS founders",
        "offer": "Free pipeline audit",
        "cta": "Book a call",
        "cta_link": "https://example.com/book",
        "document_ids": ["res-1", "res-2"],
    }


def test_playbooks_create_json(invoke, mock_api):
    mock_api.post("/api/v1/playbooks").respond(201, json=SAMPLE_PLAYBOOK)
    result = invoke(["envoy", "playbooks", "create", "--name", "Spring offer", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Spring offer"


def test_playbooks_create_refuses_the_removed_flags(invoke, mock_api):
    for flag in ("--description", "--status", "--competitor-name"):
        result = invoke(["envoy", "playbooks", "create", "--name", "X", flag, "y"])
        assert result.exit_code == 2


def test_playbooks_create_unknown_document(invoke, mock_api):
    mock_api.post("/api/v1/playbooks").respond(
        400,
        json={"error": True, "message": "Document not found", "type": "ValidationError"},
    )
    result = invoke(
        ["envoy", "playbooks", "create", "--name", "X", "--document", "res-9", "--json"]
    )
    assert result.exit_code == 1
    assert json.loads(result.output)["detail"] == "Document not found"


def test_playbooks_create_sends_icp_ids(invoke, mock_api):
    route = mock_api.post("/api/v1/playbooks").respond(201, json=SAMPLE_PLAYBOOK)
    result = invoke(
        [
            "envoy",
            "playbooks",
            "create",
            "--name",
            "Spring offer",
            "--icp-id",
            "icp-1",
            "--icp-id",
            "icp-2",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["icp_ids"] == ["icp-1", "icp-2"]
    assert "document_ids" not in body


def test_playbooks_update_sends_icp_ids(invoke, mock_api):
    route = mock_api.patch("/api/v1/playbooks/pb-1").respond(200, json=SAMPLE_PLAYBOOK)
    result = invoke(["envoy", "playbooks", "update", "pb-1", "--icp-id", "icp-1"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"icp_ids": ["icp-1"]}


def test_playbooks_update(invoke, mock_api):
    updated = {**SAMPLE_PLAYBOOK, "name": "Updated Playbook"}
    route = mock_api.patch("/api/v1/playbooks/pb-1").respond(200, json=updated)
    result = invoke(
        ["envoy", "playbooks", "update", "pb-1", "--name", "Updated Playbook", "--offer", "New"]
    )
    assert result.exit_code == 0
    assert "Updated playbook" in result.output
    assert json.loads(route.calls.last.request.content) == {
        "name": "Updated Playbook",
        "offer": "New",
    }


def test_playbooks_update_documents(invoke, mock_api):
    route = mock_api.patch("/api/v1/playbooks/pb-1").respond(200, json=SAMPLE_PLAYBOOK)
    result = invoke(["envoy", "playbooks", "update", "pb-1", "--document", "res-3"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"document_ids": ["res-3"]}


def test_playbooks_update_clears_documents(invoke, mock_api):
    route = mock_api.patch("/api/v1/playbooks/pb-1").respond(
        200, json={**SAMPLE_PLAYBOOK, "document_ids": []}
    )
    result = invoke(["envoy", "playbooks", "update", "pb-1", "--clear-documents", "--json"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"document_ids": []}
    assert json.loads(result.output)["document_ids"] == []


def test_playbooks_update_document_and_clear_is_refused(invoke, mock_api):
    route = mock_api.patch("/api/v1/playbooks/pb-1")
    result = invoke(
        [
            "envoy",
            "playbooks",
            "update",
            "pb-1",
            "--document",
            "res-1",
            "--clear-documents",
            "--json",
        ]
    )
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] is True
    assert not route.called


def test_playbooks_update_no_fields(invoke, mock_api):
    result = invoke(["envoy", "playbooks", "update", "pb-1"])
    assert result.exit_code == 1


def test_playbooks_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/playbooks/pb-1").respond(204)
    result = invoke(["envoy", "playbooks", "delete", "pb-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_playbooks_delete_aborted(invoke, mock_api):
    result = invoke(["envoy", "playbooks", "delete", "pb-1"], input="n\n")
    assert result.exit_code == 1


def test_playbooks_duplicate(invoke, mock_api):
    duplicated = {**SAMPLE_PLAYBOOK, "id": "pb-2", "name": "Spring offer (Copy)"}
    mock_api.post("/api/v1/playbooks/pb-1/duplicate").respond(201, json=duplicated)
    result = invoke(["envoy", "playbooks", "duplicate", "pb-1"])
    assert result.exit_code == 0
    assert "Duplicated playbook" in result.output
