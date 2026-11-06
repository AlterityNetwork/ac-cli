"""Tests for `ac inbox`: one row per person, reply and AI draft."""

from __future__ import annotations

import json
from unittest.mock import patch

from httpx import Response

T1 = "00000000-0000-0000-0000-0000000000d1"
P1 = "00000000-0000-0000-0000-0000000000f1"
BASE = "/api/v1/inbox"

ROW = {
    "id": T1,
    "contact_id": P1,
    "person": {"name": "Ada Placeholder", "company_name": "Example Agency Ltd"},
    "conversations": [
        {"thread_id": T1, "channel": "email", "subject": "Re: A fresh look"},
        {"thread_id": "t2", "channel": "linkedin", "subject": None},
    ],
    "conversation_count": 2,
    "last_activity_at": "2026-11-06T09:42:00Z",
    "needs_reply": True,
    "unread": True,
    "intent": "interested",
    "status": "open",
    "owner": {"user_id": "u1", "name": "Mia Me", "is_me": True},
}
PAGE = {"data": [ROW], "total": 1, "limit": 50, "offset": 0, "has_more": False}


def test_list_defaults_to_mine_and_prints_people(invoke, mock_api, table_column):
    route = mock_api.get(f"{BASE}/threads").respond(200, json=PAGE)
    result = invoke(["inbox", "list"])
    assert result.exit_code == 0, result.output
    # A fold drops the space it breaks on, so compare without spaces.
    assert table_column(result.output, 0).replace(" ", "") == "AdaPlaceholder"
    assert table_column(result.output, 2).replace(" ", "") == "email,linkedin"
    query = route.calls[0].request.url.params
    assert query["owner"] == "me"
    assert query["view"] == "inbox"


def test_list_forwards_every_filter(invoke, mock_api):
    route = mock_api.get(f"{BASE}/threads").respond(200, json=PAGE)
    result = invoke(
        [
            "inbox",
            "list",
            "--view",
            "done",
            "--owner",
            "all",
            "--channel",
            "linkedin",
            "--channel",
            "email",
            "--needs-reply",
            "--unread",
            "--intent",
            "interested",
            "--intent",
            "none",
            "--kind",
            "connection",
            "--sequence",
            "any",
            "--since",
            "2026-11-01",
            "--q",
            "ada",
            "--limit",
            "20",
            "--offset",
            "40",
        ]
    )
    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert params.get_list("channel") == ["linkedin", "email"]
    assert params.get_list("intent") == ["interested", "none"]
    assert params["kind"] == "connection"
    assert params["needs_reply"] == "true"
    assert params["unread"] == "true"
    assert (params["view"], params["owner"], params["sequence"]) == (
        "done",
        "all",
        "any",
    )
    assert (params["since"], params["q"]) == ("2026-11-01", "ada")
    assert (params["limit"], params["offset"]) == ("20", "40")


def test_list_json_prints_the_page(invoke, mock_api):
    mock_api.get(f"{BASE}/threads").respond(200, json=PAGE)
    result = invoke(["inbox", "list", "--json"])
    assert json.loads(result.output) == PAGE


def test_list_refuses_an_unknown_channel_before_any_call(invoke, mock_api):
    route = mock_api.get(f"{BASE}/threads").respond(200, json=PAGE)
    result = invoke(["inbox", "list", "--channel", "fax", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] is True
    assert not route.called


def test_list_refuses_a_limit_out_of_range(invoke, mock_api):
    result = invoke(["inbox", "list", "--limit", "500"])
    assert result.exit_code == 2


def test_messages_reads_one_view(invoke, mock_api):
    route = mock_api.get(f"{BASE}/messages").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["inbox", "messages", "--view", "scheduled", "--channel", "linkedin"])
    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert (params["view"], params["channel"], params["owner"]) == (
        "scheduled",
        "linkedin",
        "me",
    )


def test_resolve_names_one_link(invoke, mock_api):
    route = mock_api.get(f"{BASE}/threads/resolve").respond(
        200, json={"thread_id": T1, "contact_id": P1}
    )
    result = invoke(["inbox", "resolve", "--message-id", "thread_abc", "--json"])
    assert json.loads(result.output) == {"thread_id": T1, "contact_id": P1}
    assert route.calls[0].request.url.params["message_id"] == "thread_abc"


def test_resolve_needs_one_name(invoke, mock_api):
    assert invoke(["inbox", "resolve"]).exit_code == 2


def test_show_prints_the_timeline_and_the_reply_state(invoke, mock_api):
    """The timeline table is the first table; the reply table follows it."""
    mock_api.get(f"{BASE}/threads/{T1}").respond(
        200,
        json={
            "id": T1,
            "person": {"name": "Ada Placeholder"},
            "threads": [],
            "timeline": [
                {
                    "id": "c1",
                    "channel": "email",
                    "direction": "inbound",
                    "kind": "message",
                    "sent_at": "2026-11-06T09:42:00Z",
                    "text": "Can you share two case studies?",
                },
            ],
            "reply": {
                "default_channel": "email",
                "channels": [
                    {"channel": "email", "can_reply": True, "reason": None},
                    {
                        "channel": "linkedin",
                        "can_reply": False,
                        "reason": "not_owner",
                        "owner": {"name": "Sam Sample"},
                    },
                ],
            },
        },
    )
    result = invoke(["inbox", "show", T1])
    assert result.exit_code == 0, result.output
    timeline = result.output.split("Reply (starts on")[0]
    texts = "".join(
        line.split("│")[6].strip() for line in timeline.splitlines() if line.startswith("│")
    )
    assert texts.replace(" ", "") == "Canyousharetwocasestudies?"
    assert "not_owner" in result.output


def test_show_unknown_thread_exits_3(invoke, mock_api):
    mock_api.get(f"{BASE}/threads/{T1}").respond(404, json={"message": "no"})
    assert invoke(["inbox", "show", T1]).exit_code == 3


def test_read_unread_status_and_intent(invoke, mock_api):
    changed = {"thread_ids": [T1]}
    read = mock_api.post(f"{BASE}/threads/{T1}/read").respond(200, json=changed)
    unread = mock_api.post(f"{BASE}/threads/{T1}/unread").respond(200, json=changed)
    status = mock_api.post(f"{BASE}/threads/{T1}/status").respond(200, json=changed)
    intent = mock_api.post(f"{BASE}/threads/{T1}/intent").respond(200, json=changed)
    assert invoke(["inbox", "read", T1]).exit_code == 0
    assert invoke(["inbox", "unread", T1]).exit_code == 0
    assert invoke(["inbox", "status", T1, "--status", "done"]).exit_code == 0
    assert json.loads(status.calls[0].request.content) == {"status": "done"}
    assert (
        invoke(
            ["inbox", "status", T1, "--status", "snoozed", "--until", "2026-11-09T09:00:00Z"]
        ).exit_code
        == 0
    )
    assert json.loads(status.calls[1].request.content) == {
        "status": "snoozed",
        "snoozed_until": "2026-11-09T09:00:00Z",
    }
    assert invoke(["inbox", "intent", T1, "--intent", "none"]).exit_code == 0
    assert json.loads(intent.calls[0].request.content) == {"intent": None}
    assert read.called and unread.called


def test_snooze_needs_a_time(invoke, mock_api):
    assert invoke(["inbox", "status", T1, "--status", "snoozed"]).exit_code == 2


def test_bulk_splits_the_ids(invoke, mock_api):
    route = mock_api.post(f"{BASE}/threads/bulk").respond(200, json={"thread_ids": []})
    assert invoke(["inbox", "bulk", "--ids", f"{T1},{P1}", "--action", "done"]).exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "thread_ids": [T1, P1],
        "action": "done",
    }


def test_reply_by_email(invoke, mock_api):
    route = mock_api.post(f"{BASE}/threads/{T1}/reply").respond(
        200, json={"status": "sent", "communication_id": "c9"}
    )
    result = invoke(
        [
            "inbox",
            "reply",
            T1,
            "--channel",
            "email",
            "--body",
            "Two case studies.",
            "--cc",
            "cc@example.test",
        ]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "channel": "email",
        "body_text": "Two case studies.",
        "cc_emails": ["cc@example.test"],
    }


def test_a_parked_linkedin_reply_says_when_it_sends(invoke, mock_api):
    mock_api.post(f"{BASE}/threads/{T1}/reply").respond(
        200,
        json={"status": "scheduled", "communication_id": "c9", "sends_at": "2026-11-07T08:00:00Z"},
    )
    result = invoke(["inbox", "reply", T1, "--channel", "linkedin", "--body", "Tuesday works."])
    assert result.exit_code == 0
    assert "2026-11-07T08:00:00Z" in result.output


def test_a_long_linkedin_reply_is_refused_before_any_call(invoke, mock_api):
    route = mock_api.post(f"{BASE}/threads/{T1}/reply").respond(200, json={})
    result = invoke(["inbox", "reply", T1, "--channel", "linkedin", "--body", "x" * 1001])
    assert result.exit_code == 2
    assert not route.called


def test_a_reply_by_a_non_owner_exits_4(invoke, mock_api):
    mock_api.post(f"{BASE}/threads/{T1}/reply").respond(
        403, json={"message": "Only the owner replies", "code": "INBOX_NOT_OWNER"}
    )
    result = invoke(["inbox", "reply", T1, "--channel", "email", "--body", "Hi", "--json"])
    assert result.exit_code == 4
    assert json.loads(result.output)["status_code"] == 403


def test_a_disconnected_owner_exits_5(invoke, mock_api):
    mock_api.post(f"{BASE}/threads/{T1}/reply").respond(409, json={"message": "no"})
    assert invoke(["inbox", "reply", T1, "--channel", "email", "--body", "Hi"]).exit_code == 5


def test_send_writes_a_new_message(invoke, mock_api):
    route = mock_api.post(f"{BASE}/messages").respond(
        200, json={"status": "sent", "communication_id": "c9"}
    )
    result = invoke(
        [
            "inbox",
            "send",
            "--contact-id",
            P1,
            "--channel",
            "email",
            "--subject",
            "Our deck",
            "--body",
            "Here it is.",
            "--send-at",
            "2026-11-09T09:00:00Z",
        ]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {
        "contact_id": P1,
        "channel": "email",
        "subject": "Our deck",
        "body_text": "Here it is.",
        "send_at": "2026-11-09T09:00:00Z",
    }


def test_ai_draft_starts_and_waits_for_the_draft(invoke, mock_api):
    start = mock_api.post(f"{BASE}/threads/{T1}/ai-draft").respond(202, json={"draft_id": "d1"})
    mock_api.get(f"{BASE}/ai-drafts/d1").mock(
        side_effect=[
            Response(200, json={"draft_id": "d1", "status": "pending"}),
            Response(200, json={"draft_id": "d1", "status": "ready", "body": "Thanks Ada."}),
        ]
    )
    with patch("ac_cli.commands.inbox.time.sleep"):
        result = invoke(["inbox", "ai-draft", T1, "--channel", "email", "--wait"])
    assert result.exit_code == 0, result.output
    assert "Thanks Ada." in result.output
    assert json.loads(start.calls[0].request.content) == {"channel": "email"}


def test_ai_draft_without_wait_prints_the_id(invoke, mock_api):
    mock_api.post(f"{BASE}/threads/{T1}/ai-draft").respond(202, json={"draft_id": "d1"})
    result = invoke(["inbox", "ai-draft", T1, "--channel", "linkedin", "--regenerate"])
    assert result.exit_code == 0
    assert "d1" in result.output


def test_ask_to_reply_and_counts(invoke, mock_api):
    mock_api.post(f"{BASE}/threads/{T1}/ask-to-reply").respond(
        200, json={"owner_user_id": "u2", "notified": True}
    )
    mock_api.get(f"{BASE}/counts").respond(200, json={"badge": 3, "needs_reply": 2, "unread": 2})
    assert invoke(["inbox", "ask-to-reply", T1]).exit_code == 0
    counts = invoke(["inbox", "counts", "--json"])
    assert json.loads(counts.output) == {"badge": 3, "needs_reply": 2, "unread": 2}


def test_every_command_prints_json_with_json(invoke, mock_api):
    changed = {"thread_ids": [T1]}
    mock_api.get(f"{BASE}/messages").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    mock_api.get(f"{BASE}/threads/{T1}").respond(200, json={"id": T1})
    mock_api.post(f"{BASE}/threads/{T1}/read").respond(200, json=changed)
    mock_api.post(f"{BASE}/threads/{T1}/status").respond(200, json=changed)
    mock_api.post(f"{BASE}/threads/{T1}/reply").respond(
        200, json={"status": "sent", "communication_id": "c9"}
    )
    mock_api.post(f"{BASE}/messages").respond(
        200, json={"status": "sent", "communication_id": "c9"}
    )
    mock_api.post(f"{BASE}/threads/{T1}/ai-draft").respond(202, json={"draft_id": "d1"})
    mock_api.post(f"{BASE}/threads/{T1}/ask-to-reply").respond(
        200, json={"owner_user_id": "u2", "notified": True}
    )
    commands = [
        ["inbox", "messages", "--view", "sent"],
        ["inbox", "show", T1],
        ["inbox", "read", T1],
        ["inbox", "status", T1, "--status", "open"],
        ["inbox", "reply", T1, "--channel", "email", "--body", "Hi"],
        [
            "inbox",
            "send",
            "--contact-id",
            P1,
            "--channel",
            "email",
            "--subject",
            "S",
            "--body",
            "Hi",
        ],
        ["inbox", "ai-draft", T1, "--channel", "email"],
        ["inbox", "ask-to-reply", T1],
    ]
    for command in commands:
        result = invoke([*command, "--json"])
        assert result.exit_code == 0, (command, result.output)
        json.loads(result.output)


def test_local_refusals_exit_2_before_any_call(invoke, mock_api):
    reply = mock_api.post(f"{BASE}/threads/{T1}/reply").respond(200, json={})
    bulk = mock_api.post(f"{BASE}/threads/bulk").respond(200, json={})
    assert invoke(["inbox", "list", "--offset", "-1"]).exit_code == 2
    assert invoke(["inbox", "messages", "--view", "inbox"]).exit_code == 2
    assert invoke(["inbox", "reply", T1, "--channel", "email", "--body", "  "]).exit_code == 2
    assert invoke(["inbox", "bulk", "--ids", " , ", "--action", "done"]).exit_code == 2
    assert invoke(["inbox", "bulk", "--ids", T1, "--action", "archive"]).exit_code == 2
    assert not reply.called and not bulk.called


def test_a_failed_draft_says_why(invoke, mock_api):
    mock_api.post(f"{BASE}/threads/{T1}/ai-draft").respond(202, json={"draft_id": "d1"})
    mock_api.get(f"{BASE}/ai-drafts/d1").respond(
        200,
        json={"draft_id": "d1", "status": "failed", "reason": "draft_placeholder"},
    )
    result = invoke(["inbox", "ai-draft", T1, "--channel", "email", "--wait"])
    assert result.exit_code == 0
    assert "draft_placeholder" in result.output


def test_a_ready_draft_with_a_subject_prints_it_and_json_waits_too(invoke, mock_api):
    mock_api.post(f"{BASE}/threads/{T1}/ai-draft").respond(202, json={"draft_id": "d1"})
    ready = {"draft_id": "d1", "status": "ready", "subject": "Re: Deck", "body": "Here."}
    mock_api.get(f"{BASE}/ai-drafts/d1").respond(200, json=ready)
    result = invoke(["inbox", "ai-draft", T1, "--channel", "email", "--wait"])
    assert "Re: Deck" in result.output
    as_json = invoke(["inbox", "ai-draft", T1, "--channel", "email", "--wait", "--json"])
    assert json.loads(as_json.output) == ready
