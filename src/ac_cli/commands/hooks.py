"""Platform hooks commands."""

from __future__ import annotations

import typer

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.formatting import print_json, print_table

app = typer.Typer(help="Platform hooks")

_HOOKS = "/api/v1/platform/hooks"


@app.callback()
def hooks_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("list")
def hooks_list(
    ctx: typer.Context,
    capability: str = typer.Argument(..., help="Capability to filter hooks"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List available hooks for a capability."""
    set_json_mode(json_output)
    resp = _api_request("get", _HOOKS, params={"capability": capability})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    if not items:
        from rich import print as rprint

        rprint("[dim]No hooks found.[/dim]")
        return

    print_table(
        items,
        [
            ("name", "Name"),
            ("capability", "Capability"),
            ("description", "Description"),
        ],
        title=f"Hooks ({len(items)})",
    )
