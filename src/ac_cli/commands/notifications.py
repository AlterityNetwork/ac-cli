"""Notifications commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_json, print_table

app = typer.Typer(help="In-app notifications")

_NOTIFICATIONS = "/api/v1/notifications"


@app.callback()
def notifications_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("list")
def notifications_list(
    ctx: typer.Context,
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    unread_only: bool = typer.Option(False, "--unread-only", help="Only return unread"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List notifications."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset, "unread_only": unread_only}
    resp = _api_request("get", _NOTIFICATIONS, params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", []) if isinstance(data, dict) else data
    print_table(
        items,
        [
            ("type", "Type"),
            ("title", "Title"),
            ("is_read", "Read"),
            ("created_at", "Created"),
            ("id", "ID"),
        ],
        title=f"Notifications ({data.get('total', len(items)) if isinstance(data, dict) else len(items)} total)",
    )


@app.command("unread-count")
def notifications_unread_count(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show unread notification count."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_NOTIFICATIONS}/unread-count")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        count = data.get("count", data) if isinstance(data, dict) else data
        rprint(f"[bold]Unread:[/bold] {count}")


@app.command("read")
def notifications_read(
    ctx: typer.Context,
    notification_id: str = typer.Argument(..., help="Notification ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark a notification as read."""
    set_json_mode(json_output)
    _api_request("post", f"{_NOTIFICATIONS}/{notification_id}/read")

    if json_output:
        print_json({"ok": True, "id": notification_id, "action": "read"})
    else:
        rprint(f"[green]Marked notification {notification_id} read[/green]")


@app.command("read-all")
def notifications_read_all(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark all notifications as read."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_NOTIFICATIONS}/read-all")

    data = resp.json() if resp.content else {}
    if json_output:
        print_json(data or {"ok": True, "action": "read-all"})
    else:
        rprint("[green]Marked all notifications read[/green]")


@app.command("delete")
def notifications_delete(
    ctx: typer.Context,
    notification_id: str = typer.Argument(..., help="Notification ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a notification."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Delete notification {notification_id}?",
            abort=True,
        )
    _api_request("delete", f"{_NOTIFICATIONS}/{notification_id}")

    if json_output:
        print_json({"ok": True, "id": notification_id, "action": "delete"})
    else:
        rprint(f"[green]Deleted notification {notification_id}[/green]")


@app.command("preferences")
def notifications_preferences(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Get notification preferences."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_NOTIFICATIONS}/preferences")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("preferences", data) if isinstance(data, dict) else data
    if isinstance(items, list):
        print_table(
            items,
            [("type", "Type"), ("channel", "Channel"), ("enabled", "Enabled")],
            title="Notification Preferences",
        )
    else:
        rprint(items)


@app.command("set-preference")
def notifications_set_preference(
    ctx: typer.Context,
    type_: str = typer.Option(..., "--type", help="Notification type"),
    channel: str = typer.Option(..., "--channel", help="in_app or email"),
    enabled: bool = typer.Option(..., "--enabled/--disabled", help="Enable/disable channel"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Set a notification preference (type+channel)."""
    set_json_mode(json_output)
    body = {"type": type_, "channel": channel, "enabled": enabled}
    resp = _api_request("put", f"{_NOTIFICATIONS}/preferences", json=body)

    data = resp.json() if resp.content else {}
    if json_output:
        print_json(data or body)
    else:
        state = "enabled" if enabled else "disabled"
        rprint(f"[green]Preference {type_}/{channel} {state}[/green]")


@app.command("reset-preferences")
def notifications_reset_preferences(
    ctx: typer.Context,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reset all notification preferences to defaults (opt-in)."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            "Reset all notification preferences to defaults?",
            abort=True,
        )
    _api_request("delete", f"{_NOTIFICATIONS}/preferences")
    if json_output:
        print_json({"ok": True, "action": "reset-preferences"})
    else:
        rprint("[green]Reset notification preferences[/green]")
