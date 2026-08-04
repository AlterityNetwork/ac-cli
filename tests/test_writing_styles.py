"""Tests for writing styles commands.

Response fixtures mirror `ac-python-api` `WritingStyle` /
`WritingStyleListResponse` exactly. The previous fixtures invented a
`{name, description, tone, formality, status}` shape the API never returned,
so every command was asserted against a schema that does not exist and the
drift stayed green.
"""

import json

SAMPLE_STYLE = {
    "id": "ws-1",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "user_id": "user-123",
    "organization_id": "org-456",
    "style_name": "Professional",
    "style_prompt": "Write in a professional, friendly tone.",
    "is_active": True,
    "is_default": True,
    "training_examples": [],
    "training_iterations": 0,
    "last_trained_at": None,
    "style_attributes": {},
}

STYLE_LIST = {"styles": [SAMPLE_STYLE], "default_style_id": "ws-1", "total_count": 1}


def test_styles_list(invoke, mock_api):
    mock_api.get("/api/v1/writing-styles").respond(200, json=STYLE_LIST)
    result = invoke(["styles", "list"])
    assert result.exit_code == 0
    assert "Professional" in result.output


def test_styles_list_json(invoke, mock_api):
    mock_api.get("/api/v1/writing-styles").respond(200, json=STYLE_LIST)
    result = invoke(["styles", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["styles"][0]["style_name"] == "Professional"


def test_styles_list_include_inactive(invoke, mock_api):
    route = mock_api.get("/api/v1/writing-styles").respond(200, json=STYLE_LIST)
    result = invoke(["styles", "list", "--include-inactive"])
    assert result.exit_code == 0
    assert route.calls[0].request.url.params["include_inactive"] == "true"


def test_styles_get(invoke, mock_api):
    mock_api.get("/api/v1/writing-styles/ws-1").respond(200, json=SAMPLE_STYLE)
    result = invoke(["styles", "get", "ws-1"])
    assert result.exit_code == 0
    assert "Professional" in result.output
    assert "Write in a professional, friendly tone." in result.output


def test_styles_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/writing-styles/ws-1").respond(404, json={"detail": "Not found"})
    result = invoke(["styles", "get", "ws-1"])
    assert result.exit_code == 3


def test_styles_create_sends_api_field_names(invoke, mock_api):
    route = mock_api.post("/api/v1/writing-styles").respond(200, json=SAMPLE_STYLE)
    result = invoke(
        [
            "styles",
            "create",
            "--name",
            "Professional",
            "--prompt",
            "Write in a professional, friendly tone.",
        ]
    )
    assert result.exit_code == 0
    assert "Created style" in result.output
    body = json.loads(route.calls[0].request.content)
    assert body == {
        "style_name": "Professional",
        "initial_prompt": "Write in a professional, friendly tone.",
    }


def test_styles_create_default_flag(invoke, mock_api):
    route = mock_api.post("/api/v1/writing-styles").respond(200, json=SAMPLE_STYLE)
    result = invoke(["styles", "create", "--name", "Professional", "--default"])
    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content)["is_default"] is True


def test_styles_create_sample_emails(invoke, mock_api):
    route = mock_api.post("/api/v1/writing-styles").respond(200, json=SAMPLE_STYLE)
    result = invoke(
        [
            "styles",
            "create",
            "--name",
            "Professional",
            "--sample-email",
            "Hi there,",
            "--sample-email",
            "Best regards,",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["sample_emails"] == ["Hi there,", "Best regards,"]


def test_styles_create_json(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles").respond(200, json=SAMPLE_STYLE)
    result = invoke(["styles", "create", "--name", "Professional", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["style_name"] == "Professional"


def test_styles_update_sends_api_field_names(invoke, mock_api):
    updated = {**SAMPLE_STYLE, "style_name": "Updated Style"}
    route = mock_api.put("/api/v1/writing-styles/ws-1").respond(200, json=updated)
    result = invoke(["styles", "update", "ws-1", "--name", "Updated Style"])
    assert result.exit_code == 0
    assert "Updated style" in result.output
    assert json.loads(route.calls[0].request.content) == {"style_name": "Updated Style"}


def test_styles_update_set_default(invoke, mock_api):
    route = mock_api.put("/api/v1/writing-styles/ws-1").respond(200, json=SAMPLE_STYLE)
    result = invoke(["styles", "update", "ws-1", "--default"])
    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {"is_default": True}


def test_styles_update_deactivate(invoke, mock_api):
    inactive = {**SAMPLE_STYLE, "is_active": False}
    route = mock_api.put("/api/v1/writing-styles/ws-1").respond(200, json=inactive)
    result = invoke(["styles", "update", "ws-1", "--inactive"])
    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {"is_active": False}


def test_styles_update_no_fields(invoke, mock_api):
    result = invoke(["styles", "update", "ws-1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_styles_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/writing-styles/ws-1").respond(200, json={"message": "ok"})
    result = invoke(["styles", "delete", "ws-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_styles_delete_aborted(invoke, mock_api):
    result = invoke(["styles", "delete", "ws-1"], input="n\n")
    assert result.exit_code == 1


def test_styles_train(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/ws-1/train").respond(
        200, json={"session_id": "ts-1", "status": "started"}
    )
    result = invoke(["styles", "train", "ws-1", "--sample-text", "This is a sample."])
    assert result.exit_code == 0
    assert "Training session" in result.output


def test_styles_feedback(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/training-sessions/ts-1/feedback").respond(
        200, json={"status": "received"}
    )
    result = invoke(["styles", "feedback", "ts-1", "--rating", "5", "--comments", "Great"])
    assert result.exit_code == 0
    assert "Feedback submitted" in result.output


def test_styles_iterate(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/training-sessions/ts-1/iterate").respond(
        200, json={"status": "iterating"}
    )
    result = invoke(["styles", "iterate", "ts-1", "--feedback", "More formal please"])
    assert result.exit_code == 0
    assert "Iteration submitted" in result.output


def test_styles_analyze(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/analyze").respond(200, json={"analysis": "Good tone"})
    result = invoke(["styles", "analyze", "--text", "Hello world"])
    assert result.exit_code == 0
    assert "Good tone" in result.output


def test_styles_analyze_json(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/analyze").respond(200, json={"analysis": "Good tone"})
    result = invoke(["styles", "analyze", "--text", "Hello world", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["analysis"] == "Good tone"
