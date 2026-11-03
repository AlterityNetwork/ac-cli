"""Tests for resources commands."""

import json

SAMPLE_RESOURCES = {
    "data": [
        {
            "id": "res-1",
            "source_name": "Product Guide",
            "status": "completed",
            "created_at": "2026-03-20T10:00:00Z",
        },
        {
            "id": "res-2",
            "source_name": "FAQ Document",
            "status": "processing",
            "created_at": "2026-03-19T08:00:00Z",
        },
    ],
    "total": 2,
}

SAMPLE_UPLOAD = {
    "id": "res-3",
    "source_name": "New Resource",
}

SAMPLE_STATUS = {
    "id": "res-1",
    "status": "completed",
    "chunk_count": 42,
    "error_message": None,
    "source_description": "A summary of the document.",
    "image_url": "https://r2/thumb.png",
}


def test_resources_list(invoke, mock_api):
    mock_api.get("/api/v1/resources").respond(200, json=SAMPLE_RESOURCES)
    result = invoke(["resources", "list"])
    assert result.exit_code == 0
    assert "Product Guide" in result.output


def test_resources_list_json(invoke, mock_api):
    mock_api.get("/api/v1/resources").respond(200, json=SAMPLE_RESOURCES)
    result = invoke(["resources", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed["data"]) == 2


def test_resources_upload(invoke, mock_api, tmp_path):
    mock_api.post("/api/v1/resources/upload").respond(200, json=SAMPLE_UPLOAD)
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"%PDF-1.4 fake pdf content")
    result = invoke(["resources", "upload", str(test_file), "--name", "Test PDF"])
    assert result.exit_code == 0


def test_resources_upload_bad_extension(invoke, tmp_path):
    test_file = tmp_path / "malware.exe"
    test_file.write_bytes(b"bad content")
    result = invoke(["resources", "upload", str(test_file), "--name", "Bad File"])
    assert result.exit_code == 1
    assert "Unsupported" in result.output


def test_resources_delete_confirm(invoke, mock_api):
    mock_api.delete("/api/v1/resources/res-1").respond(204, content=b"")
    result = invoke(["resources", "delete", "res-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_resources_delete_abort(invoke, mock_api):
    result = invoke(["resources", "delete", "res-1"], input="n\n")
    assert result.exit_code == 1


def test_resources_status(invoke, mock_api):
    mock_api.get("/api/v1/resources/res-1/status").respond(200, json=SAMPLE_STATUS)
    result = invoke(["resources", "status", "res-1"])
    assert result.exit_code == 0
    assert "completed" in result.output
    assert "42" in result.output
    assert "A summary of the document." in result.output
    assert "Thumbnail: https://r2/thumb.png" in result.output


def test_resources_status_json(invoke, mock_api):
    mock_api.get("/api/v1/resources/res-1/status").respond(200, json=SAMPLE_STATUS)
    result = invoke(["resources", "status", "res-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["chunk_count"] == 42
    assert parsed["source_description"] == "A summary of the document."
    assert parsed["image_url"] == "https://r2/thumb.png"


def test_resources_status_without_a_description(invoke, mock_api):
    """A row with no description still prints the Description label."""
    payload = dict(SAMPLE_STATUS, source_description=None)
    mock_api.get("/api/v1/resources/res-1/status").respond(200, json=payload)
    result = invoke(["resources", "status", "res-1"])
    assert result.exit_code == 0
    assert "Description:" in result.output
    assert "None" not in result.output


IN_USE = {
    "error": True,
    "message": "This document is attached to offers or sequence steps.",
    "type": "ConflictError",
    "code": "resource_in_use",
    "context": {
        "code": "resource_in_use",
        "offers": [{"id": "pb-1", "name": "Spring [promo] offer"}],
        "steps": [
            {
                "id": "step-1",
                "sequence_id": "seq-1",
                "sequence_name": "Founders",
                "step_name": "Intro email",
            }
        ],
    },
}


def test_resources_list_help_names_the_organisation():
    from typer.testing import CliRunner

    from ac_cli.main import app

    result = CliRunner().invoke(app, ["resources", "list", "--help"])
    assert "organisation" in result.output


def test_resources_list_sends_no_scope(invoke, mock_api):
    route = mock_api.get("/api/v1/resources").respond(200, json=SAMPLE_RESOURCES)
    result = invoke(["resources", "list", "--json"])
    assert result.exit_code == 0
    assert "scope" not in route.calls.last.request.url.params


def test_resources_list_has_no_scope_option(invoke, mock_api):
    result = invoke(["resources", "list", "--scope", "organization"])
    assert result.exit_code == 2


def test_resources_delete_without_force_sends_no_force(invoke, mock_api):
    route = mock_api.delete("/api/v1/resources/res-1").respond(204, content=b"")
    result = invoke(["resources", "delete", "res-1", "--yes"])
    assert result.exit_code == 0
    assert "force" not in route.calls.last.request.url.params


def test_resources_delete_force(invoke, mock_api):
    route = mock_api.delete("/api/v1/resources/res-1").respond(204, content=b"")
    result = invoke(["resources", "delete", "res-1", "--force", "--yes", "--json"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params["force"] == "true"
    assert json.loads(result.output) == {"deleted": True, "id": "res-1"}


def test_resources_delete_in_use_lists_the_offers_and_steps(invoke, mock_api):
    mock_api.delete("/api/v1/resources/res-1").respond(409, json=IN_USE)
    result = invoke(["resources", "delete", "res-1", "--yes"])
    assert result.exit_code == 5
    assert "Spring [promo] offer" in result.output
    assert "Founders" in result.output
    assert "Intro email" in result.output
    assert "--force" in result.output


def test_resources_delete_in_use_json(invoke, mock_api):
    mock_api.delete("/api/v1/resources/res-1").respond(409, json=IN_USE)
    result = invoke(["resources", "delete", "res-1", "--yes", "--json"])
    assert result.exit_code == 5
    parsed = json.loads(result.output)
    assert parsed["status_code"] == 409
    assert parsed["context"]["offers"][0]["id"] == "pb-1"
    assert parsed["context"]["steps"][0]["sequence_id"] == "seq-1"


def test_resources_delete_other_conflict_uses_the_standard_error(invoke, mock_api):
    mock_api.delete("/api/v1/resources/res-1").respond(409, json={"detail": "Busy"})
    result = invoke(["resources", "delete", "res-1", "--yes"])
    assert result.exit_code == 5
    assert "Busy" in result.output
    assert "--force" not in result.output


def test_resources_delete_not_found(invoke, mock_api):
    mock_api.delete("/api/v1/resources/res-9").respond(404, json={"detail": "Not found"})
    result = invoke(["resources", "delete", "res-9", "--yes"])
    assert result.exit_code == 3


def test_resources_delete_env_yes(invoke, mock_api, monkeypatch):
    monkeypatch.setenv("AC_YES", "1")
    mock_api.delete("/api/v1/resources/res-1").respond(204, content=b"")
    result = invoke(["resources", "delete", "res-1"])
    assert result.exit_code == 0
