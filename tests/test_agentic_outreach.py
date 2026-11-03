"""Tests for the Outreach email draft review commands."""

import json

BASE = "/api/v1/agentic/outreach/drafts"
DECISION_ID = "11111111-1111-4111-8111-111111111111"
ENROLLMENT_ID = "22222222-2222-4222-8222-222222222222"
CAMPAIGN_ID = "33333333-3333-4333-8333-333333333333"
RUN_ID = "44444444-4444-4444-8444-444444444444"
HASH = "a" * 64

ACTIONS = "/api/v1/agentic/outreach/actions"
ACTION_ID = "88888888-8888-4888-8888-888888888888"

ACTION = {
    "id": ACTION_ID,
    "enrollment_id": ENROLLMENT_ID,
    "decision_id": DECISION_ID,
    "type": "email",
    "status": "pending_approval",
    "created_at": "2026-10-21T10:00:00Z",
    "person": {
        "kind": "crm.person",
        "id": "77777777-7777-4777-8777-777777777777",
        "name": "Jane Doe",
    },
    "company_name": "Acme",
    "campaign": {"id": CAMPAIGN_ID, "name": "Q4 intro", "status": "active"},
    "rationale": "She asked for the deck.",
    "objective": "Book a call.",
    "to": "jane@acme.example",
    "replying_to": {
        "communication_id": "99999999-9999-4999-8999-999999999999",
        "text": "Can you send the deck?",
    },
    "draft_payload": {"subject": "The deck", "body": "Hi Jane, here is the deck."},
}


def _page(*items, total=None, offset=0, has_more=False):
    return {
        "data": list(items),
        "total": len(items) if total is None else total,
        "limit": 50,
        "offset": offset,
        "has_more": has_more,
    }


REVIEW = {
    "decision_id": DECISION_ID,
    "enrollment_id": ENROLLMENT_ID,
    "campaign_id": CAMPAIGN_ID,
    "run_id": RUN_ID,
    "outcome": "proposed",
    "rationale": "She asked for the deck.",
    "ai_subject": "The deck",
    "ai_body": "Hi Jane, here is the deck.",
    "reviewer_note": None,
    "failure_reason": None,
    "context_version": 3,
    "enrollment_status": "active",
    "campaign_status": "active",
    "organization_stopped": False,
    "approval_id": "55555555-5555-4555-8555-555555555555",
    "approval_expires_at": "2026-10-28T10:00:00Z",
    "draft": {
        "communication_id": "66666666-6666-4666-8666-666666666666",
        "status": "draft",
        "subject": "The deck",
        "body": "Hi Jane, here is the deck.",
        "to_emails": ["jane@acme.example"],
    },
    "content_hash": HASH,
    "locked": False,
    "reviewable": True,
}
CONFLICT = {
    "error": "Conflict",
    "message": "The enrollment changed. Reload the draft.",
    "type": "conflict",
    "context": {"code": "version_changed"},
    "code": "version_changed",
}


def test_list_sends_the_filters_and_prints_the_actions(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page(ACTION, total=11, offset=10))

    result = invoke(
        [
            "agentic",
            "outreach",
            "drafts",
            "list",
            "--status",
            "approved",
            "--campaign-id",
            CAMPAIGN_ID,
            "--type",
            "email",
            "--limit",
            "5",
            "--offset",
            "10",
        ]
    )

    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert params["status"] == "approved"
    assert params["campaign_id"] == CAMPAIGN_ID
    assert params["type"] == "email"
    assert params["limit"] == "5"
    assert params["offset"] == "10"
    # The table folds the action id over two lines, so only its start is whole.
    for shown in (ACTION_ID[:9], "Jane Doe", "Q4 intro", "email"):
        assert shown in result.output


def test_list_sends_no_status_by_default(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page(ACTION))

    result = invoke(["agentic", "outreach", "drafts", "list"])

    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert "status" not in params
    assert "type" not in params
    assert "campaign_id" not in params


def test_list_names_the_page_and_the_next_offset(invoke, mock_api):
    mock_api.get(ACTIONS).respond(200, json=_page(ACTION, total=3, has_more=True))

    result = invoke(["agentic", "outreach", "drafts", "list", "--limit", "1"])

    assert result.exit_code == 0, result.output
    assert "1-1 of 3" in result.output
    assert "--offset 1" in result.output


def test_list_names_the_address_when_the_person_has_no_name(invoke, mock_api):
    nameless = {**ACTION, "person": {**ACTION["person"], "name": None}, "to": "ann@x.io"}
    mock_api.get(ACTIONS).respond(200, json=_page(nameless))

    result = invoke(["agentic", "outreach", "drafts", "list"])

    assert result.exit_code == 0, result.output
    assert "ann@x.io" in result.output
    assert "None" not in result.output


def test_list_of_an_empty_queue_names_the_total(invoke, mock_api):
    mock_api.get(ACTIONS).respond(200, json=_page(total=4, offset=10))

    result = invoke(["agentic", "outreach", "drafts", "list", "--offset", "10"])

    assert result.exit_code == 0, result.output
    assert "0 of 4" in result.output
    assert "--offset" not in result.output


def test_list_json_keeps_the_page(invoke, mock_api):
    mock_api.get(ACTIONS).respond(200, json=_page(ACTION))

    result = invoke(["agentic", "outreach", "drafts", "list", "--json"])

    assert json.loads(result.output) == _page(ACTION)


def test_list_refuses_a_negative_offset(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    result = invoke(["agentic", "outreach", "drafts", "list", "--offset", "-1", "--json"])

    assert result.exit_code == 2
    assert not route.called


def test_list_refuses_a_limit_the_api_refuses(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    result = invoke(["agentic", "outreach", "drafts", "list", "--limit", "101", "--json"])

    assert result.exit_code == 2
    assert not route.called


def test_list_refuses_an_unknown_status_and_type(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    status = invoke(["agentic", "outreach", "drafts", "list", "--status", "pending", "--json"])
    kind = invoke(["agentic", "outreach", "drafts", "list", "--type", "wait", "--json"])

    assert (status.exit_code, kind.exit_code) == (2, 2)
    assert not route.called


def test_get_prints_the_item_the_reply_and_the_draft(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=ACTION)

    result = invoke(["agentic", "outreach", "drafts", "get", ACTION_ID])

    assert result.exit_code == 0, result.output
    for shown in (
        DECISION_ID,
        "Jane Doe",
        "Acme",
        "Q4 intro",
        "jane@acme.example",
        "She asked for the deck.",
        "Book a call.",
        "Can you send the deck?",
        "The deck",
        "Hi Jane, here is the deck.",
    ):
        assert shown in result.output


def test_get_prints_a_linkedin_note(invoke, mock_api):
    note = {
        **ACTION,
        "type": "linkedin_connection",
        "to": "https://www.linkedin.com/in/jane",
        "replying_to": None,
        "draft_payload": {"note": "Hi Jane, let us connect."},
    }
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=note)

    result = invoke(["agentic", "outreach", "drafts", "get", ACTION_ID])

    assert result.exit_code == 0, result.output
    assert "Hi Jane, let us connect." in result.output
    assert "https://www.linkedin.com/in/jane" in result.output


def test_get_json_keeps_the_item(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=ACTION)

    result = invoke(["agentic", "outreach", "drafts", "get", ACTION_ID, "--json"])

    assert json.loads(result.output) == ACTION


def test_get_of_an_unknown_action_exits_3(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(404, json={"detail": "not found"})

    result = invoke(["agentic", "outreach", "drafts", "get", ACTION_ID, "--json"])

    assert result.exit_code == 3


def test_save_patches_only_the_given_fields(invoke, mock_api):
    route = mock_api.patch(f"{BASE}/{DECISION_ID}").respond(200, json=REVIEW)

    result = invoke(
        ["agentic", "outreach", "drafts", "save", DECISION_ID, "--body", "Shorter.", "--json"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"body": "Shorter."}


def test_save_reads_the_body_from_a_file(invoke, mock_api, tmp_path):
    route = mock_api.patch(f"{BASE}/{DECISION_ID}").respond(200, json=REVIEW)
    body = tmp_path / "body.txt"
    body.write_text("Line one.\nLine two.\n")

    result = invoke(
        [
            "agentic",
            "outreach",
            "drafts",
            "save",
            DECISION_ID,
            "--subject",
            "New subject",
            "--body-file",
            str(body),
        ]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "subject": "New subject",
        "body": "Line one.\nLine two.\n",
    }


def test_save_refuses_nothing_to_save_before_the_request(invoke, mock_api):
    route = mock_api.patch(f"{BASE}/{DECISION_ID}").respond(200, json=REVIEW)

    result = invoke(["agentic", "outreach", "drafts", "save", DECISION_ID, "--json"])

    assert result.exit_code == 2
    assert not route.called


def test_save_refuses_both_body_flags(invoke, mock_api, tmp_path):
    route = mock_api.patch(f"{BASE}/{DECISION_ID}").respond(200, json=REVIEW)
    body = tmp_path / "body.txt"
    body.write_text("x")

    result = invoke(
        [
            "agentic",
            "outreach",
            "drafts",
            "save",
            DECISION_ID,
            "--body",
            "y",
            "--body-file",
            str(body),
            "--json",
        ]
    )

    assert result.exit_code == 2
    assert not route.called


def test_save_after_the_approval_exits_5(invoke, mock_api):
    mock_api.patch(f"{BASE}/{DECISION_ID}").respond(
        409, json={**CONFLICT, "code": "draft_locked", "context": {"code": "draft_locked"}}
    )

    result = invoke(["agentic", "outreach", "drafts", "save", DECISION_ID, "--body", "x", "--json"])

    assert result.exit_code == 5
    assert json.loads(result.output)["context"] == {"code": "draft_locked"}


def test_approve_sends_the_version_and_the_hash(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DECISION_ID}/approve").respond(
        200, json={**REVIEW, "outcome": "approved", "locked": True, "reviewable": False}
    )

    result = invoke(
        [
            "agentic",
            "outreach",
            "drafts",
            "approve",
            DECISION_ID,
            "--context-version",
            "3",
            "--content-hash",
            HASH,
        ]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "context_version": 3,
        "content_hash": HASH,
    }
    assert "approved" in result.output
    assert "Approve:" not in result.output


def test_approve_refuses_a_malformed_hash_before_the_request(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DECISION_ID}/approve").respond(200, json=REVIEW)

    result = invoke(
        [
            "agentic",
            "outreach",
            "drafts",
            "approve",
            DECISION_ID,
            "--context-version",
            "3",
            "--content-hash",
            "abc",
            "--json",
        ]
    )

    assert result.exit_code == 2
    assert not route.called


def test_a_stale_approve_exits_5_with_the_code(invoke, mock_api):
    mock_api.post(f"{BASE}/{DECISION_ID}/approve").respond(409, json=CONFLICT)

    result = invoke(
        [
            "agentic",
            "outreach",
            "drafts",
            "approve",
            DECISION_ID,
            "--context-version",
            "2",
            "--content-hash",
            HASH,
            "--json",
        ]
    )

    assert result.exit_code == 5
    assert json.loads(result.output)["context"] == {"code": "version_changed"}


def test_reject_sends_the_mode_and_the_note(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DECISION_ID}/reject").respond(
        200, json={**REVIEW, "outcome": "rejected", "reviewer_note": "Shorter."}
    )

    result = invoke(
        [
            "agentic",
            "outreach",
            "drafts",
            "reject",
            DECISION_ID,
            "--mode",
            "regenerate",
            "--note",
            "Shorter.",
            "--json",
        ]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "mode": "regenerate",
        "note": "Shorter.",
    }


def test_reject_skip_sends_no_note_when_none_is_given(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DECISION_ID}/reject").respond(200, json=REVIEW)

    result = invoke(["agentic", "outreach", "drafts", "reject", DECISION_ID, "--mode", "skip"])

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"mode": "skip"}


def test_reject_refuses_an_unknown_mode_before_the_request(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DECISION_ID}/reject").respond(200, json=REVIEW)

    result = invoke(
        ["agentic", "outreach", "drafts", "reject", DECISION_ID, "--mode", "later", "--json"]
    )

    assert result.exit_code == 2
    assert not route.called


def test_reject_exit_asks_before_it_ends_the_enrollment(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DECISION_ID}/reject").respond(200, json=REVIEW)

    result = invoke(
        ["agentic", "outreach", "drafts", "reject", DECISION_ID, "--mode", "exit"],
        input="n\n",
    )

    assert result.exit_code == 1
    assert not route.called


def test_reject_exit_with_yes_skips_the_question(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{DECISION_ID}/reject").respond(200, json=REVIEW)

    result = invoke(
        ["agentic", "outreach", "drafts", "reject", DECISION_ID, "--mode", "exit", "--yes"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"mode": "exit"}
