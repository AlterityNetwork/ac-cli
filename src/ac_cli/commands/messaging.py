"""Messaging platform commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.formatting import print_json, print_table

app = typer.Typer(help="Messaging platform operations")

_MESSAGING = "/api/v1/messaging"


@app.callback()
def messaging_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("sessions")
def messaging_sessions(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List active messaging sessions for the organization."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_MESSAGING}/sessions")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("platform", "Platform"),
            ("display_name", "Display Name"),
            ("sender_id", "Sender ID"),
            ("last_activity_at", "Last Activity"),
            ("id", "ID"),
        ],
        title=f"Messaging Sessions ({len(items)})",
    )


@app.command("link")
def messaging_link(
    ctx: typer.Context,
    token: str = typer.Option(..., "--token", help="Link token from the bot's login URL"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Link an external messaging sender to your AC account."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_MESSAGING}/link", json={"token": token})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint(
        f"[green]Linked:[/green] {data['platform']} sender {data['sender_id']} "
        f"to org {data['organization_id']}"
    )
