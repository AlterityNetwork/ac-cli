"""Envoy sequence recipients commands."""

from __future__ import annotations

import json as json_lib

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode, should_skip_confirm
from ac_cli.commands.crm import _api_request
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_json, print_table

recipients_app = typer.Typer(help="Sequence recipient operations")


@recipients_app.command("list")
def recipients_list(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    status: str | None = typer.Option(None, help="Filter by status"),
    step_id: str | None = typer.Option(None, "--step-id", help="Filter by step"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List recipients of a sequence."""
    set_json_mode(json_output)
    params: dict = {}
    if status:
        params["status_filter"] = status
    if step_id:
        params["step_id"] = step_id

    resp = _api_request("get", f"{_ENVOY}/sequences/{sequence_id}/recipients", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("recipient_name", "Name"),
            ("recipient_email", "Email"),
            ("status", "Status"),
            ("current_step", "Current Step"),
            ("id", "ID"),
        ],
        title=f"Recipients ({len(items)})",
    )


@recipients_app.command("add")
def recipients_add(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    source: str = typer.Option(..., help="JSON array of recipient objects"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add recipients to a sequence."""
    set_json_mode(json_output)
    try:
        recipients = json_lib.loads(source)
    except json_lib.JSONDecodeError:
        rprint("[red]Invalid JSON for --source[/red]")
        raise typer.Exit(code=1)

    resp = _api_request("post", f"{_ENVOY}/sequences/{sequence_id}/recipients", json=recipients)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        count = len(recipients) if isinstance(recipients, list) else 1
        rprint(f"[green]Added {count} recipient(s) to sequence {sequence_id}[/green]")


@recipients_app.command("remove")
def recipients_remove(
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    recipient_id: str = typer.Argument(..., help="Recipient ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Remove a recipient from a sequence."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Remove recipient {recipient_id} from sequence {sequence_id}?", abort=True)

    _api_request("delete", f"{_ENVOY}/sequences/{sequence_id}/recipients/{recipient_id}")

    rprint(f"[green]Removed recipient {recipient_id} from sequence {sequence_id}[/green]")
