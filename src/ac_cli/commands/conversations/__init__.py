"""Commands for the agentic web chat conversation surface.

`ac agentic conversations` drives the four non-stream endpoints. The stream is
not a CLI shape: it never closes on content, so a terminal would hold it for
the life of the session.

Both lists page newest first. A person reads the last turn without paging to
the end of a conversation.

The endpoints are ac-docs, the file
engineering/system-design/agentic-platform/interfaces/surfaces.md, Web chat.
"""

from __future__ import annotations

import uuid
from typing import NoReturn

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    checked_header_key,
    set_json_mode,
)
from ac_cli.formatting import as_text, print_detail, print_json, print_table

app = typer.Typer(help="Read and write agentic web chat conversations")

_CONVERSATIONS = "/api/v1/agentic/conversations"

# Every agentic list route is `Query(50, ge=1, le=100)`. The flag carries the
# same bounds, so a page size the API refuses never reaches it.
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 100

_CONVERSATION_LIST_FIELDS = [
    ("id", "Conversation ID"),
    ("title", "Title"),
    ("last_activity_at", "Last activity"),
    ("created_at", "Created"),
]
_CONVERSATION_FIELDS = [
    ("id", "Conversation ID"),
    ("title", "Title"),
    ("summary", "Summary"),
    ("created_by", "Created by"),
    ("last_activity_at", "Last activity"),
    ("created_at", "Created"),
]

# `run_id` is here because a delegate turn writes it, and it is the one way a
# person reaches the work their message started. It is a soft reference, so it
# names a run the retention sweep may already have removed.
_MESSAGE_FIELDS = [
    ("id", "Message ID"),
    ("role", "Role"),
    ("text", "Text"),
    ("run_id", "Run"),
    ("created_at", "Created"),
]


def _refuse(detail: str, *, json_output: bool) -> NoReturn:
    """Reports one local input error in the requested output shape.

    Args:
        detail: What the caller must change.
        json_output: Whether the caller asked for JSON.

    Raises:
        typer.Exit: Always, with code 2.
    """
    if json_output:
        print_json({"error": True, "status_code": None, "detail": detail})
    else:
        rprint("[red]Invalid option:[/red]", as_text(detail))
    raise typer.Exit(code=2)


def _page_params(limit: int, cursor: str | None, *, json_output: bool) -> dict[str, object]:
    """Builds the query of one page, and refuses a size the API refuses.

    Args:
        limit: The page size the caller asked for.
        cursor: The position a previous page returned.
        json_output: Whether the caller asked for JSON.

    Returns:
        The query parameters.

    Raises:
        typer.Exit: The limit is outside 1 to 100.
    """
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        _refuse(f"--limit is {_PAGE_MIN} to {_PAGE_MAX}", json_output=json_output)
    params: dict[str, object] = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return params


def _print_next_page(next_cursor: str | None, limit: int) -> None:
    """Prints how to read the next page, when one exists.

    Args:
        next_cursor: The cursor the page answered.
        limit: The size the caller chose.
    """
    if not next_cursor:
        return
    size = "" if limit == _PAGE_DEFAULT else f" --limit {limit}"
    rprint("[dim]Next page:[/dim]", as_text(f"--cursor {next_cursor}{size}"))


@app.command("list")
def conversations_list(
    ctx: typer.Context,
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="Page size, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List your conversations, the one that moved last first."""
    set_json_mode(json_output)
    data = _api_request(
        "get",
        _CONVERSATIONS,
        params=_page_params(limit, cursor, json_output=json_output),
    ).json()
    if json_output:
        print_json(data)
        return
    print_table(data.get("items", []), _CONVERSATION_LIST_FIELDS, title="Conversations")
    _print_next_page(data.get("next_cursor"), limit)


@app.command("create")
def conversations_create(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="Optional title"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Open one conversation."""
    set_json_mode(json_output)
    body: dict[str, object] = {}
    if title is not None:
        body["title"] = title
    data = _api_request("post", _CONVERSATIONS, json=body).json()
    if json_output:
        print_json(data)
        return
    print_detail(data, _CONVERSATION_FIELDS)


@app.command("messages")
def conversations_messages(
    ctx: typer.Context,
    conversation_id: str = typer.Argument(..., help="Conversation ID"),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="Page size, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one conversation, newest message first."""
    set_json_mode(json_output)
    data = _api_request(
        "get",
        f"{_CONVERSATIONS}/{conversation_id}/messages",
        params=_page_params(limit, cursor, json_output=json_output),
    ).json()
    if json_output:
        print_json(data)
        return
    print_table(data.get("items", []), _MESSAGE_FIELDS, title="Messages")
    _print_next_page(data.get("next_cursor"), limit)


@app.command("send")
def conversations_send(
    ctx: typer.Context,
    conversation_id: str = typer.Argument(..., help="Conversation ID"),
    text: str = typer.Argument(..., help="What to say"),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
        help="Delivery identity of this message. A fresh one is minted when it is not given.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Send one message, and start one turn.

    The request never waits for a model call. It answers the stored message,
    and the answer arrives on the conversation stream, which this CLI does not
    read.
    """
    set_json_mode(json_output)
    # A fresh key per invocation, and never a stable one. The key names the
    # delivery, so a value derived from the text would make tomorrow's message
    # a duplicate of today's and it would never be answered.
    #
    # Read the flag with `is not None`. An empty flag is a typing error.
    # Truthiness would mint a key for it and disable the duplicate guard.
    key = checked_header_key(idempotency_key) if idempotency_key is not None else str(uuid.uuid4())
    response = _api_request(
        "post",
        f"{_CONVERSATIONS}/{conversation_id}/messages",
        json={"text": text},
        headers={"Idempotency-Key": key},
    )
    data = response.json()
    if json_output:
        print_json(data)
        return
    # 202 is a message this request wrote. 200 is the message the same key
    # wrote before, and the API never answers 409 for one.
    if response.status_code == 200:
        rprint(
            "[yellow]Duplicate:[/yellow] this key already sent",
            as_text(f"{data['id']} ({data['text']})"),
        )
        return
    rprint("[green]Message sent:[/green]", as_text(data["id"]))
    rprint(
        "[dim]Read the answer:[/dim] ac agentic conversations messages", as_text(conversation_id)
    )
