"""Tests for chat thread commands."""

import json


SAMPLE_THREADS = {
    "data": [
        {
            "id": "thread-1",
            "thread_title": "Project Discussion",
            "archived": False,
            "created_at": "2026-03-20T10:00:00Z",
        },
        {
            "id": "thread-2",
            "thread_title": "Bug Report",
            "archived": True,
            "created_at": "2026-03-19T08:00:00Z",
        },
    ],
    "total": 2,
}

SAMPLE_THREAD = {
    "id": "thread-1",
    "thread_title": "Project Discussion",
    "archived": False,
    "created_at": "2026-03-20T10:00:00Z",
}

SAMPLE_MESSAGES = {
    "data": [
        {
            "id": "msg-1",
            "role": "user",
            "content": "Hello, can you help me with this project?",
            "created_at": "2026-03-20T10:01:00Z",
        },
        {
            "id": "msg-2",
            "role": "assistant",
            "content": "Of course! What do you need help with?",
            "created_at": "2026-03-20T10:02:00Z",
        },
    ],
    "total": 2,
}

SAMPLE_TITLE = {"title": "Auto-generated Title"}


def test_chat_threads_list(invoke, mock_api):
    mock_api.get("/api/v1/chat/threads").respond(200, json=SAMPLE_THREADS)
    result = invoke(["chat", "threads", "list"])
    assert result.exit_code == 0
    assert "Project Discussion" in result.output


def test_chat_threads_list_json(invoke, mock_api):
    mock_api.get("/api/v1/chat/threads").respond(200, json=SAMPLE_THREADS)
    result = invoke(["chat", "threads", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed["data"]) == 2


def test_chat_threads_create(invoke, mock_api):
    mock_api.post("/api/v1/chat/threads").respond(200, json=SAMPLE_THREAD)
    result = invoke(["chat", "threads", "create", "--title", "New Thread"])
    assert result.exit_code == 0
    assert "thread-1" in result.output


def test_chat_threads_create_json(invoke, mock_api):
    mock_api.post("/api/v1/chat/threads").respond(200, json=SAMPLE_THREAD)
    result = invoke(["chat", "threads", "create", "--title", "New Thread", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "thread-1"


def test_chat_threads_update(invoke, mock_api):
    mock_api.patch("/api/v1/chat/threads/thread-1").respond(200, json=SAMPLE_THREAD)
    result = invoke(["chat", "threads", "update", "thread-1", "--title", "Updated"])
    assert result.exit_code == 0


def test_chat_threads_update_no_fields(invoke, mock_api):
    result = invoke(["chat", "threads", "update", "thread-1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_chat_threads_delete_confirm(invoke, mock_api):
    mock_api.delete("/api/v1/chat/threads/thread-1").respond(204, content=b"")
    result = invoke(["chat", "threads", "delete", "thread-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_chat_threads_delete_abort(invoke, mock_api):
    result = invoke(["chat", "threads", "delete", "thread-1"], input="n\n")
    assert result.exit_code == 1


def test_chat_threads_messages(invoke, mock_api):
    mock_api.get("/api/v1/chat/threads/thread-1/messages").respond(200, json=SAMPLE_MESSAGES)
    result = invoke(["chat", "threads", "messages", "thread-1"])
    assert result.exit_code == 0
    assert "user" in result.output


def test_chat_threads_messages_json(invoke, mock_api):
    mock_api.get("/api/v1/chat/threads/thread-1/messages").respond(200, json=SAMPLE_MESSAGES)
    result = invoke(["chat", "threads", "messages", "thread-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed["data"]) == 2


def test_chat_threads_generate_title(invoke, mock_api):
    mock_api.post("/api/v1/chat/threads/thread-1/generate-title").respond(200, json=SAMPLE_TITLE)
    result = invoke(["chat", "threads", "generate-title", "thread-1"])
    assert result.exit_code == 0
    assert "Auto-generated" in result.output
