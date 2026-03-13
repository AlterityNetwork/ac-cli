"""Workflow run commands."""

from __future__ import annotations

import json

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request, _build_body
from ac_cli.commands.workflows import _WORKFLOWS
from ac_cli.formatting import print_detail, print_json, print_table

runs_app = typer.Typer(help="Workflow run operations")


@runs_app.command("create")
def runs_create(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    input_json: str | None = typer.Option(None, "--input", help="Input JSON string"),
    idempotency_key: str | None = typer.Option(None, "--idempotency-key", help="Idempotency key"),
) -> None:
    """Create a new workflow run."""
    body: dict = {}
    if input_json:
        body["input"] = json.loads(input_json)

    headers: dict = {}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    kwargs: dict = {"json": body}
    if headers:
        kwargs["headers"] = headers

    resp = _api_request("post", f"{_WORKFLOWS}/{workflow_id}/runs", **kwargs)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Run created:[/green] {data['run_id']} (status: {data['status']})")


@runs_app.command("list")
def runs_list(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
) -> None:
    """List runs for a workflow."""
    params: dict = {"limit": limit, "offset": offset}
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs", params=params)

    data = resp.json()
    if ctx.obj["json"]:
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


@runs_app.command("get")
def runs_get(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    run_id: str = typer.Argument(..., help="Run ID"),
) -> None:
    """Get a workflow run by ID."""
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/{run_id}")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("status", "Status"),
        ("workflow_id", "Workflow ID"),
        ("started_at", "Started"),
        ("completed_at", "Completed"),
        ("error", "Error"),
    ])


@runs_app.command("logs")
def runs_logs(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    run_id: str = typer.Argument(..., help="Run ID"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
) -> None:
    """Get logs for a workflow run."""
    params: dict = {"limit": limit, "offset": offset}
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/{run_id}/logs", params=params)

    data = resp.json()
    if ctx.obj["json"]:
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
