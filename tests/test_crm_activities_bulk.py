"""Tests for `ac crm activities bulk-create` (ENG-1186)."""

import json

from tests.conftest import WHOAMI_RESPONSE

BULK_PATH = "/api/v1/crm/activities/bulk-create"


def test_bulk_create_people_happy_path(invoke, mock_api):
    route = mock_api.post(BULK_PATH).respond(
        201, json={"created_count": 2, "failed_count": 0, "activity_ids": ["a1", "a2"]}
    )
    result = invoke(
        [
            "crm",
            "activities",
            "bulk-create",
            "--type",
            "task",
            "--title",
            "Follow up",
            "--member-type",
            "person",
            "--ids",
            "p1,p2",
        ]
    )
    assert result.exit_code == 0
    assert "Created 2" in result.output

    body = json.loads(route.calls.last.request.content)
    assert body["type"] == "task"
    assert body["title"] == "Follow up"
    assert body["member_type"] == "person"
    assert body["member_ids"] == ["p1", "p2"]
    assert body["source_app"] == "manual"
    # organization_id comes from the auth context, never the body.
    assert "organization_id" not in body


def test_bulk_create_json(invoke, mock_api):
    mock_api.post(BULK_PATH).respond(
        201, json={"created_count": 1, "failed_count": 0, "activity_ids": ["a1"]}
    )
    result = invoke(
        [
            "crm",
            "activities",
            "bulk-create",
            "--type",
            "note",
            "--title",
            "Touched base",
            "--description",
            "hi",
            "--member-type",
            "company",
            "--ids",
            "c1",
            "--json",
        ]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["created_count"] == 1
    assert parsed["activity_ids"] == ["a1"]


def test_bulk_create_strips_and_filters_ids(invoke, mock_api):
    route = mock_api.post(BULK_PATH).respond(
        201, json={"created_count": 2, "failed_count": 0, "activity_ids": ["a1", "a2"]}
    )
    result = invoke(
        [
            "crm",
            "activities",
            "bulk-create",
            "--title",
            "T",
            "--member-type",
            "person",
            "--ids",
            " p1 , p2 ,",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    # whitespace stripped, trailing empty segment dropped; server de-dupes.
    assert body["member_ids"] == ["p1", "p2"]
    # --type defaults to task.
    assert body["type"] == "task"


def test_bulk_create_resolves_assigned_to_me(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    route = mock_api.post(BULK_PATH).respond(
        201, json={"created_count": 1, "failed_count": 0, "activity_ids": ["a1"]}
    )
    result = invoke(
        [
            "crm",
            "activities",
            "bulk-create",
            "--type",
            "task",
            "--title",
            "Mine",
            "--member-type",
            "person",
            "--ids",
            "p1",
            "--assigned-to",
            "me",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["assigned_to"] == WHOAMI_RESPONSE["user_id"]


def test_bulk_create_rejects_bad_member_type(invoke, mock_api):
    result = invoke(
        [
            "crm",
            "activities",
            "bulk-create",
            "--type",
            "task",
            "--title",
            "x",
            "--member-type",
            "deal",
            "--ids",
            "p1",
        ]
    )
    assert result.exit_code == 1
    assert "member-type" in result.output


def test_bulk_create_rejects_empty_ids(invoke, mock_api):
    result = invoke(
        [
            "crm",
            "activities",
            "bulk-create",
            "--type",
            "task",
            "--title",
            "x",
            "--member-type",
            "person",
            "--ids",
            " , , ",
        ]
    )
    assert result.exit_code == 1
    assert "No IDs" in result.output


def test_bulk_create_api_validation_error_exit_2(invoke, mock_api):
    mock_api.post(BULK_PATH).respond(422, json={"detail": "member_ids must not be empty"})
    result = invoke(
        [
            "crm",
            "activities",
            "bulk-create",
            "--type",
            "task",
            "--title",
            "x",
            "--member-type",
            "person",
            "--ids",
            "p1",
            "--json",
        ]
    )
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 422
