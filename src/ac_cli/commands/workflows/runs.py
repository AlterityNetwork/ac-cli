"""Workflow run commands."""

from __future__ import annotations

import json

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.workflows import _WORKFLOWS
from ac_cli.formatting import print_detail, print_json, print_table

runs_app = typer.Typer(help="Workflow run operations")


@runs_app.command("create")
def runs_create(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    input_json: str | None = typer.Option(None, "--input", help="Input JSON string"),
    idempotency_key: str | None = typer.Option(None, "--idempotency-key", help="Idempotency key"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new workflow run."""
    set_json_mode(json_output)
    body: dict = {"trigger_data": {}}
    if input_json:
        try:
            body["trigger_data"] = json.loads(input_json)
        except json.JSONDecodeError:
            rprint("[red]Invalid JSON for --input[/red]")
            raise typer.Exit(code=1)

    headers: dict = {}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    kwargs: dict = {"json": body}
    if headers:
        kwargs["headers"] = headers

    resp = _api_request("post", f"{_WORKFLOWS}/{workflow_id}/runs", **kwargs)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Run created:[/green] {data['workflow_run_id']} (status: {data['status']})")


@runs_app.command("list")
def runs_list(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    include_archived: bool = typer.Option(
        False, "--include-archived", help="Include archived runs"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List runs for a workflow."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if include_archived:
        params["include_archived"] = "true"
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("id", "ID"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Runs ({len(items)})",
    )


@runs_app.command("archive")
def runs_archive(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    run_ids: list[str] = typer.Argument(..., help="Run IDs to archive"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Archive terminal workflow runs."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Archive {len(run_ids)} workflow run(s)?", abort=True)

    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/runs/archive",
        json={"run_ids": run_ids},
    )
    data = resp.json()
    if json_output:
        print_json(data)
        return

    count = data.get("archived_count", 0)
    rprint(f"[green]Archived {count} {'run' if count == 1 else 'runs'}[/green]")


@runs_app.command("restore")
def runs_restore(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    run_ids: list[str] = typer.Argument(..., help="Run IDs to restore"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Restore archived workflow runs."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Restore {len(run_ids)} workflow run(s)?", abort=True)

    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/runs/restore",
        json={"run_ids": run_ids},
    )
    data = resp.json()
    if json_output:
        print_json(data)
        return

    count = data.get("restored_count", 0)
    rprint(f"[green]Restored {count} {'run' if count == 1 else 'runs'}[/green]")


@runs_app.command("get")
def runs_get(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    run_id: str = typer.Argument(..., help="Run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a workflow run by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/{run_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("status", "Status"),
            ("workflow_id", "Workflow ID"),
            ("started_at", "Started"),
            ("completed_at", "Completed"),
            ("error", "Error"),
        ],
    )


@runs_app.command("logs")
def runs_logs(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    run_id: str = typer.Argument(..., help="Run ID"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get logs for a workflow run."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/{run_id}/logs", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("timestamp", "Timestamp"),
            ("level", "Level"),
            ("message", "Message"),
        ],
        title=f"Run Logs ({len(items)})",
    )
