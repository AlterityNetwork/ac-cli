"""Envoy inbox commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request, _build_body
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_detail, print_json, print_table

inbox_app = typer.Typer(help="Inbox thread operations")


@inbox_app.command("list")
def inbox_list(
    ctx: typer.Context,
    status: str | None = typer.Option(None, help="Filter by status"),
    sentiment: str | None = typer.Option(None, help="Filter by sentiment"),
    sequence_id: str | None = typer.Option(None, "--sequence-id", help="Filter by sequence"),
    assigned_to: str | None = typer.Option(None, "--assigned-to", help="Filter by assignee"),
    limit: int = typer.Option(50, help="Max results"),
    cursor: str | None = typer.Option(None, help="Pagination cursor"),
) -> None:
    """List inbox threads."""
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    if sentiment:
        params["sentiment"] = sentiment
    if sequence_id:
        params["sequence_id"] = sequence_id
    if assigned_to:
        params["assigned_to"] = assigned_to
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_ENVOY}/inbox/threads", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("subject", "Subject"),
            ("status", "Status"),
            ("sentiment", "Sentiment"),
            ("assigned_to", "Assigned To"),
            ("id", "ID"),
        ],
        title=f"Inbox Threads ({len(items)})",
    )


@inbox_app.command("messages")
def inbox_messages(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
) -> None:
    """Get messages for a thread."""
    resp = _api_request("get", f"{_ENVOY}/inbox/threads/{thread_id}/messages")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("messages", [])
    print_table(
        items,
        [
            ("sender", "Sender"),
            ("body", "Body"),
            ("sent_at", "Sent At"),
        ],
        title=f"Thread Messages ({len(items)})",
    )


@inbox_app.command("archive")
def inbox_archive(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
) -> None:
    """Archive a thread."""
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/archive")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Archived thread {thread_id}[/green]")


@inbox_app.command("unarchive")
def inbox_unarchive(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
) -> None:
    """Unarchive a thread."""
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/unarchive")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Unarchived thread {thread_id}[/green]")


@inbox_app.command("assign")
def inbox_assign(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    user_id: str = typer.Option(..., "--user-id", help="User ID to assign"),
) -> None:
    """Assign a thread to a user."""
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/assign", json={"assigned_to": user_id})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Assigned thread {thread_id} to {user_id}[/green]")


@inbox_app.command("snooze")
def inbox_snooze(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    until: str = typer.Option(..., "--until", help="Snooze until (ISO datetime)"),
) -> None:
    """Snooze a thread until a given time."""
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/snooze", json={"snooze_until": until})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Snoozed thread {thread_id} until {until}[/green]")


@inbox_app.command("complete")
def inbox_complete(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
) -> None:
    """Mark a thread as complete."""
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/complete")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Completed thread {thread_id}[/green]")


@inbox_app.command("update-status")
def inbox_update_status(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    status: str = typer.Option(..., "--status", help="New status"),
) -> None:
    """Update the status of a thread."""
    resp = _api_request("patch", f"{_ENVOY}/inbox/threads/{thread_id}/status", json={"status": status})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Updated thread {thread_id} status to {status}[/green]")


@inbox_app.command("add-tags")
def inbox_add_tags(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    tags: str = typer.Option(..., "--tags", help="Comma-separated tags"),
) -> None:
    """Add tags to a thread."""
    tags_list = [t.strip() for t in tags.split(",")]
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/tags", json=tags_list)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Added tags to thread {thread_id}[/green]")


@inbox_app.command("remove-tags")
def inbox_remove_tags(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    tags: str = typer.Option(..., "--tags", help="Comma-separated tags"),
) -> None:
    """Remove tags from a thread."""
    tags_list = [t.strip() for t in tags.split(",")]
    # httpx delete() doesn't accept json body; use request() directly
    from ac_cli.client import get_api_client
    import httpx

    with get_api_client() as client:
        try:
            resp = client.request("DELETE", f"{_ENVOY}/inbox/threads/{thread_id}/tags", json=tags_list)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            from ac_cli.commands._helpers import _handle_error
            _handle_error(exc)
        except httpx.HTTPError as exc:
            rprint(f"[red]Connection error:[/red] {exc}")
            raise typer.Exit(code=1)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Removed tags from thread {thread_id}[/green]")


@inbox_app.command("reply")
def inbox_reply(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    body: str = typer.Option(..., "--body", help="Reply body"),
    subject: str | None = typer.Option(None, "--subject", help="Reply subject"),
) -> None:
    """Reply to a thread."""
    req_body = _build_body(body=body, subject=subject)
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/reply", json=req_body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Replied to thread {thread_id}[/green]")
