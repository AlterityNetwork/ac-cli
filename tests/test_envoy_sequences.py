"""Tests for envoy sequences commands."""

import json

from tests.conftest import WHOAMI_RESPONSE

SAMPLE_SEQUENCE = {
    "id": "seq-1",
    "organization_id": "org-456",
    "name": "Q1 Outreach",
    "description": "Outreach to target companies",
    "status": "draft",
    "execution_mode": "manual",
    "skip_non_working_days": True,
    "writing_style_id": None,
    "playbook_id": None,
    "crm_list_id": "l1",
    "steps": [],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_sequences_list(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences").respond(200, json=[SAMPLE_SEQUENCE])
    result = invoke(["envoy", "sequences", "list"])
    assert result.exit_code == 0
    assert "Q1 Outreach" in result.output


def test_sequences_list_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences").respond(200, json=[SAMPLE_SEQUENCE])
    result = invoke(["envoy", "sequences", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "Q1 Outreach"


def test_sequences_list_with_status(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences").respond(200, json=[])
    result = invoke(["envoy", "sequences", "list", "--status", "active"])
    assert result.exit_code == 0


def test_sequences_get(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1").respond(200, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "get", "seq-1"])
    assert result.exit_code == 0
    assert "Q1 Outreach" in result.output
    assert "Skip Non-Working Days: True" in result.output


def test_sequences_get_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1").respond(200, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "get", "seq-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "seq-1"


def test_sequences_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/envoy/sequences").respond(201, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "create", "--name", "Q1 Outreach"])
    assert result.exit_code == 0
    assert "Created sequence" in result.output


def test_sequences_create_json(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/envoy/sequences").respond(201, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "create", "--name", "Q1 Outreach", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Q1 Outreach"


def test_sequences_update(invoke, mock_api):
    updated = {**SAMPLE_SEQUENCE, "name": "Updated Sequence"}
    mock_api.patch("/api/v1/envoy/sequences/seq-1").respond(200, json=updated)
    result = invoke(["envoy", "sequences", "update", "seq-1", "--name", "Updated Sequence"])
    assert result.exit_code == 0
    assert "Updated sequence" in result.output


def test_sequences_update_no_fields(invoke, mock_api):
    result = invoke(["envoy", "sequences", "update", "seq-1"])
    assert result.exit_code == 1


def test_sequences_create_skip_non_working_days(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    route = mock_api.post("/api/v1/envoy/sequences").respond(201, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "create", "--name", "Q1", "--skip-non-working-days"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["skip_non_working_days"] is True


def test_sequences_update_skip_non_working_days(invoke, mock_api):
    route = mock_api.patch("/api/v1/envoy/sequences/seq-1").respond(200, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "update", "seq-1", "--no-skip-non-working-days"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["skip_non_working_days"] is False


def test_sequences_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/envoy/sequences/seq-1").respond(204)
    result = invoke(["envoy", "sequences", "delete", "seq-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_sequences_delete_aborted(invoke, mock_api):
    result = invoke(["envoy", "sequences", "delete", "seq-1"], input="n\n")
    assert result.exit_code == 1


def test_sequences_launch(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/launch").respond(200, json={"status": "active"})
    result = invoke(["envoy", "sequences", "launch", "seq-1", "--workflow-id", "wf-1"])
    assert result.exit_code == 0
    assert "Launched" in result.output


def test_sequences_pause(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/pause").respond(200, json={"status": "paused"})
    result = invoke(["envoy", "sequences", "pause", "seq-1"])
    assert result.exit_code == 0
    assert "Paused" in result.output


def test_sequences_resume(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/resume").respond(200, json={"status": "active"})
    result = invoke(["envoy", "sequences", "resume", "seq-1", "--workflow-id", "wf-1"])
    assert result.exit_code == 0
    assert "Resumed" in result.output


def test_sequences_duplicate(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/duplicate").respond(
        201, json={"id": "seq-2", "name": "Seq Copy"}
    )
    result = invoke(["envoy", "sequences", "duplicate", "seq-1"])
    assert result.exit_code == 0
    assert "Duplicated" in result.output


def test_sequences_archive(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/archive").respond(
        200, json={"id": "seq-1", "archived_at": "2026-04-15T00:00:00Z"}
    )
    result = invoke(["envoy", "sequences", "archive", "seq-1"])
    assert result.exit_code == 0
    assert "Archived" in result.output


def test_sequences_restore(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/restore").respond(
        200, json={"id": "seq-1", "archived_at": None}
    )
    result = invoke(["envoy", "sequences", "restore", "seq-1"])
    assert result.exit_code == 0
    assert "Restored" in result.output


def test_sequences_impact_preview(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/impact-preview").respond(
        200, json={"affected_recipients": 3, "pending_drafts": 5}
    )
    result = invoke(
        [
            "envoy",
            "sequences",
            "impact-preview",
            "seq-1",
            "--step-id",
            "step-1",
            "--step-id",
            "step-2",
            "--json",
        ]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["affected_recipients"] == 3


def test_sequences_bulk_remove_recipients(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/recipients/bulk-remove").respond(
        200, json={"removed": 2}
    )
    result = invoke(
        [
            "envoy",
            "sequences",
            "bulk-remove-recipients",
            "seq-1",
            "--recipient-id",
            "r1",
            "--recipient-id",
            "r2",
        ]
    )
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_sequences_classify_step_subtype(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/classify-step-subtype").respond(
        200, json={"subtype": "manual_email"}
    )
    result = invoke(
        ["envoy", "sequences", "classify-step-subtype", "Send a manual follow-up", "--json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["subtype"] == "manual_email"


def test_sequences_outputs_list(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1/outputs").respond(
        200, json={"data": [{"id": "out-1", "step_id": "step-1"}], "total": 1}
    )
    result = invoke(["envoy", "sequences", "outputs", "seq-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["id"] == "out-1"


def test_sequences_generate_drafts(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/steps/step-1/generate-drafts").respond(
        202, json={"run_id": "run-1", "status": "queued"}
    )
    result = invoke(
        [
            "envoy",
            "sequences",
            "generate-drafts",
            "seq-1",
            "step-1",
            "--workflow-id",
            "wf-1",
        ]
    )
    assert result.exit_code == 0
    assert "queued" in result.output.lower() or "run-1" in result.output


def test_sequences_for_prospect(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/by-prospect/p-1").respond(
        200,
        json=[{"id": "s-1", "name": "Outreach", "status": "active", "execution_mode": "manual"}],
    )
    result = invoke(["envoy", "sequences", "for-prospect", "p-1"])
    assert result.exit_code == 0
    assert "Outreach" in result.output


def test_sequences_for_prospect_json(invoke, mock_api):
    import json as _json

    payload = [{"id": "s-1", "name": "Outreach", "status": "active", "execution_mode": "manual"}]
    mock_api.get("/api/v1/envoy/sequences/by-prospect/p-1").respond(200, json=payload)
    result = invoke(["envoy", "sequences", "for-prospect", "p-1", "--json"])
    assert result.exit_code == 0
    assert _json.loads(result.output) == payload


def test_sequences_for_prospect_not_found(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/by-prospect/missing").respond(404, json={"detail": "no"})
    result = invoke(["envoy", "sequences", "for-prospect", "missing"])
    assert result.exit_code == 3
