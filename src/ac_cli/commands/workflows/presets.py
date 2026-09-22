"""Workflow preset commands."""

from __future__ import annotations

import json

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.workflows import _WORKFLOWS
from ac_cli.formatting import print_detail, print_json, print_table, styled

presets_app = typer.Typer(help="Workflow preset operations")


@presets_app.command("list")
def presets_list(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    limit: int = typer.Option(50, "--limit", min=1, max=100, help="Page size, 1 to 100"),
    offset: int = typer.Option(0, "--offset", min=0, help="Row offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List one page of presets with aggregate run statistics."""
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_WORKFLOWS}/{workflow_id}/presets",
        params={"limit": limit, "offset": offset},
    )

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    rows = [{**item, **item.get("stats", {})} for item in items]
    print_table(
        rows,
        [
            ("preset_name", "Name"),
            ("last_run_at", "Last run"),
            ("run_count", "Runs"),
            ("companies_total", "Companies"),
            ("signals_total", "Signals"),
            ("people_total", "People"),
            ("id", "ID"),
        ],
        title=f"Presets ({data.get('total', len(items))} total)",
    )


@presets_app.command("get")
def presets_get(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    preset_id: str = typer.Argument(..., help="Preset ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a workflow preset by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/presets/{preset_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("preset_name", "Name"),
            ("description", "Description"),
            ("settings", "Settings"),
            ("created_at", "Created"),
        ],
    )


@presets_app.command("create")
def presets_create(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    name: str = typer.Option(..., help="Preset name"),
    description: str | None = typer.Option(None, help="Description"),
    config_json: str | None = typer.Option(None, "--config", help="Config JSON string"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a workflow preset."""
    set_json_mode(json_output)
    body = _build_body(preset_name=name, description=description)
    if config_json:
        try:
            body["settings"] = json.loads(config_json)
        except json.JSONDecodeError:
            rprint("[red]Invalid JSON for --config[/red]")
            raise typer.Exit(code=1)

    resp = _api_request("post", f"{_WORKFLOWS}/{workflow_id}/presets", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            styled(
                "[green]Created preset:[/green] {} ({})",
                data["preset_name"],
                data["id"],
            )
        )


@presets_app.command("update")
def presets_update(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    preset_id: str = typer.Argument(..., help="Preset ID"),
    name: str | None = typer.Option(None, help="Preset name"),
    description: str | None = typer.Option(None, help="Description"),
    config_json: str | None = typer.Option(None, "--config", help="Config JSON string"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a workflow preset."""
    set_json_mode(json_output)
    body = _build_body(preset_name=name, description=description)
    if config_json:
        try:
            body["settings"] = json.loads(config_json)
        except json.JSONDecodeError:
            rprint("[red]Invalid JSON for --config[/red]")
            raise typer.Exit(code=1)

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_WORKFLOWS}/{workflow_id}/presets/{preset_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated preset {}[/green]", preset_id))


@presets_app.command("delete")
def presets_delete(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    preset_id: str = typer.Argument(..., help="Preset ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a workflow preset."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete preset {preset_id}?", abort=True)

    _api_request("delete", f"{_WORKFLOWS}/{workflow_id}/presets/{preset_id}")

    rprint(styled("[green]Deleted preset {}[/green]", preset_id))
