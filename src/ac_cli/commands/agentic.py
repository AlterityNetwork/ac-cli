"""Agentic platform run commands.

`ac agentic runs` drives the run surface of the new agentic platform. It sits
beside `ac agents runs`, which drives the live stack, and it replaces none of
it: the two stacks are branch isolated until the cutover, so the alias and the
deletion of the old commands belong to Phase 7.

The endpoints are ac-docs, the file
engineering/system-design/agentic-platform/interfaces/surfaces.md, Run Explorer.
"""

from __future__ import annotations

import json
import uuid

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Agentic platform")

_AGENTIC = "/api/v1/agentic"

runs_app = typer.Typer(help="Agentic run operations")


@app.callback()
def agentic_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


def _parse_input(input_json: str | None) -> dict:
    """Reads the --input flag, or answers an empty body.

    Args:
        input_json: The JSON string the caller passed, or None.

    Returns:
        The parsed input.

    Raises:
        typer.Exit: The string is not JSON.
    """
    if not input_json:
        return {}
    try:
        parsed = json.loads(input_json)
    except json.JSONDecodeError:
        rprint("[red]Invalid JSON for --input[/red]")
        raise typer.Exit(code=1) from None
    if not isinstance(parsed, dict):
        rprint("[red]--input must be a JSON object[/red]")
        raise typer.Exit(code=1)
    return parsed


_RUN_FIELDS = [
    ("id", "Run ID"),
    ("kind", "Kind"),
    ("definition_name", "Definition"),
    ("status", "Status"),
    ("waiting_on", "Waiting on"),
    ("source", "Source"),
    ("child_count", "Children"),
    ("created_at", "Created"),
    ("started_at", "Started"),
    ("ended_at", "Ended"),
]

_LIST_FIELDS = [
    ("id", "Run ID"),
    ("definition_name", "Definition"),
    ("status", "Status"),
    ("kind", "Kind"),
    ("created_at", "Created"),
]

_SPAN_FIELDS = [
    ("span_id", "Span ID"),
    ("kind", "Kind"),
    ("name", "Name"),
    ("status", "Status"),
    ("duration_ms", "Duration (ms)"),
    ("started_at", "Started"),
]


@runs_app.command("start")
def runs_start(
    ctx: typer.Context,
    definition_id: str = typer.Option(
        ..., "--definition", help="Definition to run (agent or workflow)"
    ),
    input_json: str | None = typer.Option(None, "--input", help="Input JSON string"),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
        help="Delivery identity of this start. A fresh one is minted when it is not given.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start a run of one definition."""
    set_json_mode(json_output)
    body = {"definition_id": definition_id, "input": _parse_input(input_json)}
    # A fresh key per invocation, and never a stable one. The key names the
    # delivery, so a value derived from the command would make tomorrow's run a
    # duplicate of today's and it would never execute.
    key = idempotency_key or str(uuid.uuid4())

    resp = _api_request("post", f"{_AGENTIC}/runs", json=body, headers={"Idempotency-Key": key})

    data = resp.json()
    if json_output:
        print_json(data)
        return
    outcome = data.get("outcome")
    if outcome == "duplicate":
        rprint(
            f"[yellow]Duplicate:[/yellow] this key already started "
            f"{data['id']} (status: {data['status']})"
        )
        return
    rprint(
        f"[green]Run started:[/green] {data['id']} "
        f"({data['definition_name']}, status: {data['status']})"
    )


@runs_app.command("get")
def runs_get(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get one agentic run by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_AGENTIC}/runs/{run_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, _RUN_FIELDS)
    usage = data.get("usage") or {}
    rprint(
        f"[dim]Tree usage:[/dim] {usage.get('total_tokens', 0)} tokens, "
        f"{usage.get('cost_cents', 0)} cents"
    )
    if data.get("child_count"):
        rprint(f"[dim]Read the children:[/dim] ac agentic runs list --parent {run_id}")


@runs_app.command("list")
def runs_list(
    ctx: typer.Context,
    parent: str | None = typer.Option(None, "--parent", help="Children of one run"),
    definition_id: str | None = typer.Option(None, "--definition", help="Runs of one definition"),
    status: str | None = typer.Option(None, "--status", help="Runs in one status"),
    every: bool = typer.Option(
        False, "--all", help="Include child runs. The default returns roots only."
    ),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(50, help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List agentic runs. It returns the top of each tree by default."""
    set_json_mode(json_output)
    params: dict = {"limit": limit}
    # root_only is unset unless --all names it. The endpoint reads roots by
    # default and children when a parent is named, so sending it would refuse
    # the --parent case with a 400.
    if every:
        params["root_only"] = "false"
    if parent:
        params["parent_run_id"] = parent
    if definition_id:
        params["definition_id"] = definition_id
    if status:
        params["status"] = status
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_AGENTIC}/runs", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    print_table(items, _LIST_FIELDS, title=f"Runs ({len(items)})")
    if data.get("next_cursor"):
        rprint(f"[dim]Next page:[/dim] --cursor {data['next_cursor']}")


@runs_app.command("spans")
def runs_spans(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(50, help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the spans of one run.

    It reads the spans of that run alone. A child run holds its own spans, so
    open the child to read them.
    """
    set_json_mode(json_output)
    params: dict = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_AGENTIC}/runs/{run_id}/spans", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    print_table(items, _SPAN_FIELDS, title=f"Spans ({len(items)})")
    if data.get("next_cursor"):
        rprint(f"[dim]Next page:[/dim] --cursor {data['next_cursor']}")


@runs_app.command("cancel")
def runs_cancel(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Cancel one run and its descendants.

    Cancel is idempotent. Cancelling a finished run is still a success, and the
    answer carries the status the run produced.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Cancel agentic run {run_id} and its children?", abort=True)

    resp = _api_request("post", f"{_AGENTIC}/runs/{run_id}/cancel")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Cancel requested:[/green] {data['id']} (status: {data['status']})")


app.add_typer(runs_app, name="runs")
