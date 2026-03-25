"""Envoy sales signals command."""
from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_json, print_table


def signals_command(
    ctx: typer.Context,
    recipient_id: str = typer.Argument(..., help="Recipient ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get sales signals for a recipient."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ENVOY}/recipients/{recipient_id}/sales-signals")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    if not items:
        rprint("[dim]No signals found.[/dim]")
        return

    print_table(
        items,
        [
            ("signal_type", "Type"),
            ("description", "Description"),
            ("strength", "Strength"),
            ("detected_at", "Detected"),
        ],
        title=f"Sales Signals ({len(items)})",
    )
