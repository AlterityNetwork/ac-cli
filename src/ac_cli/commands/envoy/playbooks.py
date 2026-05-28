"""Envoy playbooks commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    _get_org_id,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table

# Playbooks moved out of /envoy to top-level /api/v1/playbooks (ENG-592).
_PLAYBOOKS = "/api/v1/playbooks"

playbooks_app = typer.Typer(help="Playbook operations")


@playbooks_app.command("list")
def playbooks_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int | None = typer.Option(None, help="Max results to return"),
    offset: int | None = typer.Option(None, help="Row offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List playbooks."""
    set_json_mode(json_output)
    params: dict = {}
    if query:
        params["q"] = query
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    resp = _api_request("get", f"{_PLAYBOOKS}", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("name", "Name"),
            ("status", "Status"),
            ("id", "ID"),
        ],
        title=f"Playbooks ({len(items)})",
    )


@playbooks_app.command("get")
def playbooks_get(
    ctx: typer.Context,
    playbook_id: str = typer.Argument(..., help="Playbook ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a playbook by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_PLAYBOOKS}/{playbook_id}")

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
            ("status", "Status"),
            ("competitor_name", "Competitor Name"),
            ("created_at", "Created"),
            ("updated_at", "Updated"),
        ],
    )


@playbooks_app.command("create")
def playbooks_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Playbook name"),
    description: str | None = typer.Option(None, help="Description"),
    status: str | None = typer.Option(None, help="Status"),
    competitor_name: str | None = typer.Option(None, "--competitor-name", help="Competitor name"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new playbook."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        description=description,
        status=status,
        competitor_name=competitor_name,
    )

    body["organization_id"] = _get_org_id()

    resp = _api_request("post", f"{_PLAYBOOKS}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created playbook:[/green] {data['name']} ({data['id']})")


@playbooks_app.command("update")
def playbooks_update(
    ctx: typer.Context,
    playbook_id: str = typer.Argument(..., help="Playbook ID"),
    name: str | None = typer.Option(None, help="Playbook name"),
    description: str | None = typer.Option(None, help="Description"),
    status: str | None = typer.Option(None, help="Status"),
    competitor_name: str | None = typer.Option(None, "--competitor-name", help="Competitor name"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a playbook."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        description=description,
        status=status,
        competitor_name=competitor_name,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_PLAYBOOKS}/{playbook_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated playbook:[/green] {data['name']} ({data['id']})")


@playbooks_app.command("delete")
def playbooks_delete(
    playbook_id: str = typer.Argument(..., help="Playbook ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a playbook."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete playbook {playbook_id}?", abort=True)

    _api_request("delete", f"{_PLAYBOOKS}/{playbook_id}")

    rprint(f"[green]Deleted playbook {playbook_id}[/green]")


@playbooks_app.command("duplicate")
def playbooks_duplicate(
    ctx: typer.Context,
    playbook_id: str = typer.Argument(..., help="Playbook ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Duplicate a playbook."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_PLAYBOOKS}/{playbook_id}/duplicate")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Duplicated playbook:[/green] {data['name']} ({data['id']})")
