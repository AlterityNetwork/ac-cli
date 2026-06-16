"""Managed agents run commands."""

from __future__ import annotations

import json

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
)
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Managed agents")

_AGENTS = "/api/v1/agents"

runs_app = typer.Typer(help="Managed agent run operations")


@app.callback()
def agents_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@runs_app.command("create")
def runs_create(
    ctx: typer.Context,
    agent: str = typer.Option(..., "--agent", help="Agent name to run"),
    input_json: str | None = typer.Option(None, "--input", help="Input JSON string"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Enqueue a new managed agent run."""
    set_json_mode(json_output)
    body: dict = {"agent": agent, "input": {}}
    if input_json:
        try:
            body["input"] = json.loads(input_json)
        except json.JSONDecodeError:
            rprint("[red]Invalid JSON for --input[/red]")
            raise typer.Exit(code=1)

    resp = _api_request("post", f"{_AGENTS}/runs", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            f"[green]Run created:[/green] {data['run_id']} "
            f"({data['agent']}, status: {data['status']})"
        )


@runs_app.command("get")
def runs_get(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a managed agent run by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_AGENTS}/runs/{run_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("run_id", "Run ID"),
            ("agent", "Agent"),
            ("status", "Status"),
            ("error", "Error"),
            ("created_at", "Created"),
            ("started_at", "Started"),
            ("finished_at", "Finished"),
        ],
    )


@runs_app.command("list")
def runs_list(
    ctx: typer.Context,
    agent: str | None = typer.Option(None, "--agent", help="Filter by agent name"),
    status: str | None = typer.Option(None, "--status", help="Filter by run status"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List managed agent runs."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if agent:
        params["agent"] = agent
    if status:
        params["status"] = status
    resp = _api_request("get", f"{_AGENTS}/runs", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("run_id", "Run ID"),
            ("agent", "Agent"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Runs ({len(items)})",
    )


app.add_typer(runs_app, name="runs")
