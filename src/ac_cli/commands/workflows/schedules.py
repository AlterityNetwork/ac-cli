"""Workflow schedule commands."""

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
from ac_cli.formatting import print_detail, print_json, print_table

schedules_app = typer.Typer(help="Workflow schedule operations")


@schedules_app.command("list")
def schedules_list(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List schedules for a workflow."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/schedules")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("id", "ID"),
            ("cron_expression", "Cron"),
            ("timezone", "Timezone"),
            ("enabled", "Enabled"),
        ],
        title=f"Schedules ({len(items)})",
    )


@schedules_app.command("get")
def schedules_get(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get the schedule for a workflow."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/schedule")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("cron_expression", "Cron"),
            ("timezone", "Timezone"),
            ("enabled", "Enabled"),
            ("next_run_at", "Next Run"),
            ("created_at", "Created"),
        ],
    )


@schedules_app.command("create")
def schedules_create(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    cron: str = typer.Option(..., "--cron", help="Cron expression"),
    timezone: str = typer.Option("UTC", "--timezone", help="Timezone"),
    input_json: str | None = typer.Option(None, "--input", help="Input JSON string"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a schedule for a workflow."""
    set_json_mode(json_output)
    body: dict = {"cron_expression": cron, "timezone": timezone}
    if input_json:
        try:
            body["input"] = json.loads(input_json)
        except json.JSONDecodeError:
            rprint("[red]Invalid JSON for --input[/red]")
            raise typer.Exit(code=1)

    resp = _api_request("post", f"{_WORKFLOWS}/{workflow_id}/schedule", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Schedule created:[/green] {data['id']}")


@schedules_app.command("update")
def schedules_update(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    schedule_id: str = typer.Argument(..., help="Schedule ID"),
    cron: str | None = typer.Option(None, "--cron", help="Cron expression"),
    timezone: str | None = typer.Option(None, "--timezone", help="Timezone"),
    input_json: str | None = typer.Option(None, "--input", help="Input JSON string"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a workflow schedule."""
    set_json_mode(json_output)
    body = _build_body(cron_expression=cron, timezone=timezone)
    if input_json:
        try:
            body["input"] = json.loads(input_json)
        except json.JSONDecodeError:
            rprint("[red]Invalid JSON for --input[/red]")
            raise typer.Exit(code=1)

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_WORKFLOWS}/{workflow_id}/schedules/{schedule_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated schedule {schedule_id}[/green]")


@schedules_app.command("delete")
def schedules_delete(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    schedule_id: str = typer.Argument(..., help="Schedule ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a workflow schedule."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete schedule {schedule_id}?", abort=True)

    _api_request("delete", f"{_WORKFLOWS}/{workflow_id}/schedules/{schedule_id}")

    rprint(f"[green]Deleted schedule {schedule_id}[/green]")


@schedules_app.command("preview")
def schedules_preview(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    cron: str = typer.Option(..., "--cron", help="Cron expression"),
    timezone: str = typer.Option("UTC", "--timezone", help="Timezone"),
    count: int = typer.Option(5, "--count", help="Number of upcoming runs to preview"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Preview upcoming run times for a cron schedule."""
    set_json_mode(json_output)
    body = {"cron_expression": cron, "timezone": timezone, "count": count}
    resp = _api_request("post", f"{_WORKFLOWS}/{workflow_id}/schedule/preview", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    next_runs = data.get("next_runs", [])
    rprint(f"[bold]Next {len(next_runs)} runs:[/bold]")
    for run_time in next_runs:
        rprint(f"  {run_time}")


@schedules_app.command("toggle")
def schedules_toggle(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    schedule_id: str = typer.Argument(..., help="Schedule ID"),
    enabled: bool = typer.Option(..., "--enabled/--disabled", help="Enable or disable"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Toggle a workflow schedule on or off."""
    set_json_mode(json_output)
    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/schedules/{schedule_id}/toggle",
        json={"enabled": enabled},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        state = "enabled" if enabled else "disabled"
        rprint(f"[green]Schedule {schedule_id} {state}[/green]")
