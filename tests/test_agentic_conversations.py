"""Tests for the agentic conversation commands."""

import json

BASE = "/api/v1/agentic/conversations"
CONVERSATION_ID = "11111111-1111-4111-8111-111111111111"
MESSAGE_ID = "22222222-2222-4222-8222-222222222222"
USER_ID = "33333333-3333-4333-8333-333333333333"
MESSAGES = f"{BASE}/{CONVERSATION_ID}/messages"

CONVERSATION = {
    "id": CONVERSATION_ID,
    "created_by": USER_ID,
    "title": "A plan for Q4",
    "summary": None,
    "last_activity_at": "2026-08-30T10:00:00Z",
    "created_at": "2026-08-30T09:00:00Z",
}
MESSAGE = {
    "id": MESSAGE_ID,
    "conversation_id": CONVERSATION_ID,
    "role": "user",
    "sender_user_id": USER_ID,
    "text": "what is my pipeline",
    "attachment_count": 0,
    "run_id": None,
    "in_reply_to": None,
    "created_at": "2026-08-30T10:00:00Z",
}


# --- list ------------------------------------------------------------------


def test_list_reads_the_page(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json={"items": [CONVERSATION], "next_cursor": None})

    result = invoke(["agentic", "conversations", "list"])

    assert result.exit_code == 0
    assert route.called
    assert "A plan for Q4" in result.output


def test_list_json_keeps_the_page(invoke, mock_api):
    page = {"items": [CONVERSATION], "next_cursor": "abc"}
    mock_api.get(BASE).respond(200, json=page)

    result = invoke(["agentic", "conversations", "list", "--json"])

    assert json.loads(result.output) == page


def test_list_sends_the_cursor_and_the_limit(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json={"items": [], "next_cursor": None})

    invoke(["agentic", "conversations", "list", "--cursor", "abc", "--limit", "10"])

    assert route.calls[0].request.url.params["cursor"] == "abc"
    assert route.calls[0].request.url.params["limit"] == "10"


def test_list_refuses_a_page_size_the_api_refuses(invoke, mock_api):
    """The flag carries the API bounds, so a bad size never travels."""
    route = mock_api.get(BASE).respond(200, json={"items": [], "next_cursor": None})

    result = invoke(["agentic", "conversations", "list", "--limit", "101", "--json"])

    assert result.exit_code == 2
    assert not route.called


# --- create ----------------------------------------------------------------


def test_create_sends_the_title(invoke, mock_api):
    route = mock_api.post(BASE).respond(201, json=CONVERSATION)

    result = invoke(["agentic", "conversations", "create", "--title", "A plan for Q4"])

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {"title": "A plan for Q4"}
    assert CONVERSATION_ID in result.output


def test_create_sends_an_empty_body_with_no_title(invoke, mock_api):
    route = mock_api.post(BASE).respond(201, json={**CONVERSATION, "title": None})

    invoke(["agentic", "conversations", "create"])

    assert json.loads(route.calls[0].request.content) == {}


def test_create_json_keeps_the_conversation(invoke, mock_api):
    mock_api.post(BASE).respond(201, json=CONVERSATION)

    result = invoke(["agentic", "conversations", "create", "--json"])

    assert json.loads(result.output) == CONVERSATION


# --- messages --------------------------------------------------------------


def test_messages_reads_one_conversation(invoke, mock_api):
    route = mock_api.get(MESSAGES).respond(200, json={"items": [MESSAGE], "next_cursor": None})

    result = invoke(["agentic", "conversations", "messages", CONVERSATION_ID])

    assert result.exit_code == 0
    assert route.called
    assert "what is my pipeline" in result.output


def test_messages_json_keeps_the_page(invoke, mock_api):
    page = {"items": [MESSAGE], "next_cursor": None}
    mock_api.get(MESSAGES).respond(200, json=page)

    result = invoke(["agentic", "conversations", "messages", CONVERSATION_ID, "--json"])

    assert json.loads(result.output) == page


def test_messages_reports_a_conversation_this_person_does_not_own(invoke, mock_api):
    """A missing, a foreign and a colleague's conversation share one answer."""
    mock_api.get(MESSAGES).respond(404, json={"detail": "conversation not found"})

    result = invoke(["agentic", "conversations", "messages", CONVERSATION_ID, "--json"])

    # 3 is what _EXIT_CODES maps a 404 to, and a script reads that code.
    assert result.exit_code == 3
    assert json.loads(result.output)["status_code"] == 404


# --- send ------------------------------------------------------------------


def test_send_posts_the_text_with_a_fresh_key(invoke, mock_api):
    """The key names one delivery, so a fresh one is minted per invocation."""
    route = mock_api.post(MESSAGES).respond(202, json=MESSAGE)

    result = invoke(["agentic", "conversations", "send", CONVERSATION_ID, "what is my pipeline"])

    assert result.exit_code == 0
    request = route.calls[0].request
    assert json.loads(request.content) == {"text": "what is my pipeline"}
    assert len(request.headers["Idempotency-Key"]) > 0
    assert MESSAGE_ID in result.output


def test_send_takes_a_key_the_caller_names(invoke, mock_api):
    route = mock_api.post(MESSAGES).respond(202, json=MESSAGE)

    invoke(
        [
            "agentic",
            "conversations",
            "send",
            CONVERSATION_ID,
            "hello",
            "--idempotency-key",
            "k1",
        ]
    )

    assert route.calls[0].request.headers["Idempotency-Key"] == "k1"


def test_two_sends_mint_two_keys(invoke, mock_api):
    """A key derived from the text would make tomorrow's message a duplicate."""
    route = mock_api.post(MESSAGES).respond(202, json=MESSAGE)

    invoke(["agentic", "conversations", "send", CONVERSATION_ID, "hello"])
    invoke(["agentic", "conversations", "send", CONVERSATION_ID, "hello"])

    first = route.calls[0].request.headers["Idempotency-Key"]
    second = route.calls[1].request.headers["Idempotency-Key"]
    assert first != second


def test_send_reports_a_repeated_key_as_a_duplicate(invoke, mock_api):
    """The API answers 200 with the first message, and never a 409."""
    mock_api.post(MESSAGES).respond(200, json=MESSAGE)

    result = invoke(
        [
            "agentic",
            "conversations",
            "send",
            CONVERSATION_ID,
            "hello",
            "--idempotency-key",
            "k1",
        ]
    )

    assert result.exit_code == 0
    assert "Duplicate" in result.output


def test_send_json_keeps_the_message(invoke, mock_api):
    mock_api.post(MESSAGES).respond(202, json=MESSAGE)

    result = invoke(["agentic", "conversations", "send", CONVERSATION_ID, "hello", "--json"])

    assert json.loads(result.output) == MESSAGE


def test_send_reports_a_refused_message(invoke, mock_api):
    mock_api.post(MESSAGES).respond(400, json={"detail": "a message needs text"})

    result = invoke(["agentic", "conversations", "send", CONVERSATION_ID, " ", "--json"])

    # 400 is not in _EXIT_CODES, so it takes the default.
    assert result.exit_code == 1
    assert json.loads(result.output)["status_code"] == 400
