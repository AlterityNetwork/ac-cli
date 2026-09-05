"""Admin app management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, _build_body, set_json_mode
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table, styled

admin_apps_app = typer.Typer(help="Admin app management")


@admin_apps_app.command("list")
def apps_list(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List all apps."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/apps")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("apps", [])
    print_table(
        items,
        [("id", "ID"), ("name", "Name"), ("slug", "Slug"), ("status", "Status")],
        title=f"Apps ({len(items)})",
    )


@admin_apps_app.command("update")
def apps_update(
    ctx: typer.Context,
    app_id: str = typer.Argument(..., help="App ID"),
    name: str | None = typer.Option(None, "--name", help="App name"),
    status: str | None = typer.Option(None, "--status", help="App status"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an app."""
    set_json_mode(json_output)
    body = _build_body(name=name, status=status)
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ADMIN}/apps/{app_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated app {}[/green]", app_id))


@admin_apps_app.command("sync-icons")
def apps_sync_icons(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Sync app icons from source."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ADMIN}/apps/sync-icons")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]App icons synced[/green]")
