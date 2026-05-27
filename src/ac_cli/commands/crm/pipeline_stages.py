"""CRM deal pipeline stages commands (ENG-931).

Per-organization customization of the deal pipeline: rename, add, remove,
reorder open stages, edit default probability. The Won and Lost terminal
stages are protected — they can be renamed and have their probability
changed but never deleted.

All mutating commands require the caller to be an organization owner or
admin; the API returns 403 otherwise.
"""

from __future__ import annotations

import json as _json
from typing import Any

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.crm import _CRM
from ac_cli.formatting import print_detail, print_json, print_table


pipeline_app = typer.Typer(help="Per-org deal pipeline stages")


@pipeline_app.command("list")
def pipeline_stages_list(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List pipeline stages for the current org, ordered by sort_order."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/pipeline/stages")
    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data,
        [
            ("sort_order", "#"),
            ("label", "Label"),
            ("key", "Key"),
            ("stage_type", "Type"),
            ("default_probability", "Prob %"),
            ("id", "ID"),
        ],
        title=f"Pipeline stages ({len(data)} total)",
    )


@pipeline_app.command("create")
def pipeline_stages_create(
    ctx: typer.Context,
    label: str = typer.Option(..., help="Display label for the new stage"),
    default_probability: int = typer.Option(
        ..., "--default-probability", min=0, max=100, help="0-100"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new open stage (slots in before Won / Lost)."""
    set_json_mode(json_output)
    body = _build_body(label=label, default_probability=default_probability)
    resp = _api_request("post", f"{_CRM}/pipeline/stages", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created stage:[/green] {data['label']} ({data['key']})")


@pipeline_app.command("update")
def pipeline_stages_update(
    ctx: typer.Context,
    stage_id: str = typer.Argument(..., help="Stage UUID"),
    label: str | None = typer.Option(None, help="New label"),
    default_probability: int | None = typer.Option(
        None, "--default-probability", min=0, max=100
    ),
    sort_order: int | None = typer.Option(None, "--sort-order", min=0),
    json_output: bool = JSON_OPTION,
) -> None:
    """Edit a stage's label / default probability / sort order."""
    set_json_mode(json_output)
    body = _build_body(
        label=label,
        default_probability=default_probability,
        sort_order=sort_order,
    )
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/pipeline/stages/{stage_id}", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated stage:[/green] {data['label']} ({data['key']})")


@pipeline_app.command("delete")
def pipeline_stages_delete(
    ctx: typer.Context,
    stage_id: str = typer.Argument(..., help="Stage UUID"),
    reassign_to: str | None = typer.Option(
        None,
        "--reassign-to",
        help="Key of the open stage to move existing deals to. Required if the stage has deals.",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete an open stage. Won / Lost return 409. Deals must be reassigned."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        msg = f"Delete pipeline stage {stage_id}"
        if reassign_to:
            msg += f" and move its deals to {reassign_to!r}"
        typer.confirm(f"{msg}?", abort=True)

    params: dict[str, Any] = {}
    if reassign_to:
        params["reassign_to"] = reassign_to

    _api_request(
        "delete", f"{_CRM}/pipeline/stages/{stage_id}", params=params or None
    )

    if json_output:
        print_json({"deleted": True, "id": stage_id, "reassign_to": reassign_to})
    else:
        rprint(f"[green]Deleted stage:[/green] {stage_id}")


@pipeline_app.command("reorder")
def pipeline_stages_reorder(
    ctx: typer.Context,
    items: str = typer.Option(
        ...,
        "--items",
        help='JSON array of {"id":"<uuid>","sort_order":N}; e.g. \'[{"id":"a","sort_order":1}]\'',
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reorder stages."""
    set_json_mode(json_output)
    try:
        parsed = _json.loads(items)
    except _json.JSONDecodeError as exc:
        rprint(f"[red]--items must be valid JSON:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if not isinstance(parsed, list):
        rprint("[red]--items must decode to a JSON array[/red]")
        raise typer.Exit(code=2)

    body = {"items": parsed}
    resp = _api_request("post", f"{_CRM}/pipeline/stages/reorder", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Reordered {len(data)} stages.[/green]")
