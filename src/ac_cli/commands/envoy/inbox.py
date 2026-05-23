"""Envoy inbox commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, _build_body, set_json_mode
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_json, print_table

inbox_app = typer.Typer(help="Inbox thread operations")


@inbox_app.command("list")
def inbox_list(
    ctx: typer.Context,
    status: str | None = typer.Option(None, help="Filter by status"),
    sentiment: str | None = typer.Option(None, help="Filter by sentiment"),
    sequence_id: str | None = typer.Option(None, "--sequence-id", help="Filter by sequence"),
    assigned_to: str | None = typer.Option(None, "--assigned-to", help="Filter by assignee"),
    needs_response: bool = typer.Option(
        False,
        "--needs-response",
        help=(
            "Only threads where the latest message is inbound (we owe a reply) "
            "AND status='open'. Overrides --status. ENG-963 Inbox badge filter."
        ),
    ),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Pagination offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List inbox threads."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    if sentiment:
        params["sentiment"] = sentiment
    if sequence_id:
        params["sequence_id"] = sequence_id
    if assigned_to:
        params["assigned_to"] = assigned_to
    if needs_response:
        params["needs_response"] = "true"

    resp = _api_request("get", f"{_ENVOY}/inbox/threads", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    print_table(
        items,
        [
            ("subject", "Subject"),
            ("status", "Status"),
            ("sentiment", "Sentiment"),
            ("assigned_to", "Assigned To"),
            ("id", "ID"),
        ],
        title=f"Inbox Threads ({data.get('total', '?')} total)",
    )


@inbox_app.command("messages")
def inbox_messages(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get messages for a thread."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ENVOY}/inbox/threads/{thread_id}/messages")

    data = resp.json()
    if json_output:
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
    json_output: bool = JSON_OPTION,
) -> None:
    """Archive a thread."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/archive")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Archived thread {thread_id}[/green]")


@inbox_app.command("unarchive")
def inbox_unarchive(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Unarchive a thread."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/unarchive")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Unarchived thread {thread_id}[/green]")


@inbox_app.command("assign")
def inbox_assign(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    user_id: str = typer.Option(..., "--user-id", help="User ID to assign"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Assign a thread to a user."""
    set_json_mode(json_output)
    resp = _api_request(
        "post", f"{_ENVOY}/inbox/threads/{thread_id}/assign", json={"assigned_to": user_id}
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Assigned thread {thread_id} to {user_id}[/green]")


@inbox_app.command("snooze")
def inbox_snooze(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    until: str = typer.Option(..., "--until", help="Snooze until (ISO datetime)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Snooze a thread until a given time."""
    set_json_mode(json_output)
    resp = _api_request(
        "post", f"{_ENVOY}/inbox/threads/{thread_id}/snooze", json={"snooze_until": until}
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Snoozed thread {thread_id} until {until}[/green]")


@inbox_app.command("complete")
def inbox_complete(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark a thread as complete."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/complete")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Completed thread {thread_id}[/green]")


@inbox_app.command("update-status")
def inbox_update_status(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    status: str = typer.Option(..., "--status", help="New status"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update the status of a thread."""
    set_json_mode(json_output)
    resp = _api_request(
        "patch", f"{_ENVOY}/inbox/threads/{thread_id}/status", json={"status": status}
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated thread {thread_id} status to {status}[/green]")


@inbox_app.command("add-tags")
def inbox_add_tags(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    tags: str = typer.Option(..., "--tags", help="Comma-separated tags"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add tags to a thread."""
    set_json_mode(json_output)
    tags_list = [t.strip() for t in tags.split(",")]
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/tags", json=tags_list)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Added tags to thread {thread_id}[/green]")


@inbox_app.command("remove-tags")
def inbox_remove_tags(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    tags: str = typer.Option(..., "--tags", help="Comma-separated tags"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Remove tags from a thread."""
    set_json_mode(json_output)
    tags_list = [t.strip() for t in tags.split(",")]
    # httpx delete() doesn't accept json body; use request() directly
    import httpx

    from ac_cli.client import get_api_client

    with get_api_client() as client:
        try:
            resp = client.request(
                "DELETE", f"{_ENVOY}/inbox/threads/{thread_id}/tags", json=tags_list
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            from ac_cli.commands._helpers import _handle_error

            _handle_error(exc)
        except httpx.HTTPError as exc:
            rprint(f"[red]Connection error:[/red] {exc}")
            raise typer.Exit(code=1)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Removed tags from thread {thread_id}[/green]")


@inbox_app.command("reply")
def inbox_reply(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    body: str = typer.Option(..., "--body", help="Reply body"),
    subject: str | None = typer.Option(None, "--subject", help="Reply subject"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reply to a thread."""
    set_json_mode(json_output)
    req_body = _build_body(body=body, subject=subject)
    resp = _api_request("post", f"{_ENVOY}/inbox/threads/{thread_id}/reply", json=req_body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Replied to thread {thread_id}[/green]")
