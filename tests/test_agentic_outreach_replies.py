"""Tests for the Outreach reply commands."""

import json

import pytest

from ac_cli.commands.outreach.replies import _LIST_FIELDS

COLUMN = {key: index for index, (key, _) in enumerate(_LIST_FIELDS)}

REPLIES = "/api/v1/agentic/outreach/replies"
ENROLLMENT_ID = "22222222-2222-4222-8222-222222222222"
CAMPAIGN_ID = "33333333-3333-4333-8333-333333333333"
ACTION_ID = "88888888-8888-4888-8888-888888888888"

REPLY = {
    "enrollment_id": ENROLLMENT_ID,
    "state": "needs_reply",
    "channel": "email",
    "person": {
        "kind": "crm.person",
        "id": "77777777-7777-4777-8777-777777777777",
        "name": "Ben Carter",
        "avatar_url": None,
    },
    "company_name": "Tidewater Goods",
    "company_logo_url": None,
    "campaign": {"id": CAMPAIGN_ID, "name": "DTC founders", "status": "active", "max_touches": 5},
    "text": "Happy to talk in January. Can you share two dates?",
    "received_at": "2026-11-25T15:08:00Z",
    "after_touch": 3,
    "to": "ben@tidewater.example",
    "reply_message_id": "m-1",
    "communication_id": "99999999-9999-4999-8999-999999999999",
    "inbox_thread_id": "44444444-4444-4444-8444-444444444444",
    "pending_action_id": None,
    "rationale": "Ben asks for dates.",
    "next_step": "follow_up",
    "next_check_at": "2026-12-20T09:00:00Z",
    "handled_at": None,
    "handled_by": None,
}
READY = {
    **REPLY,
    "enrollment_id": "55555555-5555-4555-8555-555555555555",
    "person": {**REPLY["person"], "name": "Tom Becker"},
    "state": "reply_ready",
    "pending_action_id": ACTION_ID,
    "next_step": None,
}


def _page(*items, total=None, has_more=False, drafts=11):
    return {
        "data": list(items),
        "total": len(items) if total is None else total,
        "limit": 50,
        "offset": 0,
        "has_more": has_more,
        "counts": {"reply_ready": 1, "needs_reply": 4, "drafts": drafts},
        "coming_up": [
            {
                "campaign_id": CAMPAIGN_ID,
                "campaign_name": "DTC founders",
                "people": 3,
                "first_at": "2026-11-26T16:00:00Z",
            }
        ],
    }


def test_list_prints_each_reply_and_the_counts(invoke, mock_api, table_column):
    route = mock_api.get(REPLIES).respond(200, json=_page(REPLY, READY))

    result = invoke(["agentic", "outreach", "replies", "list"])

    assert result.exit_code == 0, result.output
    assert dict(route.calls[0].request.url.params) == {"limit": "50", "offset": "0"}
    assert "BenCarter" in table_column(result.output, COLUMN["person_name"]).replace(" ", "")
    assert "reply_ready" in table_column(result.output, COLUMN["state"]).replace(" ", "")
    line = " ".join(result.output.split())
    assert "1 reply ready, 4 need your reply, 11 drafts to approve" in line
    assert "DTC founders: 3 people due" in line


def test_list_sends_every_filter(invoke, mock_api):
    route = mock_api.get(REPLIES).respond(200, json=_page())

    result = invoke(
        [
            "agentic",
            "outreach",
            "replies",
            "list",
            "--state",
            "replied",
            "--state",
            "done",
            "--campaign-id",
            CAMPAIGN_ID,
            "--since",
            "2026-11-25T00:00:00Z",
            "--limit",
            "5",
            "--offset",
            "10",
        ]
    )

    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert params.get_list("state") == ["replied", "done"]
    assert (params["campaign_id"], params["limit"], params["offset"]) == (
        CAMPAIGN_ID,
        "5",
        "10",
    )
    assert params["since"].startswith("2026-11-25T00:00:00")


def test_list_names_the_next_offset(invoke, mock_api):
    mock_api.get(REPLIES).respond(200, json=_page(REPLY, total=3, has_more=True))

    result = invoke(["agentic", "outreach", "replies", "list", "--limit", "1"])

    assert result.exit_code == 0, result.output
    assert "1-1 of 3" in result.output
    assert "--offset 1" in result.output


def test_list_json_keeps_the_page(invoke, mock_api):
    mock_api.get(REPLIES).respond(200, json=_page(REPLY))

    result = invoke(["agentic", "outreach", "replies", "list", "--json"])

    assert json.loads(result.output) == _page(REPLY)


@pytest.mark.parametrize(
    "args",
    [
        ["--state", "open"],
        ["--limit", "0"],
        ["--limit", "101"],
        ["--offset", "-1"],
        ["--since", "2026-11-25T00:00:00"],
    ],
)
def test_list_refuses_what_the_api_refuses(invoke, mock_api, args):
    route = mock_api.get(REPLIES).respond(200, json=_page())

    result = invoke(["agentic", "outreach", "replies", "list", *args, "--json"])

    assert result.exit_code == 2
    assert not route.called


def test_done_marks_the_reply_done(invoke, mock_api):
    route = mock_api.post(f"{REPLIES}/{ENROLLMENT_ID}/done").respond(
        200, json={**REPLY, "state": "done", "handled_by": "Alex Morgan"}
    )

    result = invoke(["agentic", "outreach", "replies", "done", ENROLLMENT_ID])

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {}
    assert "is done" in result.output


def test_done_sends_the_message_the_caller_saw(invoke, mock_api):
    route = mock_api.post(f"{REPLIES}/{ENROLLMENT_ID}/done").respond(
        200, json={**REPLY, "state": "done"}
    )

    result = invoke(
        [
            "agentic",
            "outreach",
            "replies",
            "done",
            ENROLLMENT_ID,
            "--reply-message-id",
            "m-1",
            "--json",
        ]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"reply_message_id": "m-1"}
    assert json.loads(result.output)["state"] == "done"


@pytest.mark.parametrize(("status", "code"), [(404, 3), (409, 5)])
def test_done_maps_a_refusal_to_its_exit_code(invoke, mock_api, status, code):
    body = {"message": "refused", "code": "reply_not_open"}
    mock_api.post(f"{REPLIES}/{ENROLLMENT_ID}/done").respond(status, json=body)

    result = invoke(["agentic", "outreach", "replies", "done", ENROLLMENT_ID, "--json"])

    assert result.exit_code == code
