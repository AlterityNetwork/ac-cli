"""Chat thread management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.chat import _CHAT
from ac_cli.formatting import print_json, print_table

threads_app = typer.Typer(help="Chat thread operations")


@threads_app.command("list")
def list_threads(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List chat threads."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CHAT}/threads")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    print_table(
        items,
        [
            ("id", "ID"),
            ("thread_title", "Title"),
            ("archived", "Archived"),
            ("created_at", "Created"),
        ],
        title=f"Chat Threads ({data.get('total', '?')} total)",
    )


@threads_app.command("create")
def create_thread(
    ctx: typer.Context,
    title: str = typer.Option(..., "--title", help="Thread title"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new chat thread."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_CHAT}/threads", json={"title": title})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint(f"[green]Created thread {data.get('id')}[/green]")


@threads_app.command("update")
def update_thread(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    title: str | None = typer.Option(None, "--title", help="New thread title"),
    archived: bool | None = typer.Option(None, "--archived/--no-archived", help="Archive or unarchive"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a chat thread."""
    set_json_mode(json_output)
    body = _build_body(title=title, archived=archived)
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CHAT}/threads/{thread_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint(f"[green]Updated thread {thread_id}[/green]")


@threads_app.command("delete")
def delete_thread(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a chat thread."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete thread {thread_id}?", abort=True)

    _api_request("delete", f"{_CHAT}/threads/{thread_id}")

    rprint(f"[green]Deleted thread {thread_id}[/green]")


@threads_app.command("messages")
def list_messages(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List messages in a chat thread."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CHAT}/threads/{thread_id}/messages")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    print_table(
        [
            {
                **row,
                "content": str(row.get("content", ""))[:80],
            }
            for row in items
        ],
        [
            ("id", "ID"),
            ("role", "Role"),
            ("content", "Content"),
            ("created_at", "Created"),
        ],
        title=f"Messages ({data.get('total', '?')} total)",
    )


@threads_app.command("generate-title")
def generate_title(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Generate a title for a chat thread."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_CHAT}/threads/{thread_id}/generate-title")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint(data.get("title", data))


@threads_app.command("send")
def send_message(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    content: str = typer.Argument(..., help="Message content"),
    context: str | None = typer.Option(None, help="Optional surrounding context"),
    document_id: list[str] | None = typer.Option(
        None,
        "--document-id",
        help="Restrict knowledge retrieval to these resource_hub IDs (repeatable)",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Send a message to a chat thread (non-streaming)."""
    set_json_mode(json_output)
    body = _build_body(content=content, context=context, document_ids=document_id or None)
    resp = _api_request("post", f"{_CHAT}/threads/{thread_id}/send", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Sent to thread {thread_id}[/green]")


@threads_app.command("escalate")
def escalate_thread(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    note: str | None = typer.Option(None, help="Optional escalation note"),
    message_id: str | None = typer.Option(None, "--message-id", help="Specific message to escalate"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Escalate a chat thread to a human."""
    set_json_mode(json_output)
    body = _build_body(note=note, message_id=message_id)
    resp = _api_request("post", f"{_CHAT}/threads/{thread_id}/escalate", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Escalated thread {thread_id}[/green]")
