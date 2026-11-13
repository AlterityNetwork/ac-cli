"""Tests for the Envoy Review queue commands."""

import json

import pytest

from ac_cli.commands.envoy import _LIST_FIELDS, _flat

# The column index of each list cell, for the `table_column` reader.
COLUMN = {key: index for index, (key, _) in enumerate(_LIST_FIELDS)}

DECISION_ID = "11111111-1111-4111-8111-111111111111"
ENROLLMENT_ID = "22222222-2222-4222-8222-222222222222"
CAMPAIGN_ID = "33333333-3333-4333-8333-333333333333"

ACTIONS = "/api/v1/agentic/envoy/actions"
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
    "touch_number": 2,
    "campaign": {"id": CAMPAIGN_ID, "name": "Q4 intro", "status": "active", "max_touches": 5},
    "rationale": "She asked for the deck.",
    "objective": "Book a call.",
    "to": "jane@acme.example",
    "replying_to": {
        "communication_id": "99999999-9999-4999-8999-999999999999",
        "text": "Can you send the deck?",
        "sentiment": "positive",
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


def test_list_sends_the_filters_and_prints_the_actions(invoke, mock_api, table_column):
    route = mock_api.get(ACTIONS).respond(200, json=_page(ACTION, total=11, offset=10))

    result = invoke(
        [
            "agentic",
            "envoy",
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
    # A cell folds over lines, so the reader joins its parts.
    for key, shown in (
        ("id", ACTION_ID),
        ("person_name", "JaneDoe"),
        ("campaign_name", "Q4intro"),
        ("type", "email"),
    ):
        assert table_column(result.output, COLUMN[key]).replace(" ", "") == shown


def test_list_sends_no_status_by_default(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page(ACTION))

    result = invoke(["agentic", "envoy", "drafts", "list"])

    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert "status" not in params
    assert "type" not in params
    assert "campaign_id" not in params


def test_list_names_the_page_and_the_next_offset(invoke, mock_api):
    mock_api.get(ACTIONS).respond(200, json=_page(ACTION, total=3, has_more=True))

    result = invoke(["agentic", "envoy", "drafts", "list", "--limit", "1"])

    assert result.exit_code == 0, result.output
    assert "1-1 of 3" in result.output
    assert "--offset 1" in result.output


def test_list_names_the_address_when_the_person_has_no_name(invoke, mock_api, table_column):
    nameless = {**ACTION, "person": {**ACTION["person"], "name": None}, "to": "ann@x.io"}
    mock_api.get(ACTIONS).respond(200, json=_page(nameless))

    result = invoke(["agentic", "envoy", "drafts", "list"])

    assert result.exit_code == 0, result.output
    assert table_column(result.output, COLUMN["person_name"]) == "ann@x.io"
    assert "None" not in result.output


def test_list_of_an_empty_queue_names_the_total(invoke, mock_api):
    mock_api.get(ACTIONS).respond(200, json=_page(total=4, offset=10))

    result = invoke(["agentic", "envoy", "drafts", "list", "--offset", "10"])

    assert result.exit_code == 0, result.output
    assert "0 of 4" in result.output
    assert "--offset" not in result.output


def test_list_json_keeps_the_page(invoke, mock_api):
    mock_api.get(ACTIONS).respond(200, json=_page(ACTION))

    result = invoke(["agentic", "envoy", "drafts", "list", "--json"])

    assert json.loads(result.output) == _page(ACTION)


def test_list_refuses_a_negative_offset(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    result = invoke(["agentic", "envoy", "drafts", "list", "--offset", "-1", "--json"])

    assert result.exit_code == 2
    assert not route.called


def test_list_refuses_a_limit_the_api_refuses(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    result = invoke(["agentic", "envoy", "drafts", "list", "--limit", "101", "--json"])

    assert result.exit_code == 2
    assert not route.called


def test_list_refuses_an_unknown_status_and_type(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    status = invoke(["agentic", "envoy", "drafts", "list", "--status", "pending", "--json"])
    kind = invoke(["agentic", "envoy", "drafts", "list", "--type", "wait", "--json"])

    assert (status.exit_code, kind.exit_code) == (2, 2)
    assert not route.called


def test_list_sends_each_status_and_the_handled_window(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    result = invoke(
        [
            "agentic",
            "envoy",
            "drafts",
            "list",
            "--status",
            "approved",
            "--status",
            "sending",
            "--since",
            "2026-11-01T00:00:00Z",
            "--sort",
            "newest_decided",
        ]
    )

    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert params.get_list("status") == ["approved", "sending"]
    assert params["since"] == "2026-11-01T00:00:00+00:00"
    assert params["sort"] == "newest_decided"


def test_list_sends_no_since_and_no_sort_by_default(invoke, mock_api):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    result = invoke(["agentic", "envoy", "drafts", "list"])

    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert "since" not in params
    assert "sort" not in params


@pytest.mark.parametrize(
    "flags",
    [
        ["--status", "approved", "--status", "pending"],
        ["--since", "last week"],
        ["--sort", "newest"],
    ],
)
def test_list_refuses_a_bad_status_since_or_sort_before_the_request(invoke, mock_api, flags):
    route = mock_api.get(ACTIONS).respond(200, json=_page())

    result = invoke(["agentic", "envoy", "drafts", "list", *flags, "--json"])

    assert result.exit_code == 2
    assert not route.called


HANDLED = {
    **ACTION,
    "status": "rejected",
    "decided_at": "2026-10-22T09:30:00Z",
    "decided_by": "Ann Lee",
    "reject_then": "regenerate",
    "reject_reason": "Too formal.",
    "failure_reason": None,
}


def test_list_and_get_print_the_decision(invoke, mock_api, table_column):
    mock_api.get(ACTIONS).respond(200, json=_page(HANDLED))
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=HANDLED)

    listed = invoke(["agentic", "envoy", "drafts", "list"])
    got = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID])

    assert listed.exit_code == 0, listed.output
    assert table_column(listed.output, COLUMN["decided_at"]).replace(" ", "") == (
        "2026-10-22T09:30:00Z"
    )
    assert table_column(listed.output, COLUMN["reason"]).replace(" ", "") == "Tooformal."
    assert got.exit_code == 0, got.output
    assert "Ann Lee" in got.output
    assert "Too formal." in got.output


def test_the_reason_cell_reads_the_reject_or_the_failure():
    assert _flat(HANDLED)["reason"] == "Too formal."
    failed = {**HANDLED, "status": "failed", "reject_reason": None}
    assert _flat({**failed, "failure_reason": "not_connected"})["reason"] == "not_connected"
    assert _flat(ACTION)["reason"] is None


def test_get_prints_the_item_the_reply_and_the_draft(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=ACTION)

    result = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID])

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

    result = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID])

    assert result.exit_code == 0, result.output
    assert "Hi Jane, let us connect." in result.output
    assert "https://www.linkedin.com/in/jane" in result.output


def test_get_prints_the_reasoning_of_a_linkedin_draft(invoke, mock_api):
    message = {
        **ACTION,
        "type": "linkedin_message",
        "replying_to": None,
        "draft_payload": {"body": "Hi Jane.", "ai_reasoning": "Angle: her new role."},
    }
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=message)

    result = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID])

    assert result.exit_code == 0, result.output
    assert "Reasoning:" in result.output
    assert "Angle: her new role." in result.output
    assert result.output.index("Hi Jane.") < result.output.index("Reasoning:")


def test_get_of_a_draft_with_no_reasoning_prints_no_label(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=ACTION)

    result = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID])

    assert result.exit_code == 0, result.output
    assert "Reasoning" not in result.output


def test_list_and_get_print_the_touch_and_the_sentiment(invoke, mock_api, table_column):
    mock_api.get(ACTIONS).respond(200, json=_page(ACTION))
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=ACTION)

    listed = invoke(["agentic", "envoy", "drafts", "list"])
    got = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID])

    assert listed.exit_code == 0, listed.output
    # A cell folds over lines, so the reader joins its parts.
    assert table_column(listed.output, COLUMN["touch"]).replace(" ", "") == "2of5"
    assert table_column(listed.output, COLUMN["sentiment"]) == "positive"
    assert got.exit_code == 0, got.output
    assert "2 of 5" in got.output
    assert "positive" in got.output


@pytest.mark.parametrize(
    ("touch_number", "max_touches", "touch"),
    [(2, 5, "2 of 5"), (3, None, "3"), (None, 5, None)],
)
def test_the_touch_cell_names_the_number_and_the_max(touch_number, max_touches, touch):
    item = {**ACTION, "campaign": {**ACTION["campaign"], "max_touches": max_touches}}
    if touch_number is None:
        del item["touch_number"]
    else:
        item["touch_number"] = touch_number

    assert _flat(item)["touch"] == touch


def test_the_touch_cell_names_the_number_when_the_campaign_has_no_max():
    item = {**ACTION, "campaign": {"id": CAMPAIGN_ID, "name": None, "status": None}}

    assert _flat(item)["touch"] == "2"


def test_the_sentiment_cell_reads_the_reply():
    assert _flat(ACTION)["sentiment"] == "positive"
    assert _flat({**ACTION, "replying_to": None})["sentiment"] is None
    unclassified = {**ACTION, "replying_to": {**ACTION["replying_to"], "sentiment": None}}
    assert _flat(unclassified)["sentiment"] is None


@pytest.mark.parametrize(
    ("linkedin", "shown"),
    [
        (
            {
                "state": "connected",
                "degree": 1,
                "invited_at": "2026-11-09T08:00:00Z",
                "connected_at": "2026-11-11T09:30:00Z",
            },
            "connected · 1st · 2026-11-11",
        ),
        (
            {
                "state": "invited",
                "degree": None,
                "invited_at": "2026-11-09T08:00:00Z",
                "connected_at": None,
            },
            "invited · 2026-11-09",
        ),
        (
            {
                "state": "declined",
                "degree": None,
                "invited_at": "2026-11-09T08:00:00Z",
                "connected_at": None,
            },
            "declined",
        ),
        (
            {"state": "none", "degree": None, "invited_at": None, "connected_at": None},
            "none",
        ),
    ],
)
def test_get_prints_the_linkedin_state(invoke, mock_api, linkedin, shown):
    message = {**MESSAGE, "replying_to": None, "linkedin": linkedin}
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=message)

    result = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID])

    assert result.exit_code == 0, result.output
    [line] = [one for one in result.output.splitlines() if "LinkedIn" in one]
    assert line.split("LinkedIn", 1)[1].strip(" │:") == shown


def test_get_of_an_email_prints_no_linkedin_state(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json={**ACTION, "linkedin": None})

    result = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID])

    assert result.exit_code == 0, result.output
    [line] = [one for one in result.output.splitlines() if "LinkedIn" in one]
    assert line.split("LinkedIn", 1)[1].strip(" │:") == ""


def test_get_json_keeps_the_item(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=ACTION)

    result = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID, "--json"])

    assert json.loads(result.output) == ACTION


def test_get_of_an_unknown_action_exits_3(invoke, mock_api):
    mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(404, json={"detail": "not found"})

    result = invoke(["agentic", "envoy", "drafts", "get", ACTION_ID, "--json"])

    assert result.exit_code == 3


APPROVED = {**ACTION, "status": "approved"}


def _approve(*flags):
    return ["agentic", "envoy", "drafts", "approve", ACTION_ID, *flags]


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
    return ["agentic", "envoy", "drafts", "reject", ACTION_ID, *args]


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
    result = invoke(["agentic", "envoy", "drafts", "save", DECISION_ID, "--body", "x"])

    assert result.exit_code == 2
    assert "No such command" in result.output
