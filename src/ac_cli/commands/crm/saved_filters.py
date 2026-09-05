"""CRM saved-filters commands."""

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
from ac_cli.formatting import print_detail, print_json, print_table, styled

saved_filters_app = typer.Typer(help="Saved-filter presets for CRM list views")


def _parse_criteria(raw: str | None) -> dict[str, Any] | None:
    """Parse `--criteria` JSON string into a dict, or return None if not provided."""
    if raw is None:
        return None
    try:
        value = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        rprint(styled("[red]--criteria must be valid JSON:[/red] {}", exc))
        raise typer.Exit(code=2) from exc
    if not isinstance(value, dict):
        rprint("[red]--criteria must decode to a JSON object[/red]")
        raise typer.Exit(code=2)
    return value


@saved_filters_app.command("list")
def saved_filters_list(
    ctx: typer.Context,
    member_type: str | None = typer.Option(None, "--member-type", help="company | person | signal"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List saved filters for the current org."""
    set_json_mode(json_output)
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if member_type is not None:
        params["member_type"] = member_type

    resp = _api_request("get", f"{_CRM}/saved-filters", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("name", "Name"),
            ("member_type", "Member type"),
            ("visibility", "Visibility"),
            ("id", "ID"),
        ],
        title=f"Saved filters ({data.get('total', '?')} total)",
    )


@saved_filters_app.command("get")
def saved_filters_get(
    ctx: typer.Context,
    filter_id: str = typer.Argument(..., help="Saved-filter ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show a saved filter by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/saved-filters/{filter_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("name", "Name"),
            ("description", "Description"),
            ("member_type", "Member type"),
            ("visibility", "Visibility"),
            ("criteria", "Criteria"),
            ("created_at", "Created"),
            ("updated_at", "Updated"),
        ],
    )


@saved_filters_app.command("create")
def saved_filters_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Saved-filter name"),
    member_type: str = typer.Option(..., "--member-type", help="company | person | signal"),
    criteria: str = typer.Option("{}", "--criteria", help="JSON object of captured filter state"),
    visibility: str = typer.Option("private", "--visibility", help="private | org"),
    description: str | None = typer.Option(None, help="Optional description"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new saved filter for the current user."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        member_type=member_type,
        visibility=visibility,
        description=description,
        criteria=_parse_criteria(criteria),
    )

    resp = _api_request("post", f"{_CRM}/saved-filters", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Created saved filter:[/green] {} ({})", data["name"], data["id"]))


@saved_filters_app.command("update")
def saved_filters_update(
    ctx: typer.Context,
    filter_id: str = typer.Argument(..., help="Saved-filter ID"),
    name: str | None = typer.Option(None, help="New name"),
    description: str | None = typer.Option(None, help="New description"),
    visibility: str | None = typer.Option(None, "--visibility", help="private | org"),
    criteria: str | None = typer.Option(None, "--criteria", help="Replacement JSON criteria"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a saved filter."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        description=description,
        visibility=visibility,
        criteria=_parse_criteria(criteria),
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/saved-filters/{filter_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated saved filter:[/green] {} ({})", data["name"], data["id"]))


@saved_filters_app.command("delete")
def saved_filters_delete(
    ctx: typer.Context,
    filter_id: str = typer.Argument(..., help="Saved-filter ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a saved filter."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete saved filter {filter_id}?", abort=True)

    _api_request("delete", f"{_CRM}/saved-filters/{filter_id}")

    if json_output:
        print_json({"deleted": True, "id": filter_id})
    else:
        rprint(styled("[green]Deleted saved filter:[/green] {}", filter_id))
