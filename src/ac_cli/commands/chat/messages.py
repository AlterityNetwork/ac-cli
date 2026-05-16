"""Chat message management commands."""

from __future__ import annotations

import json as _json

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.commands.chat import _CHAT
from ac_cli.formatting import print_json

messages_app = typer.Typer(help="Chat message operations")


@messages_app.command("update-data")
def update_message_data(
    ctx: typer.Context,
    message_id: str = typer.Argument(..., help="Message ID"),
    data: str = typer.Option(
        ...,
        "--data",
        help="JSON object to merge into the message's data field",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update structured data attached to a chat message."""
    set_json_mode(json_output)
    try:
        parsed = _json.loads(data)
    except _json.JSONDecodeError as exc:
        rprint(f"[red]--data is not valid JSON: {exc}[/red]")
        raise typer.Exit(code=2)
    if not isinstance(parsed, dict):
        rprint("[red]--data must be a JSON object[/red]")
        raise typer.Exit(code=2)

    resp = _api_request("patch", f"{_CHAT}/messages/{message_id}/data", json={"data": parsed})
    body = resp.json()
    if json_output:
        print_json(body)
    else:
        rprint(f"[green]Updated message {message_id}[/green]")
