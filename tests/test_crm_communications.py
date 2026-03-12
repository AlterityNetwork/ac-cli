"""Tests for CRM communications commands."""

import json


SAMPLE_COMMUNICATION = {
    "id": "comm1",
    "organization_id": "org-456",
    "type": "email",
    "direction": "inbound",
    "status": "delivered",
    "subject": "Re: Sales automation",
    "content": "Hi Alex, thanks for reaching out.",
    "from_email": "jane@example.com",
    "from_name": "Jane Doe",
    "to_emails": ["alex@agencycore.ai"],
    "communication_date": "2026-03-11T12:00:00Z",
    "thread_id": "thread_jane_001",
    "company_id": "c1",
    "contact_id": "p1",
    "sentiment": "positive",
    "created_at": "2026-03-11T12:00:00Z",
    "updated_at": "2026-03-11T12:00:00Z",
}

SAMPLE_OUTBOUND = {
    "id": "comm0",
    "organization_id": "org-456",
    "type": "email",
    "direction": "outbound",
    "status": "sent",
    "subject": "Sales automation",
    "content": "Hi Jane, I noticed your company...",
    "from_email": "alex@agencycore.ai",
    "from_name": "Alex Chen",
    "to_emails": ["jane@example.com"],
    "communication_date": "2026-03-10T10:00:00Z",
    "thread_id": "thread_jane_001",
    "company_id": "c1",
    "contact_id": "p1",
    "sentiment": None,
    "created_at": "2026-03-10T10:00:00Z",
    "updated_at": "2026-03-10T10:00:00Z",
}


def test_comms_list(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications").respond(200, json=[SAMPLE_COMMUNICATION])
    result = invoke(["crm", "comms", "list"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output


def test_comms_list_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications").respond(200, json=[SAMPLE_COMMUNICATION])
    result = invoke(["crm", "--json", "comms", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["from_name"] == "Jane Doe"


def test_comms_list_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications").respond(200, json=[])
    result = invoke(["crm", "comms", "list", "--direction", "inbound", "--type", "email"])
    assert result.exit_code == 0


def test_comms_get(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/comm1").respond(200, json=SAMPLE_COMMUNICATION)
    result = invoke(["crm", "comms", "get", "comm1"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output
    assert "Hi Alex, thanks for reaching out." in result.output


def test_comms_thread(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/thread/thread_jane_001").respond(
        200, json=[SAMPLE_OUTBOUND, SAMPLE_COMMUNICATION]
    )
    result = invoke(["crm", "comms", "thread", "thread_jane_001"])
    assert result.exit_code == 0
    assert "Alex Chen" in result.output
    assert "Jane Doe" in result.output


def test_comms_thread_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/thread/thread_jane_001").respond(
        200, json=[SAMPLE_OUTBOUND, SAMPLE_COMMUNICATION]
    )
    result = invoke(["crm", "--json", "comms", "thread", "thread_jane_001"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed) == 2


def test_comms_unread(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/unread-counts").respond(
        200, json={"thread_counts": {"thread_jane_001": 2, "thread_bob_001": 1}}
    )
    result = invoke(["crm", "comms", "unread"])
    assert result.exit_code == 0
    assert "3 total" in result.output
    assert "thread_jane_001" in result.output


def test_comms_unread_empty(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/unread-counts").respond(
        200, json={"thread_counts": {}}
    )
    result = invoke(["crm", "comms", "unread"])
    assert result.exit_code == 0
    assert "No unread" in result.output


def test_comms_mark_read(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/thread/thread_jane_001/mark-read").respond(200, json={})
    result = invoke(["crm", "comms", "mark-read", "thread_jane_001"])
    assert result.exit_code == 0
    assert "Marked thread" in result.output


def test_comms_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/communications/comm1").respond(204)
    result = invoke(["crm", "comms", "delete", "comm1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_comms_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "comms", "delete", "comm1"], input="n\n")
    assert result.exit_code == 1


def test_comms_delete_thread_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/communications/thread/thread_jane_001").respond(204)
    result = invoke(["crm", "comms", "delete-thread", "thread_jane_001", "--yes"])
    assert result.exit_code == 0
    assert "Deleted thread" in result.output


def test_comms_delete_thread_aborted(invoke, mock_api):
    result = invoke(["crm", "comms", "delete-thread", "thread_jane_001"], input="n\n")
    assert result.exit_code == 1


def test_comms_list_error(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications").respond(500, json={"detail": "Internal error"})
    result = invoke(["crm", "comms", "list"])
    assert result.exit_code == 1
    assert "500" in result.output


# -- update --


def test_comms_update(invoke, mock_api):
    updated = {**SAMPLE_COMMUNICATION, "subject": "Updated subject"}
    mock_api.patch("/api/v1/crm/communications/comm1").respond(200, json=updated)
    result = invoke(["crm", "comms", "update", "comm1", "--subject", "Updated subject"])
    assert result.exit_code == 0
    assert "Updated communication" in result.output


def test_comms_update_json(invoke, mock_api):
    updated = {**SAMPLE_COMMUNICATION, "subject": "Updated subject"}
    mock_api.patch("/api/v1/crm/communications/comm1").respond(200, json=updated)
    result = invoke(["crm", "--json", "comms", "update", "comm1", "--subject", "Updated subject"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["subject"] == "Updated subject"


def test_comms_update_no_fields(invoke, mock_api):
    result = invoke(["crm", "comms", "update", "comm1"])
    assert result.exit_code == 1


# -- archive / unarchive --


def test_comms_archive_thread(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/archive").respond(200, json={"archived": True})
    result = invoke(["crm", "comms", "archive", "--thread-id", "thread_jane_001"])
    assert result.exit_code == 0
    assert "Archived" in result.output


def test_comms_archive_comm(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/archive").respond(200, json={"archived": True})
    result = invoke(["crm", "comms", "archive", "--comm-id", "comm1"])
    assert result.exit_code == 0
    assert "Archived" in result.output


def test_comms_archive_missing_id(invoke, mock_api):
    result = invoke(["crm", "comms", "archive"])
    assert result.exit_code == 1
    assert "Must specify" in result.output


def test_comms_unarchive_thread(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/unarchive").respond(200, json={"archived": False})
    result = invoke(["crm", "comms", "unarchive", "--thread-id", "thread_jane_001"])
    assert result.exit_code == 0
    assert "Unarchived" in result.output


def test_comms_unarchive_missing_id(invoke, mock_api):
    result = invoke(["crm", "comms", "unarchive"])
    assert result.exit_code == 1
    assert "Must specify" in result.output


# -- contact-by-email --


SAMPLE_CONTACT = {
    "id": "p1",
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "job_title": "VP Sales",
    "company_id": "c1",
}


def test_comms_contact_by_email(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/contact-by-email").respond(200, json=SAMPLE_CONTACT)
    result = invoke(["crm", "comms", "contact-by-email", "jane@example.com"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output


def test_comms_contact_by_email_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/contact-by-email").respond(200, json=SAMPLE_CONTACT)
    result = invoke(["crm", "--json", "comms", "contact-by-email", "jane@example.com"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["email"] == "jane@example.com"


# -- resolve-contact --


def test_comms_resolve_contact(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/resolve-contact").respond(200, json=SAMPLE_CONTACT)
    result = invoke(["crm", "comms", "resolve-contact", "jane@example.com", "--name", "Jane Doe"])
    assert result.exit_code == 0
    assert "Resolved contact" in result.output


def test_comms_resolve_contact_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/resolve-contact").respond(200, json=SAMPLE_CONTACT)
    result = invoke(["crm", "--json", "comms", "resolve-contact", "jane@example.com"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["full_name"] == "Jane Doe"


# -- draft-email --


SAMPLE_DRAFT = {
    "id": "draft1",
    "subject": "Partnership opportunity",
    "content": "Dear Jane...",
    "status": "draft",
}


def test_comms_draft_email(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/draft-email").respond(201, json=SAMPLE_DRAFT)
    result = invoke([
        "crm", "comms", "draft-email",
        "--contact-id", "p1",
        "--subject", "Partnership opportunity",
        "--content", "Dear Jane...",
    ])
    assert result.exit_code == 0
    assert "Draft created" in result.output


def test_comms_draft_email_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/draft-email").respond(201, json=SAMPLE_DRAFT)
    result = invoke([
        "crm", "--json", "comms", "draft-email",
        "--contact-id", "p1",
        "--subject", "Partnership opportunity",
        "--content", "Dear Jane...",
    ])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["subject"] == "Partnership opportunity"


# -- generate-draft --


SAMPLE_GENERATED = {
    "subject": "Re: Partnership",
    "body": "Hi Jane, thank you for...",
}


def test_comms_generate_draft(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/generate-draft").respond(200, json=SAMPLE_GENERATED)
    result = invoke([
        "crm", "comms", "generate-draft",
        "--mode", "compose",
        "--recipient-name", "Jane Doe",
    ])
    assert result.exit_code == 0
    assert "Generated Draft" in result.output
    assert "Re: Partnership" in result.output


def test_comms_generate_draft_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/communications/generate-draft").respond(200, json=SAMPLE_GENERATED)
    result = invoke([
        "crm", "--json", "comms", "generate-draft",
        "--mode", "reply",
        "--recipient-name", "Jane Doe",
        "--original-subject", "Partnership",
    ])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["subject"] == "Re: Partnership"


# -- unread-thread-ids --


def test_comms_unread_thread_ids(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/unread-thread-ids").respond(
        200, json={"thread_ids": ["thread_jane_001", "thread_bob_001"]}
    )
    result = invoke(["crm", "comms", "unread-thread-ids"])
    assert result.exit_code == 0
    assert "thread_jane_001" in result.output
    assert "2" in result.output  # count


def test_comms_unread_thread_ids_empty(invoke, mock_api):
    mock_api.get("/api/v1/crm/communications/unread-thread-ids").respond(
        200, json={"thread_ids": []}
    )
    result = invoke(["crm", "comms", "unread-thread-ids"])
    assert result.exit_code == 0
    assert "No unread" in result.output


def test_comms_unread_thread_ids_json(invoke, mock_api):
    data = {"thread_ids": ["thread_jane_001"]}
    mock_api.get("/api/v1/crm/communications/unread-thread-ids").respond(200, json=data)
    result = invoke(["crm", "--json", "comms", "unread-thread-ids"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["thread_ids"] == ["thread_jane_001"]
