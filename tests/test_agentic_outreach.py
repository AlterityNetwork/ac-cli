"""Tests for the Outreach Review queue commands."""

import json

import pytest

DECISION_ID = "11111111-1111-4111-8111-111111111111"
ENROLLMENT_ID = "22222222-2222-4222-8222-222222222222"
CAMPAIGN_ID = "33333333-3333-4333-8333-333333333333"

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


APPROVED = {**ACTION, "status": "approved"}


def _approve(*flags):
    return ["agentic", "outreach", "drafts", "approve", ACTION_ID, *flags]


def test_approve_without_an_edit_sends_no_payload(invoke, mock_api):
    read = mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=ACTION)
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/approve").respond(200, json=APPROVED)

    result = invoke(_approve())

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {}
    assert not read.called
    assert f"Action {ACTION_ID} is approved." in result.output
    assert "Hi Jane, here is the deck." in result.output


def test_approve_merges_an_edit_over_the_draft(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=NEW_EMAIL)
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/approve").respond(200, json=APPROVED)

    result = invoke(_approve("--subject", "A new subject", "--json"))

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "payload": {"subject": "A new subject", "body": "Hi Jane, here is the deck."}
    }
    assert json.loads(result.output)["status"] == "approved"


def test_approve_reads_the_body_from_a_file(invoke, mock_api, tmp_path):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=ACTION)
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/approve").respond(200, json=APPROVED)
    body = tmp_path / "body.txt"
    body.write_text("Line one.\nLine two.\n")

    result = invoke(_approve("--body-file", str(body), "--json"))

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content)["payload"] == {
        "subject": "The deck",
        "body": "Line one.\nLine two.\n",
    }


def test_approve_sends_a_linkedin_message_and_a_note(invoke, mock_api):
    message = {**ACTION, "type": "linkedin_message", "draft_payload": {"body": "Hi"}}
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=message)
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/approve").respond(200, json=APPROVED)

    result = invoke(_approve("--message", "Hi Jane", "--json"))

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"payload": {"body": "Hi Jane"}}

    note = {**ACTION, "type": "linkedin_connection", "draft_payload": {"note": "Hi"}}
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=note)

    result = invoke(_approve("--note", "Hi Jane, let us connect.", "--json"))

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[1].request.content) == {
        "payload": {"note": "Hi Jane, let us connect."}
    }


def test_approve_refuses_two_body_flags_before_the_request(invoke, mock_api, tmp_path):
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/approve").respond(200, json=APPROVED)
    body = tmp_path / "body.txt"
    body.write_text("x")

    for flags in (
        ("--body", "y", "--body-file", str(body)),
        ("--body", "y", "--message", "z"),
        ("--body-file", str(body), "--message", "z"),
    ):
        result = invoke(_approve(*flags, "--json"))

        assert result.exit_code == 2, flags
    assert not route.called


def test_a_failed_draft_check_exits_2_with_the_code_and_the_field(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=NEW_EMAIL)
    detail = {
        "message": "The draft fails the check: draft_placeholder on subject.",
        "code": "draft_placeholder",
        "field": "subject",
    }
    mock_api.post(f"{ACTIONS}/{ACTION_ID}/approve").respond(
        422,
        json={
            "error": "HTTP Error",
            "message": detail["message"],
            "type": "http_error",
            "code": "draft_placeholder",
            "detail": detail,
        },
    )

    result = invoke(_approve("--subject", "Hi [First name]", "--json"))

    assert result.exit_code == 2
    body = json.loads(result.output)
    assert (body["detail"]["code"], body["detail"]["field"]) == ("draft_placeholder", "subject")


NEW_EMAIL = {**ACTION, "replying_to": None}
REPLY = ACTION
CONNECTION = {**ACTION, "type": "linkedin_connection", "draft_payload": {"note": "Hi"}}
MESSAGE = {**ACTION, "type": "linkedin_message", "draft_payload": {"body": "Hi"}}


@pytest.mark.parametrize(
    ("action", "flags"),
    [
        (REPLY, ("--subject", "Re: x")),
        (NEW_EMAIL, ("--note", "x")),
        (NEW_EMAIL, ("--message", "x")),
        (CONNECTION, ("--body", "x")),
        (CONNECTION, ("--message", "x")),
        (MESSAGE, ("--note", "x")),
        (MESSAGE, ("--subject", "x")),
        (MESSAGE, ("--body", "x")),
    ],
)
def test_approve_refuses_a_flag_the_action_type_does_not_take(invoke, mock_api, action, flags):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=action)
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/approve").respond(200, json=APPROVED)

    result = invoke(_approve(*flags, "--json"))

    assert result.exit_code == 2, result.output
    assert not route.called


def test_an_approve_that_is_not_pending_exits_5_with_the_code(invoke, mock_api):
    mock_api.post(f"{ACTIONS}/{ACTION_ID}/approve").respond(
        409,
        json={
            **CONFLICT,
            "code": "action_not_pending",
            "context": {"code": "action_not_pending"},
        },
    )

    result = invoke(_approve("--json"))

    assert result.exit_code == 5
    assert json.loads(result.output)["context"] == {"code": "action_not_pending"}


REJECTED = {**ACTION, "status": "rejected"}


def _reject(*args):
    return ["agentic", "outreach", "drafts", "reject", ACTION_ID, *args]


def test_reject_regenerate_sends_then_and_the_reason_to_the_action(invoke, mock_api):
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/reject").respond(200, json=REJECTED)

    result = invoke(_reject("--then", "regenerate", "--reason", "Shorter.", "--json"))

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "then": "regenerate",
        "reason": "Shorter.",
    }
    assert json.loads(result.output)["status"] == "rejected"


def test_reject_regenerate_needs_a_reason_before_the_request(invoke, mock_api):
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/reject").respond(200, json=REJECTED)

    result = invoke(_reject("--then", "regenerate", "--json"))

    assert result.exit_code == 2
    assert not route.called


def test_reject_refuses_an_unknown_then_before_the_request(invoke, mock_api):
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/reject").respond(200, json=REJECTED)

    result = invoke(_reject("--then", "skip", "--reason", "Later.", "--json"))

    assert result.exit_code == 2
    assert not route.called


def test_reject_stop_asks_before_it_ends_the_enrollment(invoke, mock_api):
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/reject").respond(200, json=REJECTED)

    result = invoke(_reject("--then", "stop"), input="n\n")

    assert result.exit_code == 1
    assert not route.called


def test_reject_stop_with_yes_sends_no_reason_when_none_is_given(invoke, mock_api):
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/reject").respond(200, json=REJECTED)

    result = invoke(_reject("--then", "stop", "--yes"))

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"then": "stop"}
    assert "rejected" in result.output


def test_reject_stop_sends_an_optional_reason(invoke, mock_api):
    route = mock_api.post(f"{ACTIONS}/{ACTION_ID}/reject").respond(200, json=REJECTED)

    result = invoke(_reject("--then", "stop", "--reason", "Wrong person.", "--yes", "--json"))

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "then": "stop",
        "reason": "Wrong person.",
    }


def test_a_reject_that_is_not_pending_exits_5_with_the_code(invoke, mock_api):
    mock_api.post(f"{ACTIONS}/{ACTION_ID}/reject").respond(
        409,
        json={
            **CONFLICT,
            "code": "action_not_pending",
            "context": {"code": "action_not_pending"},
        },
    )

    result = invoke(_reject("--then", "regenerate", "--reason", "x", "--json"))

    assert result.exit_code == 5


def test_the_v2_save_is_gone(invoke, mock_api):
    result = invoke(["agentic", "outreach", "drafts", "save", DECISION_ID, "--body", "x"])

    assert result.exit_code == 2
    assert "No such command" in result.output
