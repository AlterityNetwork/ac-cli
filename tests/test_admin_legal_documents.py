"""Tests for admin legal-docs commands."""

import json

SAMPLE_DOCS = [
    {
        "id": "doc-1",
        "document_type": "terms_of_service",
        "version": "1.0",
        "title": "Terms of Service",
        "is_current": True,
        "published_at": "2026-01-01T00:00:00Z",
    },
    {
        "id": "doc-2",
        "document_type": "privacy_policy",
        "version": "1.0",
        "title": "Privacy Policy",
        "is_current": True,
        "published_at": "2026-01-01T00:00:00Z",
    },
]

SAMPLE_DOC = {
    "id": "doc-1",
    "document_type": "terms_of_service",
    "version": "1.0",
    "title": "Terms of Service",
    "content_html": "<p>Terms content</p>",
    "is_current": True,
    "published_at": "2026-01-01T00:00:00Z",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-03-01T00:00:00Z",
}


def test_legal_docs_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/legal-documents").respond(200, json=SAMPLE_DOCS)
    result = invoke(["admin", "legal-docs", "list"])
    assert result.exit_code == 0
    assert "doc-1" in result.output


def test_legal_docs_list_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/legal-documents").respond(200, json=SAMPLE_DOCS)
    result = invoke(["admin", "legal-docs", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["title"] == "Terms of Service"


def test_legal_docs_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/legal-documents/doc-1").respond(200, json=SAMPLE_DOC)
    result = invoke(["admin", "legal-docs", "get", "doc-1"])
    assert result.exit_code == 0
    assert "Terms of Service" in result.output


def test_legal_docs_get_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/legal-documents/doc-1").respond(200, json=SAMPLE_DOC)
    result = invoke(["admin", "legal-docs", "get", "doc-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "doc-1"
    assert parsed["content_html"] == "<p>Terms content</p>"


def test_legal_docs_create(invoke, mock_api):
    mock_api.post("/api/v1/admin/legal-documents").respond(200, json=SAMPLE_DOC)
    result = invoke([
        "admin", "legal-docs", "create",
        "--document-type", "terms_of_service",
        "--version", "1.0",
        "--title", "Terms of Service",
    ])
    assert result.exit_code == 0


def test_legal_docs_create_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/legal-documents").respond(200, json=SAMPLE_DOC)
    result = invoke([
        "admin", "legal-docs", "create",
        "--document-type", "terms_of_service",
        "--version", "1.0",
        "--title", "Terms of Service",
        "--json",
    ])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "doc-1"


def test_legal_docs_update(invoke, mock_api):
    updated = {**SAMPLE_DOC, "title": "Updated Terms"}
    mock_api.patch("/api/v1/admin/legal-documents/doc-1").respond(200, json=updated)
    result = invoke(["admin", "legal-docs", "update", "doc-1", "--title", "Updated Terms"])
    assert result.exit_code == 0


def test_legal_docs_update_no_fields(invoke, mock_api):
    result = invoke(["admin", "legal-docs", "update", "doc-1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_legal_docs_delete_confirm(invoke, mock_api):
    mock_api.delete("/api/v1/admin/legal-documents/doc-1").respond(204, content=b"")
    result = invoke(["admin", "legal-docs", "delete", "doc-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_legal_docs_delete_abort(invoke, mock_api):
    result = invoke(["admin", "legal-docs", "delete", "doc-1"], input="n\n")
    assert result.exit_code == 1


def test_legal_docs_set_current(invoke, mock_api):
    mock_api.post("/api/v1/admin/legal-documents/doc-1/set-current").respond(200, json=SAMPLE_DOC)
    result = invoke(["admin", "legal-docs", "set-current", "doc-1"])
    assert result.exit_code == 0
